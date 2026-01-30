"""Integration tests for cart API."""

import pytest
from fastapi.testclient import TestClient

from crud_service.main import app

client = TestClient(app)


def test_get_cart_requires_auth():
    """Test that getting cart requires authentication."""
    response = client.get("/api/cart")
    assert response.status_code == 401


def test_add_to_cart_requires_auth():
    """Test that adding to cart requires authentication."""
    response = client.post(
        "/api/cart/items",
        json={"product_id": "test-product", "quantity": 1},
    )
    assert response.status_code == 401


def test_add_to_cart_authenticated(mock_auth_token):
    """Test adding to cart when authenticated."""
    # TODO: Implement with mock auth token
    # response = client.post(
    #     "/api/cart/items",
    #     json={"product_id": "test-product", "quantity": 1},
    #     headers={"Authorization": mock_auth_token},
    # )
    # assert response.status_code == 200
    pass
