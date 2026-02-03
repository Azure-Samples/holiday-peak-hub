"""Unit tests for CRUD routes error handling and fallback behavior."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from crud_service.main import app
from crud_service.auth import User, get_current_user
from crud_service.routes import products as products_routes
from crud_service.routes import cart as cart_routes
from crud_service.routes import checkout as checkout_routes


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


class TestProductRoutesFallback:
    """Test product routes gracefully handle agent failures."""

    @pytest.mark.asyncio
    async def test_product_get_with_agent_timeout(self, client, monkeypatch):
        """Product details should return base product when agent times out."""

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

        class TimeoutAgentClient:
            async def get_product_enrichment(self, sku: str):
                return None  # Timeout fallback

            async def calculate_dynamic_pricing(self, sku: str):
                return None  # Timeout fallback

        monkeypatch.setattr(products_routes.product_repo, "get_by_id", fake_get_by_id)
        monkeypatch.setattr(products_routes, "agent_client", TimeoutAgentClient())

        response = client.get("/api/products/prod-1")
        assert response.status_code == 200
        payload = response.json()
        # Should return base product data
        assert payload["name"] == "Test Product"
        assert payload["price"] == 20.0  # Original price

    @pytest.mark.asyncio
    async def test_product_not_found(self, client, monkeypatch):
        """Should return 404 when product doesn't exist."""

        async def fake_get_by_id(product_id: str):
            return None

        monkeypatch.setattr(products_routes.product_repo, "get_by_id", fake_get_by_id)

        response = client.get("/api/products/nonexistent")
        assert response.status_code == 404


class TestCartRoutesFallback:
    """Test cart routes gracefully handle agent failures."""

    @pytest.mark.asyncio
    async def test_cart_recommendations_with_agent_failure(
        self, client, monkeypatch, override_auth
    ):
        """Cart recommendations should return empty when agent fails."""

        async def fake_get_by_user(user_id: str):
            return {
                "user_id": user_id,
                "items": [{"product_id": "prod-1", "quantity": 2, "price": 10.0}],
            }

        class FailingAgentClient:
            async def get_user_recommendations(self, user_id: str, items):
                return None  # Agent failure

        monkeypatch.setattr(cart_routes.cart_repo, "get_by_user", fake_get_by_user)
        monkeypatch.setattr(cart_routes, "agent_client", FailingAgentClient())

        response = client.get("/api/cart/recommendations")
        assert response.status_code == 200
        payload = response.json()
        assert payload["user_id"] == "user-1"
        # Should return empty or None recommendations gracefully
        assert payload["recommendations"] is None

    @pytest.mark.asyncio
    async def test_cart_not_found(self, client, monkeypatch, override_auth):
        """Should handle missing cart gracefully."""

        async def fake_get_by_user(user_id: str):
            return None

        monkeypatch.setattr(cart_routes.cart_repo, "get_by_user", fake_get_by_user)

        response = client.get("/api/cart/recommendations")
        assert response.status_code == 404


class TestCheckoutRoutesFallback:
    """Test checkout routes gracefully handle agent failures."""

    @pytest.mark.asyncio
    async def test_checkout_validation_with_agent_failure(
        self, client, monkeypatch, override_auth
    ):
        """Checkout validation should still work when agent fails."""

        async def fake_get_by_user(user_id: str):
            return {
                "user_id": user_id,
                "items": [{"product_id": "prod-1", "quantity": 1, "price": 20.0}],
            }

        class FailingAgentClient:
            async def call_endpoint(self, *args, **kwargs):
                return None  # Agent failure

        monkeypatch.setattr(checkout_routes.cart_repo, "get_by_user", fake_get_by_user)
        monkeypatch.setattr(checkout_routes, "agent_client", FailingAgentClient())

        response = client.post("/api/checkout/validate")
        assert response.status_code == 200
        payload = response.json()
        # Should proceed with fallback validation
        assert "valid" in payload

    @pytest.mark.asyncio
    async def test_checkout_validation_ready_cart(
        self, client, monkeypatch, override_auth
    ):
        """Checkout validation should pass for ready cart."""

        async def fake_get_by_user(user_id: str):
            return {
                "user_id": user_id,
                "items": [{"product_id": "prod-1", "quantity": 1, "price": 20.0}],
            }

        class SuccessAgentClient:
            async def call_endpoint(self, *args, **kwargs):
                return {"validation": {"issues": []}}  # No issues

        monkeypatch.setattr(checkout_routes.cart_repo, "get_by_user", fake_get_by_user)
        monkeypatch.setattr(checkout_routes, "agent_client", SuccessAgentClient())

        response = client.post("/api/checkout/validate")
        assert response.status_code == 200
        payload = response.json()
        assert payload["valid"] is True
        assert len(payload["errors"]) == 0

    @pytest.mark.asyncio
    async def test_checkout_validation_multiple_issues(
        self, client, monkeypatch, override_auth
    ):
        """Checkout validation should report all issues."""

        async def fake_get_by_user(user_id: str):
            return {
                "user_id": user_id,
                "items": [
                    {"product_id": "prod-1", "quantity": 1, "price": 20.0},
                    {"product_id": "prod-2", "quantity": 2, "price": 30.0},
                ],
            }

        class MultiIssueAgentClient:
            async def call_endpoint(self, *args, **kwargs):
                return {
                    "validation": {
                        "issues": [
                            {"sku": "prod-1", "type": "out_of_stock"},
                            {"sku": "prod-2", "type": "insufficient_stock", "available": 1},
                        ]
                    }
                }

        monkeypatch.setattr(checkout_routes.cart_repo, "get_by_user", fake_get_by_user)
        monkeypatch.setattr(checkout_routes, "agent_client", MultiIssueAgentClient())

        response = client.post("/api/checkout/validate")
        assert response.status_code == 200
        payload = response.json()
        assert payload["valid"] is False
        assert len(payload["errors"]) == 2


class TestProductSearchRoutes:
    """Test product search routes."""

    @pytest.mark.asyncio
    async def test_search_products_returns_results(self, client, monkeypatch):
        """Search should return matching products."""

        async def fake_search(query: str, limit: int = 10):
            return [
                {
                    "id": "prod-1",
                    "name": "Test Product",
                    "description": "A test product",
                    "price": 20.0,
                    "category_id": "cat-1",
                }
            ]

        monkeypatch.setattr(products_routes.product_repo, "search", fake_search)

        response = client.get("/api/products", params={"q": "test"})
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) >= 1

    @pytest.mark.asyncio
    async def test_search_products_empty_results(self, client, monkeypatch):
        """Search should return empty list for no matches."""

        async def fake_search(query: str, limit: int = 10):
            return []

        monkeypatch.setattr(products_routes.product_repo, "search", fake_search)

        response = client.get("/api/products", params={"q": "nonexistent"})
        assert response.status_code == 200
        payload = response.json()
        assert len(payload) == 0
