from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from ecommerce_catalog_search.adapters import AcpCatalogMapper, CatalogAdapters
from holiday_peak_lib.agents.base_agent import AgentDependencies, ModelTarget
from holiday_peak_lib.schemas.inventory import InventoryItem
from holiday_peak_lib.schemas.product import CatalogProduct
from truth_enrichment.adapters import EnrichmentAdapters
from truth_ingestion.adapters import IngestionAdapters, TruthStoreAdapter, build_ingestion_adapters


@dataclass
class IngestionHarness:
    adapters: IngestionAdapters
    truth_store: TruthStoreAdapter
    published_events: list[tuple[str, str]]


@dataclass
class EnrichmentHarness:
    adapters: EnrichmentAdapters
    proposed_records: list[dict[str, Any]]
    truth_records: list[dict[str, Any]]
    audit_records: list[dict[str, Any]]
    hitl_events: list[dict[str, Any]]


@dataclass
class CatalogHarness:
    adapters: CatalogAdapters
    products: AsyncMock
    inventory: AsyncMock


@pytest.fixture(name="agent_config_with_slm")
def fixture_agent_config_with_slm() -> AgentDependencies:
    async def dummy_invoker(*, messages, tools=None, **kwargs):  # noqa: ANN001
        _ = messages, tools, kwargs
        return {"value": "dummy", "confidence": 0.0, "evidence": "dummy"}

    slm = ModelTarget(name="slm", model="fast-model", invoker=dummy_invoker)
    setattr(slm, "deployment_name", "fast-model")
    return AgentDependencies(
        service_name="e2e-test-agent",
        router=None,
        tools={},
        slm=slm,
        llm=None,
    )


@pytest.fixture(name="agent_config_without_models")
def fixture_agent_config_without_models() -> AgentDependencies:
    return AgentDependencies(
        service_name="e2e-test-agent",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


@pytest.fixture(name="raw_product_payload")
def fixture_raw_product_payload() -> dict[str, Any]:
    return {
        "id": "STYLE-100",
        "name": "Explorer Jacket",
        "category": "outerwear",
        "brand": "Contoso",
        "description": "Weather-resistant commuter jacket.",
        "source": "pim",
        "variants": [
            {
                "variant_id": "STYLE-100-BLK-M",
                "sku": "SKU-100",
                "size": "M",
                "color": "",
                "price": 129.99,
            }
        ],
    }


@pytest.fixture(name="build_ingestion_harness")
def fixture_build_ingestion_harness(monkeypatch) -> Callable[[list[dict[str, Any]]], IngestionHarness]:
    monkeypatch.delenv("COSMOS_ACCOUNT_URI", raising=False)

    def _build(dam_assets: list[dict[str, Any]]) -> IngestionHarness:
        truth_store = TruthStoreAdapter()
        published_events: list[tuple[str, str]] = []

        dam = AsyncMock()
        dam.fetch_assets = AsyncMock(return_value=dam_assets)

        events = AsyncMock()

        async def publish_completeness_job(entity_id: str) -> None:
            published_events.append(("completeness-jobs", entity_id))

        async def publish_ingestion_notification(entity_id: str, source: str = "pim") -> None:
            published_events.append((f"ingestion-notifications:{source}", entity_id))

        events.publish_completeness_job = AsyncMock(side_effect=publish_completeness_job)
        events.publish_ingestion_notification = AsyncMock(side_effect=publish_ingestion_notification)

        adapters = build_ingestion_adapters(
            truth_store=truth_store,
            dam=dam,
            events=events,
        )
        return IngestionHarness(
            adapters=adapters,
            truth_store=truth_store,
            published_events=published_events,
        )

    return _build


@pytest.fixture(name="build_enrichment_harness")
def fixture_build_enrichment_harness() -> Callable[..., EnrichmentHarness]:
    def _build(
        *,
        product: dict[str, Any],
        schema: dict[str, Any],
        image_response: dict[str, Any],
    ) -> EnrichmentHarness:
        proposed_records: list[dict[str, Any]] = []
        truth_records: list[dict[str, Any]] = []
        audit_records: list[dict[str, Any]] = []
        hitl_events: list[dict[str, Any]] = []

        products = AsyncMock()
        products.get_product = AsyncMock(return_value=product)
        products.get_schema = AsyncMock(return_value=schema)

        image_analysis = Mock()
        image_analysis.set_vision_invoker = Mock()
        image_analysis.analyze_attribute_from_images = AsyncMock(return_value=image_response)

        proposed = AsyncMock()

        async def upsert_proposed(payload: dict[str, Any]) -> dict[str, Any]:
            proposed_records.append(payload)
            return payload

        proposed.upsert = AsyncMock(side_effect=upsert_proposed)

        truth = AsyncMock()

        async def upsert_truth(payload: dict[str, Any]) -> dict[str, Any]:
            truth_records.append(payload)
            return payload

        truth.upsert = AsyncMock(side_effect=upsert_truth)

        audit = AsyncMock()

        async def append_audit(event: dict[str, Any]) -> dict[str, Any]:
            audit_records.append(event)
            return event

        audit.append = AsyncMock(side_effect=append_audit)

        hitl_publisher = AsyncMock()

        async def publish_hitl(payload: dict[str, Any]) -> None:
            hitl_events.append(payload)

        hitl_publisher.publish = AsyncMock(side_effect=publish_hitl)

        adapters = EnrichmentAdapters(
            products=products,
            proposed=proposed,
            truth=truth,
            audit=audit,
            image_analysis=image_analysis,
            hitl_publisher=hitl_publisher,
        )

        return EnrichmentHarness(
            adapters=adapters,
            proposed_records=proposed_records,
            truth_records=truth_records,
            audit_records=audit_records,
            hitl_events=hitl_events,
        )

    return _build


@pytest.fixture(name="build_catalog_harness")
def fixture_build_catalog_harness() -> Callable[..., CatalogHarness]:
    def _build(
        *,
        products_by_sku: dict[str, CatalogProduct] | None = None,
        default_product: CatalogProduct | None = None,
        related_products: list[CatalogProduct] | None = None,
    ) -> CatalogHarness:
        products_by_sku = products_by_sku or {}
        related_products = related_products or []

        products = AsyncMock()

        async def get_product(sku: str) -> CatalogProduct | None:
            if sku in products_by_sku:
                return products_by_sku[sku]
            return default_product

        products.get_product = AsyncMock(side_effect=get_product)
        products.get_related = AsyncMock(return_value=related_products)

        inventory = AsyncMock()
        inventory.get_item = AsyncMock(return_value=InventoryItem(sku="SKU-100", available=10, reserved=0))

        adapters = CatalogAdapters(
            products=products,
            inventory=inventory,
            mapping=AcpCatalogMapper(),
        )
        return CatalogHarness(adapters=adapters, products=products, inventory=inventory)

    return _build


@pytest.fixture(name="catalog_product")
def fixture_catalog_product() -> CatalogProduct:
    return CatalogProduct(
        sku="SKU-100",
        name="Explorer Headphones",
        description="Over-ear headphones for travel and commuting.",
        price=149.99,
        category="audio",
        brand="Contoso",
        image_url="https://cdn.example.com/sku-100.jpg",
    )


@pytest.fixture(name="make_event")
def fixture_make_event() -> Callable[[dict[str, Any]], MagicMock]:
    def _build(payload: dict[str, Any]) -> MagicMock:
        event = MagicMock()
        event.body_as_str.return_value = json.dumps(payload)
        return event

    return _build


@pytest.fixture(name="review_timestamp")
def fixture_review_timestamp() -> datetime:
    return datetime(2026, 3, 19, tzinfo=timezone.utc)
