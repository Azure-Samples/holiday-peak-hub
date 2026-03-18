"""Integration tests for cart API."""

import pytest
from crud_service.main import app
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    """Create a fresh test client per test."""
    with TestClient(app) as c:
        yield c


def test_get_cart_requires_auth(client):
    """Test that getting cart requires authentication."""
    response = client.get("/api/cart")
    assert response.status_code == 401


def test_add_to_cart_requires_auth(client):
    """Test that adding to cart requires authentication."""
    response = client.post(
        "/api/cart/items",
        json={"product_id": "test-product", "quantity": 1},
    )
    assert response.status_code == 401


def test_add_to_cart_authenticated(client, mock_auth_token, mock_cosmos_db):
    """Test adding to cart when authenticated."""
    response = client.post(
        "/api/cart/items",
        json={"product_id": "test-product", "quantity": 2},
        headers=mock_auth_token,
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Item added to cart"

    cart_response = client.get("/api/cart", headers=mock_auth_token)
    assert cart_response.status_code == 200
    payload = cart_response.json()
    assert payload["user_id"] == "test-user"
    assert len(payload["items"]) == 1
    assert payload["items"][0]["product_id"] == "test-product"
    assert payload["items"][0]["quantity"] == 2
