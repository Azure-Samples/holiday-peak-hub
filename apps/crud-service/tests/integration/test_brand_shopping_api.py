"""Integration tests for brand-shopping API contracts."""

from unittest.mock import AsyncMock, patch

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from fastapi.testclient import TestClient


@pytest.fixture(name="client")
def fixture_client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _override_auth():
    async def _customer_user():
        return User(
            user_id="customer-100",
            email="customer100@example.com",
            name="Customer 100",
            roles=["customer"],
        )

    app.dependency_overrides[get_current_user] = _customer_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _mock_brand_shopping_dependencies():
    async def fake_product_get(sku):
        return {
            "id": sku,
            "name": f"Product {sku}",
            "description": "Mock product",
            "category_id": "mock-category",
            "price": 50.0,
            "in_stock": True,
        }

    async def fake_user_get_by_id(customer_id):
        return {
            "id": customer_id,
            "email": f"{customer_id}@example.com",
            "name": "Mock Customer",
            "phone": None,
            "tier": "silver",
        }

    async def fake_user_get_by_entra_id(_customer_id):
        return None

    with (
        patch(
            "crud_service.routes.brand_shopping.product_repo.get_by_id",
            new=AsyncMock(side_effect=fake_product_get),
        ),
        patch(
            "crud_service.routes.brand_shopping.user_repo.get_by_id",
            new=AsyncMock(side_effect=fake_user_get_by_id),
        ),
        patch(
            "crud_service.routes.brand_shopping.user_repo.get_by_entra_id",
            new=AsyncMock(side_effect=fake_user_get_by_entra_id),
        ),
        patch(
            "crud_service.routes.brand_shopping.agent_client.get_customer_profile",
            new=AsyncMock(return_value={"tier": "silver"}),
        ),
        patch(
            "crud_service.routes.brand_shopping.agent_client.get_personalization",
            new=AsyncMock(return_value={"preferred_categories": ["mock-category"]}),
        ),
        patch(
            "crud_service.routes.brand_shopping.agent_client.calculate_dynamic_pricing",
            new=AsyncMock(return_value=45.0),
        ),
    ):
        yield


def test_brand_shopping_contract_happy_path(client):
    """All brand-shopping contracts return stable success schemas."""
    product_response = client.get("/api/catalog/products/SKU-100")
    profile_response = client.get("/api/customers/customer-100/profile")
    offers_response = client.post(
        "/api/pricing/offers",
        json={"customer_id": "customer-100", "sku": "SKU-100", "quantity": 3},
    )
    rank_response = client.post(
        "/api/recommendations/rank",
        json={
            "customer_id": "customer-100",
            "candidates": [
                {"sku": "SKU-100", "score": 0.5},
                {"sku": "SKU-101", "score": 0.6},
            ],
        },
    )
    compose_response = client.post(
        "/api/recommendations/compose",
        json={
            "customer_id": "customer-100",
            "ranked_items": [{"sku": "SKU-100", "score": 0.8}],
            "max_items": 1,
        },
    )

    assert product_response.status_code == 200
    assert profile_response.status_code == 200
    assert offers_response.status_code == 200
    assert rank_response.status_code == 200
    assert compose_response.status_code == 200

    assert product_response.json()["sku"] == "SKU-100"
    assert profile_response.json()["customer_id"] == "customer-100"
    assert offers_response.json()["final_price"] == 120.0
    assert len(rank_response.json()["ranked"]) == 2
    assert len(compose_response.json()["recommendations"]) == 1


def test_brand_shopping_contract_validation_failures(client):
    """Contract endpoints return deterministic validation errors for invalid payloads."""
    invalid_sku = client.get("/api/catalog/products/sku invalid")
    invalid_profile = client.get("/api/customers/customer invalid/profile")
    invalid_offers = client.post(
        "/api/pricing/offers",
        json={"customer_id": "customer-100", "sku": "SKU-100", "quantity": 0},
    )
    invalid_rank = client.post(
        "/api/recommendations/rank",
        json={"customer_id": "customer-100", "candidates": []},
    )
    invalid_compose = client.post(
        "/api/recommendations/compose",
        json={
            "customer_id": "customer-100",
            "ranked_items": [{"sku": "SKU-100", "score": 0.7}],
            "max_items": 0,
        },
    )

    assert invalid_sku.status_code == 422
    assert invalid_profile.status_code == 422
    assert invalid_offers.status_code == 422
    assert invalid_rank.status_code == 422
    assert invalid_compose.status_code == 422


def test_brand_shopping_contract_not_found_paths(client):
    """Contract endpoints return deterministic not-found errors."""
    async def _staff_user():
        return User(
            user_id="staff-100",
            email="staff100@example.com",
            name="Staff 100",
            roles=["staff"],
        )

    app.dependency_overrides[get_current_user] = _staff_user

    with (
        patch(
            "crud_service.routes.brand_shopping.product_repo.get_by_id",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "crud_service.routes.brand_shopping.user_repo.get_by_id",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "crud_service.routes.brand_shopping.user_repo.get_by_entra_id",
            new=AsyncMock(return_value=None),
        ),
    ):
        product_not_found = client.get("/api/catalog/products/SKU-404")
        profile_not_found = client.get("/api/customers/customer-404/profile")
        offers_not_found = client.post(
            "/api/pricing/offers",
            json={"customer_id": "customer-404", "sku": "SKU-404", "quantity": 1},
        )
        rank_not_found = client.post(
            "/api/recommendations/rank",
            json={"customer_id": "customer-404", "candidates": [{"sku": "SKU-404", "score": 0.5}]},
        )
        compose_not_found = client.post(
            "/api/recommendations/compose",
            json={"customer_id": "customer-404", "ranked_items": [{"sku": "SKU-404", "score": 0.5}]},
        )

    assert product_not_found.status_code == 404
    assert profile_not_found.status_code == 404
    assert offers_not_found.status_code == 404
    assert rank_not_found.status_code == 404
    assert compose_not_found.status_code == 404


def test_customer_profile_forbidden_for_non_owner_customer(client):
    """Customer profile route blocks non-owner customer access."""
    response = client.get("/api/customers/customer-200/profile")

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


def test_brand_shopping_post_routes_forbidden_for_non_owner_customer(client):
    """Customer users cannot access other customers' pricing/recommendation contracts."""
    offers_response = client.post(
        "/api/pricing/offers",
        json={"customer_id": "customer-200", "sku": "SKU-100", "quantity": 1},
    )
    rank_response = client.post(
        "/api/recommendations/rank",
        json={
            "customer_id": "customer-200",
            "candidates": [{"sku": "SKU-100", "score": 0.5}],
        },
    )
    compose_response = client.post(
        "/api/recommendations/compose",
        json={
            "customer_id": "customer-200",
            "ranked_items": [{"sku": "SKU-100", "score": 0.5}],
            "max_items": 1,
        },
    )

    assert offers_response.status_code == 403
    assert rank_response.status_code == 403
    assert compose_response.status_code == 403


def test_brand_shopping_post_routes_require_authentication(client):
    """Pricing and recommendation contract POST endpoints require auth."""
    app.dependency_overrides.pop(get_current_user, None)

    offers_response = client.post(
        "/api/pricing/offers",
        json={"customer_id": "customer-100", "sku": "SKU-100", "quantity": 1},
    )
    rank_response = client.post(
        "/api/recommendations/rank",
        json={
            "customer_id": "customer-100",
            "candidates": [{"sku": "SKU-100", "score": 0.5}],
        },
    )
    compose_response = client.post(
        "/api/recommendations/compose",
        json={
            "customer_id": "customer-100",
            "ranked_items": [{"sku": "SKU-100", "score": 0.5}],
            "max_items": 1,
        },
    )

    assert offers_response.status_code == 401
    assert rank_response.status_code == 401
    assert compose_response.status_code == 401
