"""Integration tests for product API."""

import pytest
from fastapi.testclient import TestClient

from crud_service.main import app
from crud_service.auth import get_current_user_optional
from crud_service.repositories.base import BaseRepository


@pytest.fixture(autouse=True)
def _override_optional_auth():
    """Override optional auth for anonymous access in integration tests."""

    async def _anon():
        return None

    app.dependency_overrides[get_current_user_optional] = _anon
    yield
    app.dependency_overrides.clear()
    # Reset the shared asyncpg pool so the next test gets a fresh one
    # bound to its own event loop (avoids "Event loop is closed" errors).
    BaseRepository._pool = None
    BaseRepository._initialized_tables = set()


@pytest.fixture()
def client():
    """Create a fresh TestClient per test to avoid event-loop reuse issues."""
    with TestClient(app) as c:
        yield c


def test_list_products_anonymous(client):
    """Test listing products as anonymous user."""
    response = client.get("/api/products")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_product_by_id(client):
    """Test getting product by ID."""
    # TODO: Create test product first
    # response = client.get("/api/products/test-product-id")
    # assert response.status_code == 200
    pass


def test_list_products_with_search(client):
    """Test product search."""
    response = client.get("/api/products?search=laptop")
    assert response.status_code == 200
    # TODO: Verify search results
