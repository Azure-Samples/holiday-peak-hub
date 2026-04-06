"""Unit tests for the Truth Enrichment service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from truth_enrichment.main import app

    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "truth-enrichment"


def test_invoke_missing_entity(client):
    resp = client.post("/invoke", json={})
    assert resp.status_code == 200
    assert resp.json().get("error") == "entity_id is required"


def test_invoke_product_not_found(client):
    resp = client.post("/invoke", json={"entity_id": "sku-999"})
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("error") == "product not found"
    assert data.get("entity_id") == "sku-999"


def test_enrich_product_endpoint_not_found(client):
    resp = client.post("/enrich/product/sku-missing")
    assert resp.status_code == 200
    assert resp.json()["error"] == "product not found"


def test_enrich_field_endpoint_not_found(client):
    resp = client.post("/enrich/field", json={"entity_id": "sku-x", "field_name": "color"})
    assert resp.status_code == 200
    assert resp.json()["error"] == "product not found"


def test_enrich_status_not_found(client):
    resp = client.get("/enrich/status/nonexistent-job-id")
    assert resp.status_code == 200
    assert resp.json()["status"] == "not_found"


def test_agent_activity_endpoints(client):
    invoke_response = client.post("/invoke", json={"entity_id": "sku-999"})
    assert invoke_response.status_code == 200

    traces_response = client.get("/agent/traces")
    assert traces_response.status_code == 200
    assert "traces" in traces_response.json()

    metrics_response = client.get("/agent/metrics")
    assert metrics_response.status_code == 200
    assert metrics_response.json()["service"] == "truth-enrichment"
    assert metrics_response.json()["enabled"] is False

    evaluation_response = client.get("/agent/evaluation/latest")
    assert evaluation_response.status_code == 200
    assert "latest" in evaluation_response.json()
    assert evaluation_response.json()["latest"] is None
