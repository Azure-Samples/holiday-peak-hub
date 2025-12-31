from fastapi.testclient import TestClient
from inventory_health_check.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "inventory-health-check"
