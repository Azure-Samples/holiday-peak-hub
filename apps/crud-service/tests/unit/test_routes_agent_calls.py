"""Unit tests for CRUD routes that call agent services."""

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from crud_service.routes import cart as cart_routes
from crud_service.routes import checkout as checkout_routes
from crud_service.routes import products as products_routes
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def override_auth():
    async def _override_user():
        return User(
            user_id="user-1",
            email="user@example.com",
            name="Test User",
            roles=["customer"],
        )

    app.dependency_overrides[get_current_user] = _override_user
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_product_enrichment(monkeypatch, client):
    async def fake_get_by_id(product_id: str):
        return {
            "id": product_id,
            "name": "Test Product",
            "description": "Base description",
            "price": 20.0,
            "category_id": "cat-1",
            "image_url": None,
            "in_stock": True,
        }

    class FakeAgentClient:
        async def get_product_enrichment(self, sku: str):
            return {
                "description": "Enriched description",
                "rating": 4.7,
                "review_count": 12,
                "features": ["Feature A"],
                "media": [{"url": "https://example.com/media.png"}],
                "inventory": {"available": True},
                "related": [],
            }

        async def calculate_dynamic_pricing(self, sku: str):
            return 18.5

    monkeypatch.setattr(products_routes.product_repo, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(products_routes, "agent_client", FakeAgentClient())

    response = client.get("/api/products/prod-1")
    assert response.status_code == 200
    payload = response.json()
    assert payload["price"] == 18.5
    assert payload["rating"] == 4.7
    assert payload["description"] == "Enriched description"


@pytest.mark.asyncio
async def test_cart_recommendations(monkeypatch, client, override_auth):
    async def fake_get_by_user(user_id: str):
        return {
            "user_id": user_id,
            "items": [{"product_id": "prod-1", "quantity": 2, "price": 10.0}],
        }

    class FakeAgentClient:
        async def get_user_recommendations(self, user_id: str, items):
            return {"recommendations": ["prod-2"]}

    monkeypatch.setattr(cart_routes.cart_repo, "get_by_user", fake_get_by_user)
    monkeypatch.setattr(cart_routes, "agent_client", FakeAgentClient())

    response = client.get("/api/cart/recommendations")
    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == "user-1"
    assert payload["recommendations"] == {"recommendations": ["prod-2"]}


@pytest.mark.asyncio
async def test_checkout_validation_with_agent(monkeypatch, client, override_auth):
    async def fake_get_by_user(user_id: str):
        return {
            "user_id": user_id,
            "items": [{"product_id": "prod-1", "quantity": 1, "price": 20.0}],
        }

    class FakeAgentClient:
        async def call_endpoint(self, *args, **kwargs):
            return {"validation": {"issues": [{"sku": "prod-1", "type": "out_of_stock"}]}}

    monkeypatch.setattr(checkout_routes.cart_repo, "get_by_user", fake_get_by_user)
    monkeypatch.setattr(checkout_routes, "agent_client", FakeAgentClient())

    response = client.post("/api/checkout/validate")
    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is False
    assert "Product prod-1 is out of stock" in payload["errors"]
