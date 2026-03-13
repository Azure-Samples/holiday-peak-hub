"""Unit tests for brand shopping contract routes."""

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from crud_service.routes import brand_shopping
from fastapi.testclient import TestClient


@pytest.fixture(name="test_client")
def fixture_test_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def _override_auth():
    async def _customer_user():
        return User(
            user_id="customer-1",
            email="customer1@example.com",
            name="Customer One",
            roles=["customer"],
        )

    app.dependency_overrides[get_current_user] = _customer_user
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_catalog_product_success(test_client, monkeypatch):
    """Returns canonical product contract for valid SKU."""

    async def fake_get_by_id(_sku):
        return {
            "id": "SKU-1",
            "name": "Runner Shoe",
            "description": "Comfort-focused running shoe",
            "category_id": "footwear",
            "price": 129.99,
            "in_stock": True,
        }

    monkeypatch.setattr(brand_shopping.product_repo, "get_by_id", fake_get_by_id)

    response = test_client.get("/api/catalog/products/SKU-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sku"] == "SKU-1"
    assert payload["price"] == 129.99
    assert payload["currency"] == "usd"


@pytest.mark.asyncio
async def test_get_catalog_product_validation_failure(test_client):
    """SKU path validation rejects invalid characters."""
    response = test_client.get("/api/catalog/products/sku with spaces")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_catalog_product_incomplete_contract_returns_503(test_client, monkeypatch):
    """Missing required catalog fields returns deterministic service error."""

    async def fake_get_by_id(_sku):
        return {
            "id": "SKU-1",
            "name": "",
            "description": "Missing name should fail",
            "category_id": "footwear",
            "price": 129.99,
            "in_stock": True,
        }

    monkeypatch.setattr(brand_shopping.product_repo, "get_by_id", fake_get_by_id)

    response = test_client.get("/api/catalog/products/SKU-1")

    assert response.status_code == 503
    assert response.json()["detail"] == "Catalog product contract is incomplete"


@pytest.mark.asyncio
async def test_get_customer_profile_success(test_client, monkeypatch):
    """Returns profile with CRM + personalization payloads when available."""

    async def fake_resolve(_customer_id):
        return {
            "id": "customer-1",
            "email": "customer@example.com",
            "name": "Customer One",
            "phone": "+5511999999999",
        }

    class FakeAgent:
        async def get_customer_profile(self, _customer_id):
            return {"tier": "gold"}

        async def get_personalization(self, _customer_id):
            return {"preferred_categories": ["footwear"]}

    monkeypatch.setattr(brand_shopping, "_resolve_user_profile", fake_resolve)
    monkeypatch.setattr(brand_shopping, "agent_client", FakeAgent())

    response = test_client.get("/api/customers/customer-1/profile")

    assert response.status_code == 200
    payload = response.json()
    assert payload["customer_id"] == "customer-1"
    assert payload["tier"] == "gold"
    assert payload["personalization"]["preferred_categories"] == ["footwear"]


@pytest.mark.asyncio
async def test_get_customer_profile_validation_failure(test_client):
    """Customer id validation rejects invalid characters."""
    response = test_client.get("/api/customers/customer id/profile")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_customer_profile_forbidden_for_non_owner_customer(test_client, monkeypatch):
    """Non-owner customers cannot read arbitrary customer profiles."""

    async def fake_resolve(_customer_id):
        return {
            "id": "customer-2",
            "email": "customer2@example.com",
            "name": "Customer Two",
            "phone": "+5511888888888",
        }

    monkeypatch.setattr(brand_shopping, "_resolve_user_profile", fake_resolve)

    response = test_client.get("/api/customers/customer-2/profile")

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


@pytest.mark.asyncio
async def test_pricing_offers_success(test_client, monkeypatch):
    """Returns deterministic pricing offers and final price."""

    async def fake_product(_sku):
        return {
            "id": "SKU-2",
            "name": "Winter Jacket",
            "description": "Insulated",
            "category_id": "outerwear",
            "price": 100.0,
            "in_stock": True,
        }

    async def fake_resolve(_customer_id):
        return {"id": "customer-1", "tier": "gold"}

    class FakeAgent:
        async def get_customer_profile(self, _customer_id):
            return {"tier": "gold"}

        async def calculate_dynamic_pricing(self, _sku):
            return 90.0

    monkeypatch.setattr(brand_shopping.product_repo, "get_by_id", fake_product)
    monkeypatch.setattr(brand_shopping, "_resolve_user_profile", fake_resolve)
    monkeypatch.setattr(brand_shopping, "agent_client", FakeAgent())

    response = test_client.post(
        "/api/pricing/offers",
        json={"customer_id": "customer-1", "sku": "SKU-2", "quantity": 5},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_price"] == 500.0
    assert payload["final_price"] == 350.0
    assert {offer["offer_type"] for offer in payload["offers"]} == {
        "bulk",
        "loyalty",
        "dynamic",
    }


@pytest.mark.asyncio
async def test_pricing_offers_validation_failure(test_client):
    """Request rejects unknown fields and invalid quantity."""
    response = test_client.post(
        "/api/pricing/offers",
        json={
            "customer_id": "customer-2",
            "sku": "SKU-2",
            "quantity": 0,
            "unexpected": True,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pricing_offers_rejects_invalid_identifier(test_client):
    """Request rejects invalid customer identifier pattern."""
    response = test_client.post(
        "/api/pricing/offers",
        json={"customer_id": "customer with spaces", "sku": "SKU-2", "quantity": 1},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_pricing_offers_forbidden_for_non_owner_customer(test_client):
    """Customer role cannot request offers for a different customer id."""
    response = test_client.post(
        "/api/pricing/offers",
        json={"customer_id": "customer-2", "sku": "SKU-2", "quantity": 1},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


@pytest.mark.asyncio
async def test_pricing_offers_requires_authentication(test_client):
    """Offers endpoint requires authenticated user context."""
    app.dependency_overrides.pop(get_current_user, None)

    response = test_client.post(
        "/api/pricing/offers",
        json={"customer_id": "customer-1", "sku": "SKU-2", "quantity": 1},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_rank_recommendations_success(test_client, monkeypatch):
    """Ranks candidates with deterministic score ordering."""

    async def fake_resolve(_customer_id):
        return {"id": "customer-1"}

    async def fake_product(sku):
        if sku == "sku-a":
            return {"id": sku, "category_id": "shoes", "in_stock": True}
        return {"id": sku, "category_id": "accessories", "in_stock": False}

    class FakeAgent:
        async def get_personalization(self, _customer_id):
            return {"preferred_categories": ["shoes"]}

    monkeypatch.setattr(brand_shopping, "_resolve_user_profile", fake_resolve)
    monkeypatch.setattr(brand_shopping.product_repo, "get_by_id", fake_product)
    monkeypatch.setattr(brand_shopping, "agent_client", FakeAgent())

    response = test_client.post(
        "/api/recommendations/rank",
        json={
            "customer_id": "customer-1",
            "candidates": [
                {"sku": "sku-b", "score": 0.8},
                {"sku": "sku-a", "score": 0.7},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["ranked"][0]["sku"] == "sku-a"
    assert payload["ranked"][0]["score"] == 0.85


@pytest.mark.asyncio
async def test_rank_recommendations_deduplicates_by_sku(test_client, monkeypatch):
    """Duplicate SKU candidates are merged with max score before ranking."""

    async def fake_resolve(_customer_id):
        return {"id": "customer-1"}

    async def fake_product(sku):
        return {"id": sku, "category_id": "shoes", "in_stock": True}

    class FakeAgent:
        async def get_personalization(self, _customer_id):
            return {"preferred_categories": []}

    monkeypatch.setattr(brand_shopping, "_resolve_user_profile", fake_resolve)
    monkeypatch.setattr(brand_shopping.product_repo, "get_by_id", fake_product)
    monkeypatch.setattr(brand_shopping, "agent_client", FakeAgent())

    response = test_client.post(
        "/api/recommendations/rank",
        json={
            "customer_id": "customer-1",
            "candidates": [
                {"sku": "sku-a", "score": 0.3},
                {"sku": "sku-a", "score": 0.8},
                {"sku": "sku-b", "score": 0.7},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["ranked"]) == 2
    assert payload["ranked"][0]["sku"] == "sku-a"
    assert payload["ranked"][0]["score"] == 0.8


@pytest.mark.asyncio
async def test_rank_recommendations_validation_failure(test_client):
    """Rank endpoint validates candidate payload shape."""
    response = test_client.post(
        "/api/recommendations/rank",
        json={"customer_id": "customer-3", "candidates": []},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_rank_recommendations_forbidden_for_non_owner_customer(test_client):
    """Customer role cannot rank recommendations for a different customer id."""
    response = test_client.post(
        "/api/recommendations/rank",
        json={
            "customer_id": "customer-2",
            "candidates": [{"sku": "sku-a", "score": 0.7}],
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


@pytest.mark.asyncio
async def test_rank_recommendations_requires_authentication(test_client):
    """Rank endpoint requires authenticated user context."""
    app.dependency_overrides.pop(get_current_user, None)

    response = test_client.post(
        "/api/recommendations/rank",
        json={
            "customer_id": "customer-1",
            "candidates": [{"sku": "sku-a", "score": 0.5}],
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_compose_recommendations_success(test_client, monkeypatch):
    """Composes recommendation cards with product names when available."""

    async def fake_resolve(_customer_id):
        return {"id": "customer-1"}

    async def fake_product(sku):
        return {"id": sku, "name": f"Name for {sku}"}

    monkeypatch.setattr(brand_shopping, "_resolve_user_profile", fake_resolve)
    monkeypatch.setattr(brand_shopping.product_repo, "get_by_id", fake_product)

    response = test_client.post(
        "/api/recommendations/compose",
        json={
            "customer_id": "customer-1",
            "ranked_items": [{"sku": "sku-1", "score": 0.91}],
            "max_items": 1,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["headline"] == "Top picks for customer-1"
    assert payload["recommendations"][0]["title"] == "Name for sku-1"


@pytest.mark.asyncio
async def test_compose_recommendations_validation_failure(test_client):
    """Compose endpoint enforces strict request schema."""
    response = test_client.post(
        "/api/recommendations/compose",
        json={
            "customer_id": "customer-4",
            "ranked_items": [{"sku": "sku-1", "score": 0.91}],
            "max_items": 0,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_compose_recommendations_deduplicates_by_sku(test_client, monkeypatch):
    """Compose returns unique recommendation SKUs in deterministic order."""

    async def fake_resolve(_customer_id):
        return {"id": "customer-1"}

    async def fake_product(sku):
        return {"id": sku, "name": f"Name for {sku}"}

    monkeypatch.setattr(brand_shopping, "_resolve_user_profile", fake_resolve)
    monkeypatch.setattr(brand_shopping.product_repo, "get_by_id", fake_product)

    response = test_client.post(
        "/api/recommendations/compose",
        json={
            "customer_id": "customer-1",
            "ranked_items": [
                {"sku": "sku-1", "score": 0.6},
                {"sku": "sku-1", "score": 0.9},
                {"sku": "sku-2", "score": 0.7},
            ],
            "max_items": 2,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["sku"] for item in payload["recommendations"]] == ["sku-1", "sku-2"]
    assert payload["recommendations"][0]["score"] == 0.9


@pytest.mark.asyncio
async def test_compose_recommendations_forbidden_for_non_owner_customer(test_client):
    """Customer role cannot compose recommendations for a different customer id."""
    response = test_client.post(
        "/api/recommendations/compose",
        json={
            "customer_id": "customer-2",
            "ranked_items": [{"sku": "sku-1", "score": 0.91}],
            "max_items": 1,
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


@pytest.mark.asyncio
async def test_compose_recommendations_requires_authentication(test_client):
    """Compose endpoint requires authenticated user context."""
    app.dependency_overrides.pop(get_current_user, None)

    response = test_client.post(
        "/api/recommendations/compose",
        json={
            "customer_id": "customer-1",
            "ranked_items": [{"sku": "sku-1", "score": 0.91}],
            "max_items": 1,
        },
    )

    assert response.status_code == 401
