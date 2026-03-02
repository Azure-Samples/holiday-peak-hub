from ecommerce_order_status.main import app
from fastapi.testclient import TestClient


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "ecommerce-order-status"


def test_invoke_requires_order_or_tracking():
    client = TestClient(app)
    response = client.post("/invoke", json={})
    assert response.status_code == 200
    assert response.json().get("error") == "order_id or tracking_id is required"


def test_invoke_includes_acp_wrapper():
    client = TestClient(app)
    response = client.post("/invoke", json={"tracking_id": "TRK-001"})
    assert response.status_code == 200
    payload = response.json()
    assert "acp" in payload
    assert payload["acp"]["domain"] == "order_status"
