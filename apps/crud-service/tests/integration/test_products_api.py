"""Integration tests for product API."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from crud_service.auth import get_current_user_optional
from crud_service.main import app
from crud_service.repositories.base import BaseRepository
from fastapi.testclient import TestClient

_SAMPLE_PRODUCT = {
    "id": "prod-1",
    "name": "Test Laptop",
    "description": "A test laptop",
    "price": 999.99,
    "category_id": "electronics",
    "image_url": None,
    "in_stock": True,
    "rating": 4.5,
    "review_count": 10,
}


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


@pytest.fixture(autouse=True)
def _mock_product_repo():
    """Mock product repository so integration tests don't need a live database."""
    with (
        patch(
            "crud_service.routes.products.product_repo.get_by_id",
            new_callable=AsyncMock,
            return_value=_SAMPLE_PRODUCT,
        ),
        patch(
            "crud_service.routes.products.product_repo.query",
            new_callable=AsyncMock,
            return_value=[_SAMPLE_PRODUCT],
        ),
        patch(
            "crud_service.routes.products.product_repo.search_by_name",
            new_callable=AsyncMock,
            return_value=[_SAMPLE_PRODUCT],
        ),
        patch(
            "crud_service.routes.products.product_repo.get_by_category",
            new_callable=AsyncMock,
            return_value=[_SAMPLE_PRODUCT],
        ),
    ):
        yield


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
    assert len(response.json()) >= 1


def test_get_product_by_id(client):
    """Test getting product by ID."""
    response = client.get("/api/products/prod-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == _SAMPLE_PRODUCT["id"]
    assert payload["name"] == _SAMPLE_PRODUCT["name"]


def test_list_products_with_search(client):
    """Test product search."""
    response = client.get("/api/products?search=laptop")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_list_products_skips_malformed_records(client):
    """Malformed product rows should be skipped instead of raising 500."""
    malformed_record = {
        "id": "prod-bad",
        "name": "Broken Product",
        "description": "Invalid data",
        "price": "not-a-number",
        "category_id": "electronics",
    }

    with patch(
        "crud_service.routes.products.product_repo.query",
        new_callable=AsyncMock,
        return_value=[malformed_record, _SAMPLE_PRODUCT],
    ):
        response = client.get("/api/products")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == _SAMPLE_PRODUCT["id"]


def test_list_products_repo_failure_returns_503(client):
    """Repository/runtime failures should return 503 rather than unhandled 500."""
    with patch(
        "crud_service.routes.products.product_repo.query",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db unavailable"),
    ):
        response = client.get("/api/products")

    assert response.status_code == 503
    assert response.json()["detail"] == "Product catalog is temporarily unavailable"


def test_list_products_none_repo_result_returns_503(client):
    """Non-iterable None result should degrade to stable 503."""
    with patch(
        "crud_service.routes.products.product_repo.query",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.get("/api/products")

    assert response.status_code == 503
    assert response.json()["detail"] == "Product catalog is temporarily unavailable"


def test_list_products_non_iterable_repo_result_returns_503(client):
    """Non-iterable result shape should degrade to stable 503."""
    with patch(
        "crud_service.routes.products.product_repo.query",
        new_callable=AsyncMock,
        return_value=42,
    ):
        response = client.get("/api/products")

    assert response.status_code == 503
    assert response.json()["detail"] == "Product catalog is temporarily unavailable"


def test_list_products_repo_timeout_returns_503(client):
    """Repository timeout should degrade to stable 503."""
    with patch(
        "crud_service.routes.products.product_repo.query",
        new_callable=AsyncMock,
        side_effect=asyncio.TimeoutError(),
    ):
        response = client.get("/api/products")

    assert response.status_code == 503
    assert response.json()["detail"] == "Product catalog is temporarily unavailable"
