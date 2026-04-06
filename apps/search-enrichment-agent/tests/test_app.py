"""App smoke tests for search enrichment agent."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _build_client() -> TestClient:
    from search_enrichment_agent.main import app

    return TestClient(app)


def test_health() -> None:
    client = _build_client()
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "search-enrichment-agent"


def test_invoke_requires_entity_id() -> None:
    client = _build_client()
    response = client.post("/invoke", json={})
    assert response.status_code == 200
    assert response.json()["error"] == "entity_id is required"


def test_agent_activity_endpoints() -> None:
    client = _build_client()
    invoke_response = client.post("/invoke", json={"entity_id": "SKU-1"})
    assert invoke_response.status_code == 200

    traces_response = client.get("/agent/traces")
    assert traces_response.status_code == 200
    assert "traces" in traces_response.json()

    metrics_response = client.get("/agent/metrics")
    assert metrics_response.status_code == 200
    assert metrics_response.json()["service"] == "search-enrichment-agent"
    assert metrics_response.json()["enabled"] is False

    evaluation_response = client.get("/agent/evaluation/latest")
    assert evaluation_response.status_code == 200
    assert "latest" in evaluation_response.json()
    assert evaluation_response.json()["latest"] is None
