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
