"""Integration tests for ACP products API."""

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
    "image_url": "https://example.com/laptop.png",
    "in_stock": True,
}


@pytest.fixture(autouse=True)
def _override_optional_auth():
    """Override optional auth for anonymous access in integration tests."""

    async def _anon():
        return None

    app.dependency_overrides[get_current_user_optional] = _anon
    yield
    app.dependency_overrides.clear()
    BaseRepository._pool = None
    BaseRepository._initialized_tables = set()


@pytest.fixture(autouse=True)
def _mock_product_repo():
    """Mock product repository so integration tests don't need a live database."""
    with (
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
        patch(
            "crud_service.routes.products.product_repo.get_by_id",
            new_callable=AsyncMock,
            return_value=_SAMPLE_PRODUCT,
        ),
    ):
        yield


@pytest.fixture()
def client():
    """Create a fresh TestClient per test to avoid event-loop reuse issues."""
    with TestClient(app) as c:
        yield c


def test_list_products_acp(client):
    response = client.get("/acp/products")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["item_id"] == "prod-1"
    assert data[0]["title"] == "Test Laptop"
    assert data[0]["availability"] == "in_stock"


def test_get_product_acp_by_id(client):
    response = client.get("/acp/products/prod-1")
    assert response.status_code == 200
    data = response.json()
    assert data["item_id"] == "prod-1"
    assert data["title"] == "Test Laptop"
    assert data["price"] == "999.99 usd"
