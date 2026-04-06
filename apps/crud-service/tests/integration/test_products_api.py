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


def test_list_products_repo_failure_returns_empty_list(client):
    """Repository/runtime failures should degrade to an empty catalog list."""
    with patch(
        "crud_service.routes.products.product_repo.query",
        new_callable=AsyncMock,
        side_effect=RuntimeError("db unavailable"),
    ):
        response = client.get("/api/products")

    assert response.status_code == 200
    assert response.json() == []


def test_list_products_none_repo_result_returns_empty_list(client):
    """Non-iterable None result should degrade to an empty catalog list."""
    with patch(
        "crud_service.routes.products.product_repo.query",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = client.get("/api/products")

    assert response.status_code == 200
    assert response.json() == []


def test_list_products_non_iterable_repo_result_returns_empty_list(client):
    """Non-iterable result shape should degrade to an empty catalog list."""
    with patch(
        "crud_service.routes.products.product_repo.query",
        new_callable=AsyncMock,
        return_value=42,
    ):
        response = client.get("/api/products")

    assert response.status_code == 200
    assert response.json() == []


def test_list_products_repo_timeout_returns_empty_list(client):
    """Repository timeout should degrade to an empty catalog list."""
    with patch(
        "crud_service.routes.products.product_repo.query",
        new_callable=AsyncMock,
        side_effect=asyncio.TimeoutError(),
    ):
        response = client.get("/api/products")

    assert response.status_code == 200
    assert response.json() == []


def test_trigger_product_enrichment_returns_202_and_publishes_product_updated(client):
    """Trigger endpoint should enqueue ProductUpdated with optional metadata."""
    with patch(
        "crud_service.routes.products.event_publisher.publish_product_updated",
        new_callable=AsyncMock,
    ) as publish_product_updated:
        response = client.post(
            "/api/products/prod-1/trigger-enrichment",
            json={
                "trace_id": "trace-001",
                "trigger_source": "manual",
                "reason": "refresh content",
            },
        )

    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "queued"
    assert payload["product_id"] == "prod-1"
    assert payload["event_type"] == "ProductUpdated"
    assert payload["queued_at"]
    assert payload["trace_id"] == "trace-001"
    assert payload["trigger_source"] == "manual"
    assert payload["reason"] == "refresh content"

    publish_product_updated.assert_awaited_once()
    published_payload = publish_product_updated.await_args.args[0]
    assert published_payload["id"] == "prod-1"
    assert published_payload["timestamp"]
    assert published_payload["trace_id"] == "trace-001"
    assert published_payload["trigger_source"] == "manual"
    assert published_payload["reason"] == "refresh content"


def test_trigger_product_enrichment_returns_404_when_product_not_found(client):
    """Trigger endpoint should return 404 and publish no event for unknown product."""
    with (
        patch(
            "crud_service.routes.products.product_repo.get_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "crud_service.routes.products.event_publisher.publish_product_updated",
            new_callable=AsyncMock,
        ) as publish_product_updated,
    ):
        response = client.post("/api/products/prod-missing/trigger-enrichment", json={})

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
    publish_product_updated.assert_not_awaited()
