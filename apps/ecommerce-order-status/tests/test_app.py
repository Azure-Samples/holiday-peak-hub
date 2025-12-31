from fastapi.testclient import TestClient
from ecommerce_order_status.main import app


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "ecommerce-order-status"
