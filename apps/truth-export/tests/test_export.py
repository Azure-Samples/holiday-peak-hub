"""Unit tests for the truth-export service."""

# pylint: disable=redefined-outer-name

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from truth_export.adapters import build_truth_export_adapters
from truth_export.export_engine import ExportEngine
from truth_export.main import app
from truth_export.routes import get_adapters, get_engine


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
    from truth_export.schemas_compat import TruthAttribute

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
