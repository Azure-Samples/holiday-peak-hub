import pytest
from fastapi.testclient import TestClient
from inventory_health_check.main import app

pytestmark = pytest.mark.usefixtures("mock_foundry_readiness")


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "inventory-health-check"


def test_invoke_requires_sku():
    client = TestClient(app)
    response = client.post("/invoke", json={})
    assert response.status_code == 200
    assert response.json().get("error") == "sku is required"
