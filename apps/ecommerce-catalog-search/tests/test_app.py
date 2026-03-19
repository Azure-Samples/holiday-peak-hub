from ecommerce_catalog_search.main import app
from fastapi.testclient import TestClient


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "ecommerce-catalog-search"


def test_invoke_returns_service():
    client = TestClient(app)
    response = client.post("/invoke", json={"query": "", "limit": 1})
    assert response.status_code == 200
    assert response.json()["service"] == "ecommerce-catalog-search"


def test_agent_activity_endpoints():
    client = TestClient(app)

    traces_response = client.get("/agent/traces")
    assert traces_response.status_code == 200
    assert "traces" in traces_response.json()

    metrics_response = client.get("/agent/metrics")
    assert metrics_response.status_code == 200
    assert metrics_response.json()["service"] == "ecommerce-catalog-search"

    evaluation_response = client.get("/agent/evaluation/latest")
    assert evaluation_response.status_code == 200
    assert "latest" in evaluation_response.json()
