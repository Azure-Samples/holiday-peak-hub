"""Unit tests for the truth-export service."""

# pylint: disable=redefined-outer-name

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient
from holiday_peak_lib.integrations import (
    GenericRestPIMConnector,
    PIMConnectionConfig,
    PIMWritebackManager,
    TenantConfig,
)
from truth_export.adapters import GenericPIMWritebackAdapter, build_truth_export_adapters
from truth_export.export_engine import ExportEngine
from truth_export.main import app
from truth_export.routes import get_adapters, get_engine
from truth_export.schemas_compat import TruthAttribute


@pytest.fixture()
def engine():
    return ExportEngine()


@pytest.fixture()
def adapters():
    return build_truth_export_adapters()


@pytest.fixture()
def sample_style():
    from truth_export.schemas_compat import ProductStyle

    return ProductStyle(
        id="STYLE-001",
        brand="Contoso",
        modelName="Trail Runner Pro",
        categoryId="footwear",
    )


@pytest.fixture()
def sample_attributes():
    return [
        TruthAttribute(
            entityType="style",
            entityId="STYLE-001",
            attributeKey="price",
            value=89.99,
            source="SYSTEM",
        ),
        TruthAttribute(
            entityType="style",
            entityId="STYLE-001",
            attributeKey="currency",
            value="usd",
            source="SYSTEM",
        ),
        TruthAttribute(
            entityType="style",
            entityId="STYLE-001",
            attributeKey="availability",
            value="in_stock",
            source="SYSTEM",
        ),
    ]


# ---------------------------------------------------------------------------
# ExportEngine unit tests
# ---------------------------------------------------------------------------


def test_engine_ucp_export(engine, sample_style, sample_attributes):
    result = engine.export("job-1", sample_style, sample_attributes, "ucp")
    assert result.status == "completed"
    assert result.payload["product_id"] == "STYLE-001"
    assert result.payload["title"] == "Trail Runner Pro"
    assert result.payload["brand"] == "Contoso"
    assert result.payload["price_amount"] == 89.99
    assert result.payload["currency"] == "usd"
    assert result.payload["protocol"] == "ucp"


def test_engine_acp_export(engine, sample_style, sample_attributes):
    result = engine.export("job-2", sample_style, sample_attributes, "acp")
    assert result.status == "completed"
    assert result.payload["item_id"] == "STYLE-001"
    assert result.payload["title"] == "Trail Runner Pro"
    assert "89.99" in result.payload["price"]


def test_engine_unsupported_protocol(engine, sample_style, sample_attributes):
    result = engine.export("job-3", sample_style, sample_attributes, "unknown_protocol")
    assert result.status == "failed"
    assert result.errors


def test_engine_supported_protocols(engine):
    protocols = engine.supported_protocols()
    assert "acp" in protocols
    assert "ucp" in protocols


def test_engine_audit_event(engine, sample_style):
    event = engine.build_audit_event("job-4", sample_style, "ucp")
    assert event.entity_id == "STYLE-001"
    assert event.action.value == "exported"
    assert event.details["job_id"] == "job-4"


# ---------------------------------------------------------------------------
# REST endpoint tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def seeded_adapters(adapters, sample_style, sample_attributes):
    adapters.truth_store.seed_style(sample_style)
    adapters.truth_store.seed_attributes("STYLE-001", sample_attributes)
    fake_pim = AsyncMock()
    fake_pim.get_product = AsyncMock(return_value=None)
    fake_pim.push_enrichment = AsyncMock(return_value={"ok": True})
    audit_store = AsyncMock()
    audit_store.record = AsyncMock()
    adapters.writeback_manager = PIMWritebackManager(
        pim_connector=fake_pim,
        truth_store=adapters.truth_store,
        audit_store=audit_store,
        tenant_config=TenantConfig(tenant_id="test", writeback_enabled=True),
    )
    return adapters


@pytest.fixture()
def client(seeded_adapters):
    def _adapters_factory():
        return seeded_adapters

    app.dependency_overrides[get_adapters] = _adapters_factory

    def _engine_factory() -> ExportEngine:
        return ExportEngine()

    app.dependency_overrides[get_engine] = _engine_factory
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "truth-export"


def test_export_ucp_endpoint(client):
    resp = client.post("/export/ucp/STYLE-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == "STYLE-001"
    assert data["protocol"] == "ucp"
    assert data["status"] == "completed"


def test_export_acp_endpoint(client):
    resp = client.post("/export/acp/STYLE-001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == "STYLE-001"
    assert data["protocol"] == "acp"
    assert data["status"] == "completed"


def test_export_ucp_not_found(client):
    resp = client.post("/export/ucp/NONEXISTENT")
    assert resp.status_code == 404


def test_export_bulk(client):
    resp = client.post(
        "/export/bulk",
        json={"entity_ids": ["STYLE-001"], "protocol": "ucp"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["protocol"] == "ucp"


def test_export_protocols_endpoint(client):
    resp = client.get("/export/protocols")
    assert resp.status_code == 200
    data = resp.json()
    assert "ucp" in data["protocols"]
    assert "acp" in data["protocols"]


def test_export_status_not_found(client):
    resp = client.get("/export/status/nonexistent-job-id")
    assert resp.status_code == 404


def test_export_pim_single_endpoint(client):
    resp = client.post("/export/pim/STYLE-001", json={"dry_run": False})
    assert resp.status_code == 200
    data = resp.json()
    assert data["entity_id"] == "STYLE-001"
    assert data["status"] == "completed"
    assert "pim_response_summary" in data


def test_export_pim_batch_endpoint(client):
    resp = client.post(
        "/export/pim/batch",
        json={
            "entity_ids": ["STYLE-001", "STYLE-001"],
            "dry_run": False,
            "max_concurrency": 2,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    assert len(data["results"]) == 2


def test_export_pim_batch_limit_validation(client):
    too_many = [f"STYLE-{index:03d}" for index in range(101)]
    resp = client.post(
        "/export/pim/batch",
        json={"entity_ids": too_many, "dry_run": True},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_reverse_mapping_for_salsify_and_akeneo_paths(engine, adapters):
    captured_payloads: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET" and request.url.path == "/api/products/STYLE-001":
            return httpx.Response(
                status_code=200,
                json={
                    "id": "STYLE-001",
                    "name": "Trail Runner Pro",
                    "last_modified": "2025-01-01T00:00:00+00:00",
                },
            )
        if request.method == "PATCH" and request.url.path == "/api/products/STYLE-001":
            captured_payloads.append(json.loads(request.content.decode()))
            return httpx.Response(status_code=200, json={"ok": True})
        return httpx.Response(status_code=404)

    transport = httpx.MockTransport(handler)
    rest_connector = GenericRestPIMConnector(
        PIMConnectionConfig(
            base_url="https://pim.example",
            product_endpoint="/api/products",
            field_mapping={
                "salsify:title": "title",
                "values.description": "description",
            },
        )
    )
    connector = GenericPIMWritebackAdapter(rest_connector)
    connector._connector._client = httpx.AsyncClient(  # pylint: disable=protected-access
        base_url="https://pim.example",
        transport=transport,
    )

    adapters.truth_store.seed_attributes(
        "STYLE-001",
        [
            TruthAttribute(
                entityType="style",
                entityId="STYLE-001",
                attributeKey="title",
                value="Mapped title",
                source="SYSTEM",
            )
        ],
    )
    audit_store = AsyncMock()
    audit_store.record = AsyncMock()
    manager = PIMWritebackManager(
        pim_connector=connector,
        truth_store=adapters.truth_store,
        audit_store=audit_store,
        tenant_config=TenantConfig(tenant_id="test", writeback_enabled=True),
    )

    result = await engine.writeback_entity(manager, "STYLE-001")
    assert result["status"] == "completed"
    assert captured_payloads
    assert "salsify:title" in captured_payloads[0]

    await connector._connector.close()  # pylint: disable=protected-access


@pytest.mark.asyncio
async def test_conflict_handling_blocks_writeback(engine):
    now = datetime.now(timezone.utc)
    truth_version = (now - timedelta(days=1)).isoformat()

    class _ConflictTruthStore:
        async def get_attributes(self, _entity_id: str):
            return [
                {
                    "field": "description",
                    "value": "new value",
                    "version": truth_version,
                    "writeback_eligible": True,
                }
            ]

    pim = AsyncMock()
    pim.push_enrichment = AsyncMock(return_value={"ok": True})
    product = AsyncMock()
    product.last_modified = now
    pim.get_product = AsyncMock(return_value=product)

    manager = PIMWritebackManager(
        pim_connector=pim,
        truth_store=_ConflictTruthStore(),
        audit_store=AsyncMock(record=AsyncMock()),
        tenant_config=TenantConfig(tenant_id="test", writeback_enabled=True),
    )

    result = await engine.writeback_entity(manager, "STYLE-001")

    assert result["status"] == "conflict"
    assert result["conflicts"] == 1
    pim.push_enrichment.assert_not_called()


@pytest.mark.asyncio
async def test_writeback_to_pim_uses_approved_fields_only(engine, adapters):
    adapters.truth_store.seed_attributes(
        "STYLE-001",
        [
            TruthAttribute(
                entityType="style",
                entityId="STYLE-001",
                attributeKey="title",
                value="Approved title",
                source="SYSTEM",
            ),
            TruthAttribute(
                entityType="style",
                entityId="STYLE-001",
                attributeKey="description",
                value="Should not be written",
                source="SYSTEM",
            ),
        ],
    )

    class _StubManager:
        def __init__(self):
            self.called_fields: list[str] = []

        async def writeback_attribute(
            self, entity_id: str, field: str, value, *, truth_version=None
        ):
            _ = entity_id
            _ = value
            _ = truth_version
            self.called_fields.append(field)

            from holiday_peak_lib.integrations import WritebackResult, WritebackStatus

            return WritebackResult(
                entity_id="STYLE-001",
                field=field,
                status=WritebackStatus.SUCCESS,
                message="Writeback succeeded",
            )

    manager = _StubManager()
    result = await engine.writeback_to_pim(
        manager,
        adapters.truth_store,
        "STYLE-001",
        approved_attributes=["title"],
    )

    assert manager.called_fields == ["title"]
    assert result["status"] == "completed"
    assert result["total"] == 1
