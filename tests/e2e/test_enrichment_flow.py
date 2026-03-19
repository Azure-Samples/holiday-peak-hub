from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from holiday_peak_lib.integrations import ProductWritebackResult, WritebackResult, WritebackStatus
from holiday_peak_lib.integrations.pim_writeback import (
    CircuitBreaker,
    PIMWritebackManager,
    TenantConfig,
)
from truth_enrichment.agents import TruthEnrichmentAgent
from truth_export.adapters import AuditStoreAdapter, MockTruthStoreAdapter, build_truth_export_adapters
from truth_export.event_handlers import build_event_handlers
from truth_export.export_engine import ExportEngine
from truth_export.schemas_compat import TruthAttribute
from truth_hitl.review_manager import ReviewDecision, ReviewItem, ReviewManager
from truth_ingestion.adapters import ingest_single_product

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


class _StubWritebackManager:
    async def dry_run(self, entity_id: str) -> ProductWritebackResult:
        return await self.writeback_product(entity_id)

    async def writeback_product(self, entity_id: str) -> ProductWritebackResult:
        return ProductWritebackResult(
            entity_id=entity_id,
            total=1,
            succeeded=1,
            results=[
                WritebackResult(
                    entity_id=entity_id,
                    field="color",
                    status=WritebackStatus.SUCCESS,
                    message="Writeback succeeded",
                )
            ],
        )


class _CapturePIMConnector:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, object]] = []

    async def get_product(self, sku: str) -> None:
        _ = sku
        return None

    async def push_enrichment(self, sku: str, field_name: str, value: object) -> dict[str, object]:
        self.calls.append((sku, field_name, value))
        return {"status": "ok"}


class _FailingPIMConnector:
    async def get_product(self, sku: str) -> None:
        _ = sku
        return None

    async def push_enrichment(self, sku: str, field_name: str, value: object) -> dict[str, object]:
        _ = sku, field_name, value
        raise RuntimeError("pim unavailable")


async def test_happy_path_ingest_enrich_approve_writeback(
    agent_config_with_slm,
    build_ingestion_harness,
    build_enrichment_harness,
    raw_product_payload,
    make_event,
    review_timestamp,
) -> None:
    ingestion = build_ingestion_harness(
        dam_assets=[{"url": "https://cdn.example.com/style-100-front.jpg"}]
    )
    ingested = await ingest_single_product(raw_product_payload, ingestion.adapters)

    style_record = dict(ingested["style"])
    style_record["color"] = None

    enrichment = build_enrichment_harness(
        product=style_record,
        schema={"required_fields": ["color"]},
        image_response={
            "value": "Midnight Blue",
            "confidence": 0.93,
            "evidence": "Dominant color from product imagery.",
            "metadata": {
                "source": "image_analysis",
                "assets": ["https://cdn.example.com/style-100-front.jpg"],
            },
        },
    )

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=enrichment.adapters):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value={
                "value": "Navy",
                "confidence": 0.82,
                "evidence": "Description and title indicate navy tone.",
                "metadata": {"source": "text_enrichment"},
            }
        )
        enrich_result = await agent.handle({"entity_id": style_record["entity_id"]})

    proposed = enrich_result["proposed"][0]

    review_manager = ReviewManager()
    review_manager.enqueue(
        ReviewItem(
            entity_id=proposed["entity_id"],
            attr_id=proposed["id"],
            field_name=proposed["field_name"],
            proposed_value=proposed["proposed_value"],
            confidence=proposed["confidence"],
            current_value=proposed["original_data"].get("color"),
            source="ai",
            proposed_at=review_timestamp,
            product_title=style_record["name"],
            category_label=style_record["category"],
            original_data=proposed["original_data"],
            enriched_data=proposed["enriched_data"],
            reasoning=proposed["reasoning"],
            source_assets=[{"url": asset} for asset in proposed["source_assets"]],
            source_type=proposed["source_type"],
        )
    )
    approved = review_manager.approve(
        proposed["entity_id"],
        ReviewDecision(attr_ids=[proposed["id"]], reviewed_by="staff-user"),
    )

    export_adapters = build_truth_export_adapters()
    export_adapters.writeback_manager = _StubWritebackManager()
    handlers = build_event_handlers(adapters=export_adapters)
    await handlers["export-jobs"](
        None,
        make_event(
            {
                "event_type": "hitl.approved",
                "source": "truth-hitl",
                "data": {
                    "entity_id": proposed["entity_id"],
                    "protocol": "pim",
                    "status": "approved",
                },
            }
        ),
    )

    assert ingested["entity_id"] == "STYLE-100"
    assert proposed["source_type"] == "hybrid"
    assert len(approved) == 1
    assert approved[0].status == "approved"
    assert export_adapters.truth_store._results[-1]["status"] == "completed"  # pylint: disable=protected-access
    assert (
        export_adapters.truth_store._audit_events[-1]["details"]["writeback_status"]  # pylint: disable=protected-access
        == "completed"
    )


async def test_image_only_enrichment_path(agent_config_without_models, build_enrichment_harness) -> None:
    product = {
        "entity_id": "STYLE-IMG",
        "name": "Adventure Backpack",
        "category": "bags",
        "color": None,
    }
    enrichment = build_enrichment_harness(
        product=product,
        schema={"required_fields": ["color"]},
        image_response={
            "value": "Graphite",
            "confidence": 0.97,
            "evidence": "Color inferred from image pixels.",
            "metadata": {"source": "image_analysis", "assets": ["https://cdn.example.com/img.jpg"]},
        },
    )

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=enrichment.adapters):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        proposed = await agent.enrich_field(
            entity_id="STYLE-IMG",
            field_name="color",
            product=product,
            field_definition={"type": "string", "required": True},
        )

    assert proposed["source_type"] == "image_analysis"
    assert proposed["status"] == "auto_approved"
    assert len(enrichment.truth_records) == 1
    assert enrichment.hitl_events == []


async def test_rejection_no_writeback_and_audit(make_event, review_timestamp) -> None:
    manager = ReviewManager()
    manager.enqueue(
        ReviewItem(
            entity_id="STYLE-REJECT",
            attr_id="attr-reject-1",
            field_name="material",
            proposed_value="Wool",
            confidence=0.64,
            current_value=None,
            source="ai",
            proposed_at=review_timestamp,
            product_title="Thermal Hoodie",
            category_label="apparel",
        )
    )

    rejected = manager.reject(
        "STYLE-REJECT",
        ReviewDecision(attr_ids=["attr-reject-1"], reason="incorrect", reviewed_by="qa-user"),
    )

    export_adapters = build_truth_export_adapters()
    export_adapters.writeback_manager = AsyncMock()
    export_adapters.writeback_manager.writeback_product = AsyncMock()
    export_adapters.writeback_manager.dry_run = AsyncMock()

    handlers = build_event_handlers(adapters=export_adapters)
    await handlers["export-jobs"](
        None,
        make_event(
            {
                "event_type": "hitl.rejected",
                "source": "truth-hitl",
                "data": {
                    "entity_id": "STYLE-REJECT",
                    "protocol": "ucp",
                    "status": "rejected",
                },
            }
        ),
    )

    assert len(rejected) == 1
    assert rejected[0].status == "rejected"
    assert manager.audit_log()[0].action == "rejected"
    export_adapters.writeback_manager.writeback_product.assert_not_awaited()
    export_adapters.writeback_manager.dry_run.assert_not_awaited()


async def test_partial_approval_edits_before_approve(review_timestamp) -> None:
    manager = ReviewManager()
    manager.enqueue(
        ReviewItem(
            entity_id="STYLE-EDIT",
            attr_id="attr-color",
            field_name="color",
            proposed_value="Blue",
            confidence=0.78,
            current_value=None,
            source="ai",
            proposed_at=review_timestamp,
            product_title="Urban Jacket",
            category_label="apparel",
        )
    )
    manager.enqueue(
        ReviewItem(
            entity_id="STYLE-EDIT",
            attr_id="attr-material",
            field_name="material",
            proposed_value="Nylon",
            confidence=0.81,
            current_value=None,
            source="ai",
            proposed_at=review_timestamp,
            product_title="Urban Jacket",
            category_label="apparel",
        )
    )

    edited = manager.edit_and_approve(
        "STYLE-EDIT",
        ReviewDecision(
            attr_ids=["attr-color"],
            edited_value="Navy Blue",
            reason="matches brand style guide",
            reviewed_by="staff-editor",
        ),
    )

    truth_store = MockTruthStoreAdapter()
    truth_store.seed_attributes(
        "STYLE-EDIT",
        [
            TruthAttribute(
                entityType="style",
                entityId="STYLE-EDIT",
                attributeKey="color",
                value=edited[0].proposed_value,
                source="HUMAN",
            )
        ],
    )

    pim_connector = _CapturePIMConnector()
    manager_writeback = PIMWritebackManager(
        pim_connector=pim_connector,
        truth_store=truth_store,
        audit_store=AuditStoreAdapter(truth_store),
        tenant_config=TenantConfig(tenant_id="e2e", writeback_enabled=True),
    )

    writeback_result = await ExportEngine().writeback_entity(manager_writeback, "STYLE-EDIT")

    assert edited[0].proposed_value == "Navy Blue"
    assert edited[0].status == "approved"
    assert len(manager.get_by_entity("STYLE-EDIT")) == 1
    assert writeback_result["status"] == "completed"
    assert pim_connector.calls == [("STYLE-EDIT", "color", "Navy Blue")]


async def test_dam_unavailable_fallback_text_only(agent_config_with_slm, build_enrichment_harness) -> None:
    product = {
        "entity_id": "STYLE-DAM-DOWN",
        "name": "Commuter Messenger Bag",
        "category": "bags",
        "material": None,
    }
    enrichment = build_enrichment_harness(
        product=product,
        schema={"required_fields": ["material"]},
        image_response={
            "value": None,
            "confidence": 0.0,
            "evidence": "image analysis unavailable for material",
            "metadata": {"source": "image_analysis", "fallback_reason": "adapter_failure"},
        },
    )

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=enrichment.adapters):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value={
                "value": "Canvas",
                "confidence": 0.85,
                "evidence": "Description mentions waxed canvas shell.",
                "metadata": {"source": "text_enrichment"},
            }
        )
        proposed = await agent.enrich_field(
            entity_id="STYLE-DAM-DOWN",
            field_name="material",
            product=product,
        )

    assert proposed["source_type"] == "text_enrichment"
    assert proposed["proposed_value"] == "Canvas"
    assert proposed["source_assets"] == []


async def test_pim_writeback_failure_and_circuit_breaker_behavior(make_event) -> None:
    truth_store = MockTruthStoreAdapter()
    truth_store.seed_attributes(
        "STYLE-PIM-FAIL",
        [
            TruthAttribute(
                entityType="style",
                entityId="STYLE-PIM-FAIL",
                attributeKey="color",
                value="Black",
                source="SYSTEM",
            )
        ],
    )

    manager = PIMWritebackManager(
        pim_connector=_FailingPIMConnector(),
        truth_store=truth_store,
        audit_store=AuditStoreAdapter(truth_store),
        tenant_config=TenantConfig(tenant_id="e2e", writeback_enabled=True),
        circuit_breaker=CircuitBreaker(threshold=1, reset_seconds=600.0),
    )

    export_adapters = build_truth_export_adapters()
    export_adapters.truth_store = truth_store
    export_adapters.writeback_manager = manager

    handlers = build_event_handlers(adapters=export_adapters)
    event_payload = {
        "event_type": "hitl.approved",
        "source": "truth-hitl",
        "data": {
            "entity_id": "STYLE-PIM-FAIL",
            "protocol": "pim",
            "status": "approved",
        },
    }

    await handlers["export-jobs"](None, make_event(event_payload))
    await handlers["export-jobs"](None, make_event(event_payload))

    first = truth_store._results[-2]  # pylint: disable=protected-access
    second = truth_store._results[-1]  # pylint: disable=protected-access

    assert first["status"] == "failed"
    assert "pim unavailable" in first["results"][0]["message"]
    assert second["status"] == "failed"
    assert "Circuit breaker is open" in second["results"][0]["message"]
