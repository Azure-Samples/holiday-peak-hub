from ecommerce_cart_intelligence.main import app
from fastapi.testclient import TestClient


def test_health():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["service"] == "ecommerce-cart-intelligence"


def test_invoke_returns_service():
    client = TestClient(app)
    response = client.post("/invoke", json={"items": []})
    assert response.status_code == 200
    assert response.json()["service"] == "ecommerce-cart-intelligence"
