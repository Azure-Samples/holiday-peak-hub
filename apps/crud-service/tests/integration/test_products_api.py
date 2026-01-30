"""Integration tests for product API."""

import pytest
from fastapi.testclient import TestClient

from crud_service.main import app

client = TestClient(app)


def test_list_products_anonymous():
    """Test listing products as anonymous user."""
    response = client.get("/api/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_product_by_id():
    """Test getting product by ID."""
    # TODO: Create test product first
    # response = client.get("/api/products/test-product-id")
    # assert response.status_code == 200
    pass


def test_list_products_with_search():
    """Test product search."""
    response = client.get("/api/products?search=laptop")
    assert response.status_code == 200
    # TODO: Verify search results
