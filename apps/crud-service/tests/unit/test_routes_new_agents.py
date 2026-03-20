"""Unit tests for newly wired CRUD routes (orders, users, cart, products)."""

import httpx
import pytest
from crud_service.auth import User, get_current_user, get_current_user_optional
from crud_service.main import app
from crud_service.routes import cart as cart_routes
from crud_service.routes import orders as orders_routes
from crud_service.routes import products as products_routes
from crud_service.routes import users as users_routes
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


@pytest.fixture
def override_auth_optional():
    """Override optional auth to return None (anonymous access)."""

    async def _override():
        return None

    app.dependency_overrides[get_current_user_optional] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def override_auth_optional_user():
    """Override optional auth to return an authenticated user."""

    async def _override():
        return User(
            user_id="user-1",
            email="user@example.com",
            name="Test User",
            roles=["customer"],
        )

    app.dependency_overrides[get_current_user_optional] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def staff_auth():
    async def _override_user():
        return User(
            user_id="staff-1",
            email="staff@example.com",
            name="Staff User",
            roles=["staff"],
        )

    app.dependency_overrides[get_current_user] = _override_user
    yield
    app.dependency_overrides.clear()


# ── Order Routes ────────────────────────────────────────────────────


class TestOrderGetWithTracking:
    """GET /orders/{id} enriches response with tracking, ETA, carrier."""

    @pytest.mark.asyncio
    async def test_enriched_order(self, client, monkeypatch, override_auth):
        """Should return order enriched with tracking, ETA, and carrier."""

        async def fake_get_by_id(order_id, partition_key=None):
            return {
                "id": order_id,
                "user_id": "user-1",
                "items": [{"product_id": "p1", "quantity": 1, "price": 10.0}],
                "total": 10.0,
                "status": "shipped",
                "created_at": "2025-01-01T00:00:00",
                "tracking_id": "TRACK-123",
            }

        class FakeAgent:
            async def get_order_status(self, order_id):
                return {"status": "in_transit"}

            async def get_delivery_eta(self, tracking_id):
                return {"eta": "2025-01-10T12:00:00Z"}

            async def get_carrier_recommendation(self, tracking_id):
                return {"carrier": "UPS"}

        monkeypatch.setattr(orders_routes.order_repo, "get_by_id", fake_get_by_id)
        monkeypatch.setattr(orders_routes, "agent_client", FakeAgent())

        response = client.get("/api/orders/order-1")
        assert response.status_code == 200
        data = response.json()
        assert data["tracking"]["status"] == "in_transit"
        assert data["eta"]["eta"] == "2025-01-10T12:00:00Z"
        assert data["carrier"]["carrier"] == "UPS"

    @pytest.mark.asyncio
    async def test_order_with_agent_failures(self, client, monkeypatch, override_auth):
        """Should return order without enrichment when agents fail."""

        async def fake_get_by_id(order_id, partition_key=None):
            return {
                "id": order_id,
                "user_id": "user-1",
                "items": [],
                "total": 0.0,
                "status": "pending",
                "created_at": "2025-01-01T00:00:00",
            }

        class FailingAgent:
            async def get_order_status(self, order_id):
                raise httpx.ConnectError("agent timeout")

            async def get_delivery_eta(self, tracking_id):
                raise httpx.ConnectError("agent timeout")

            async def get_carrier_recommendation(self, tracking_id):
                raise httpx.ConnectError("agent timeout")

        monkeypatch.setattr(orders_routes.order_repo, "get_by_id", fake_get_by_id)
        monkeypatch.setattr(orders_routes, "agent_client", FailingAgent())

        response = client.get("/api/orders/order-1")
        assert response.status_code == 200
        data = response.json()
        assert data["tracking"] is None
        assert data["eta"] is None
        assert data["carrier"] is None

    @pytest.mark.asyncio
    async def test_order_unexpected_agent_error_surfaces(self, monkeypatch, override_auth):
        """Unexpected enrichment failures should not be silently swallowed."""

        async def fake_get_by_id(order_id, partition_key=None):
            return {
                "id": order_id,
                "user_id": "user-1",
                "items": [],
                "total": 0.0,
                "status": "pending",
                "created_at": "2025-01-01T00:00:00",
            }

        class BrokenAgent:
            async def get_order_status(self, order_id):
                raise RuntimeError("unexpected mapping bug")

            async def get_delivery_eta(self, tracking_id):
                return None

            async def get_carrier_recommendation(self, tracking_id):
                return None

        test_client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.setattr(orders_routes.order_repo, "get_by_id", fake_get_by_id)
        monkeypatch.setattr(orders_routes, "agent_client", BrokenAgent())

        response = test_client.get("/api/orders/order-1")
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_order_not_found(self, client, monkeypatch, override_auth):

        async def fake_get_by_id(order_id, partition_key=None):
            return None

        monkeypatch.setattr(orders_routes.order_repo, "get_by_id", fake_get_by_id)

        response = client.get("/api/orders/missing")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_order_access_denied(self, client, monkeypatch, override_auth):
        """Non-owner, non-staff users should get 403."""

        async def fake_get_by_id(order_id, partition_key=None):
            return {
                "id": order_id,
                "user_id": "other-user",
                "items": [],
                "total": 0.0,
                "status": "pending",
                "created_at": "2025-01-01T00:00:00",
            }

        monkeypatch.setattr(orders_routes.order_repo, "get_by_id", fake_get_by_id)

        response = client.get("/api/orders/order-1")
        assert response.status_code == 403


class TestOrderReturns:
    """GET /orders/{id}/returns endpoint."""

    @pytest.mark.asyncio
    async def test_returns_plan(self, client, monkeypatch, override_auth):

        async def fake_get_by_id(order_id, partition_key=None):
            return {
                "id": order_id,
                "user_id": "user-1",
                "items": [],
                "total": 0.0,
                "status": "delivered",
                "created_at": "2025-01-01T00:00:00",
                "tracking_id": "TRACK-1",
            }

        class FakeAgent:
            async def get_return_plan(self, tracking_id):
                return {"steps": ["Print label", "Ship"], "refund": 10.0}

        monkeypatch.setattr(orders_routes.order_repo, "get_by_id", fake_get_by_id)
        monkeypatch.setattr(orders_routes, "agent_client", FakeAgent())

        response = client.get("/api/orders/order-1/returns")
        assert response.status_code == 200
        data = response.json()
        assert data["order_id"] == "order-1"
        assert data["plan"]["refund"] == 10.0

    @pytest.mark.asyncio
    async def test_returns_plan_agent_unavailable(self, client, monkeypatch, override_auth):

        async def fake_get_by_id(order_id, partition_key=None):
            return {
                "id": order_id,
                "user_id": "user-1",
                "items": [],
                "total": 0.0,
                "status": "delivered",
                "created_at": "2025-01-01T00:00:00",
            }

        class FakeAgent:
            async def get_return_plan(self, tracking_id):
                return None

        monkeypatch.setattr(orders_routes.order_repo, "get_by_id", fake_get_by_id)
        monkeypatch.setattr(orders_routes, "agent_client", FakeAgent())

        response = client.get("/api/orders/order-1/returns")
        assert response.status_code == 200
        data = response.json()
        assert data["plan"] is None


# ── User Routes ─────────────────────────────────────────────────────


class TestCrmProfile:
    """GET /users/me/crm endpoint."""

    @pytest.mark.asyncio
    async def test_crm_profile(self, client, monkeypatch, override_auth):

        class FakeAgent:
            async def get_customer_profile(self, contact_id):
                return {"tier": "gold", "ltv": 5000}

            async def get_personalization(self, contact_id):
                return {"segment": "vip", "offers": ["offer-1"]}

        monkeypatch.setattr(users_routes, "agent_client", FakeAgent())

        response = client.get("/api/users/me/crm")
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == "user-1"
        assert data["crm_profile"]["tier"] == "gold"
        assert data["personalization"]["segment"] == "vip"

    @pytest.mark.asyncio
    async def test_crm_profile_agents_unavailable(self, client, monkeypatch, override_auth):

        class FakeAgent:
            async def get_customer_profile(self, contact_id):
                return None

            async def get_personalization(self, contact_id):
                return None

        monkeypatch.setattr(users_routes, "agent_client", FakeAgent())

        response = client.get("/api/users/me/crm")
        assert response.status_code == 200
        data = response.json()
        assert data["crm_profile"] is None
        assert data["personalization"] is None


class TestUserEventPublishing:
    """PATCH /users/me emits UserUpdated event."""

    @pytest.mark.asyncio
    async def test_update_profile_publishes_user_updated(self, client, monkeypatch, override_auth):
        async def fake_get_by_entra_id(_entra_id):
            return {
                "id": "user-1",
                "entra_id": "user-1",
                "email": "user@example.com",
                "name": "Old Name",
                "phone": None,
                "created_at": "2025-01-01T00:00:00Z",
            }

        async def fake_update(user):
            return {
                **user,
                "updated_at": "2025-01-02T00:00:00Z",
            }

        published_events: list[tuple[str, str, dict]] = []

        class FakePublisher:
            async def publish(self, topic, event_type, data):
                published_events.append((topic, event_type, data))

        monkeypatch.setattr(users_routes.user_repo, "get_by_entra_id", fake_get_by_entra_id)
        monkeypatch.setattr(users_routes.user_repo, "update", fake_update)
        monkeypatch.setattr(users_routes, "event_publisher", FakePublisher())

        response = client.patch("/api/users/me", json={"name": "New Name", "phone": "555-0000"})
        assert response.status_code == 200
        assert response.json()["name"] == "New Name"
        assert published_events
        topic, event_type, payload = published_events[0]
        assert topic == "user-events"
        assert event_type == "UserUpdated"
        assert payload["user_id"] == "user-1"


# ── Cart Routes ─────────────────────────────────────────────────────


class TestCartReservationValidation:
    """POST /cart/items validates reservation before adding."""

    @pytest.mark.asyncio
    async def test_adds_item_with_valid_reservation(self, client, monkeypatch, override_auth):

        async def fake_product(product_id):
            return {"id": product_id, "name": "Widget", "price": 9.99}

        async def fake_cart(user_id):
            return None

        async def fake_update(cart):
            pass

        class FakeAgent:
            async def validate_reservation(self, sku, quantity):
                return {"valid": True}

        published_reservations: list[dict] = []

        class FakePublisher:
            async def publish_inventory_reserved(self, reservation):
                published_reservations.append(reservation)

        monkeypatch.setattr(cart_routes.product_repo, "get_by_id", fake_product)
        monkeypatch.setattr(cart_routes.cart_repo, "get_by_user", fake_cart)
        monkeypatch.setattr(cart_routes.cart_repo, "update", fake_update)
        monkeypatch.setattr(cart_routes, "agent_client", FakeAgent())
        monkeypatch.setattr(cart_routes, "event_publisher", FakePublisher())

        response = client.post("/api/cart/items", json={"product_id": "p1", "quantity": 2})
        assert response.status_code == 200
        assert response.json()["message"] == "Item added to cart"
        assert published_reservations
        assert published_reservations[0]["user_id"] == "user-1"
        assert published_reservations[0]["sku"] == "p1"

    @pytest.mark.asyncio
    async def test_rejects_invalid_reservation(self, client, monkeypatch, override_auth):

        async def fake_product(product_id):
            return {"id": product_id, "name": "Widget", "price": 9.99}

        class FakeAgent:
            async def validate_reservation(self, sku, quantity):
                return {"valid": False, "reason": "Insufficient stock"}

        monkeypatch.setattr(cart_routes.product_repo, "get_by_id", fake_product)
        monkeypatch.setattr(cart_routes, "agent_client", FakeAgent())

        response = client.post("/api/cart/items", json={"product_id": "p1", "quantity": 100})
        assert response.status_code == 409
        assert "Insufficient stock" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_continues_when_agent_unavailable(self, client, monkeypatch, override_auth):
        """Should add item even if reservation agent is unreachable."""

        async def fake_product(product_id):
            return {"id": product_id, "name": "Widget", "price": 9.99}

        async def fake_cart(user_id):
            return None

        async def fake_update(cart):
            pass

        class FakeAgent:
            async def validate_reservation(self, sku, quantity):
                raise httpx.ConnectError("agent down")

        monkeypatch.setattr(cart_routes.product_repo, "get_by_id", fake_product)
        monkeypatch.setattr(cart_routes.cart_repo, "get_by_user", fake_cart)
        monkeypatch.setattr(cart_routes.cart_repo, "update", fake_update)
        monkeypatch.setattr(cart_routes, "agent_client", FakeAgent())

        response = client.post("/api/cart/items", json={"product_id": "p1", "quantity": 1})
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_logs_publish_failure_but_still_succeeds(
        self, client, monkeypatch, override_auth, caplog
    ):
        """Fire-and-forget reservation publish failures should be logged."""

        async def fake_product(product_id):
            return {"id": product_id, "name": "Widget", "price": 9.99}

        async def fake_cart(user_id):
            return None

        async def fake_update(cart):
            pass

        class FakeAgent:
            async def validate_reservation(self, sku, quantity):
                return {"valid": True}

        class FailingPublisher:
            async def publish_inventory_reserved(self, reservation):
                raise RuntimeError("event-hub unavailable")

        monkeypatch.setattr(cart_routes.product_repo, "get_by_id", fake_product)
        monkeypatch.setattr(cart_routes.cart_repo, "get_by_user", fake_cart)
        monkeypatch.setattr(cart_routes.cart_repo, "update", fake_update)
        monkeypatch.setattr(cart_routes, "agent_client", FakeAgent())
        monkeypatch.setattr(cart_routes, "event_publisher", FailingPublisher())

        with caplog.at_level("WARNING"):
            response = client.post("/api/cart/items", json={"product_id": "p1", "quantity": 1})

        assert response.status_code == 200
        assert "Inventory reservation publish failed" in caplog.text


# ── Product Routes ──────────────────────────────────────────────────


class TestProductSemanticSearch:
    """GET /products with search uses semantic search agent first."""

    @pytest.mark.asyncio
    async def test_semantic_search_used(self, client, monkeypatch, override_auth_optional):

        class FakeAgent:
            async def semantic_search(self, query, limit=20):
                return [
                    {
                        "id": "p1",
                        "name": "Smart Widget",
                        "description": "AI-powered",
                        "price": 19.99,
                        "category_id": "cat-1",
                    }
                ]

            async def get_user_recommendations(self, user_id=None):
                return None

        monkeypatch.setattr(products_routes, "agent_client", FakeAgent())

        response = client.get("/api/products", params={"search": "widget"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Smart Widget"

    @pytest.mark.asyncio
    async def test_falls_back_to_keyword_search(self, client, monkeypatch, override_auth_optional):
        """When semantic search returns nothing, falls back to keyword."""

        class FakeAgent:
            async def semantic_search(self, query, limit=20):
                return []

            async def get_user_recommendations(self, user_id=None):
                return None

        async def fake_search_by_name(query, limit=20):
            return [
                {
                    "id": "p2",
                    "name": "Basic Widget",
                    "description": "Simple",
                    "price": 5.0,
                    "category_id": "cat-1",
                }
            ]

        monkeypatch.setattr(products_routes, "agent_client", FakeAgent())
        monkeypatch.setattr(products_routes.product_repo, "search_by_name", fake_search_by_name)

        response = client.get("/api/products", params={"search": "widget"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Basic Widget"

    @pytest.mark.asyncio
    async def test_accepts_acp_shape_and_normalizes(
        self, client, monkeypatch, override_auth_optional
    ):
        """ACP-shaped result payloads should normalize to CRUD ProductResponse."""

        class FakeAgent:
            async def semantic_search(self, query, limit=20):
                return [
                    {
                        "item_id": "sku-77",
                        "title": "ACP Widget",
                        "description": "ACP enriched",
                        "price": "11.50 usd",
                        "category": "cat-acp",
                        "image_url": "https://example.com/widget.png",
                    }
                ]

            async def get_user_recommendations(self, user_id=None):
                return None

        monkeypatch.setattr(products_routes, "agent_client", FakeAgent())

        response = client.get("/api/products", params={"search": "widget"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "sku-77"
        assert data[0]["name"] == "ACP Widget"
        assert data[0]["price"] == 11.5
        assert data[0]["category_id"] == "cat-acp"

    @pytest.mark.asyncio
    async def test_agent_failure_falls_back_to_keyword(
        self, client, monkeypatch, override_auth_optional
    ):
        """When semantic agent raises, falls back to keyword search."""

        class FakeAgent:
            async def semantic_search(self, query, limit=20):
                raise httpx.ConnectError("agent down")

            async def get_user_recommendations(self, user_id=None):
                return None

        async def fake_search_by_name(query, limit=20):
            return [
                {
                    "id": "p3",
                    "name": "Fallback Widget",
                    "description": "Fallback",
                    "price": 7.0,
                    "category_id": "cat-1",
                }
            ]

        monkeypatch.setattr(products_routes, "agent_client", FakeAgent())
        monkeypatch.setattr(products_routes.product_repo, "search_by_name", fake_search_by_name)

        response = client.get("/api/products", params={"search": "widget"})
        assert response.status_code == 200
        data = response.json()
        assert data[0]["name"] == "Fallback Widget"


class TestProductErrorSurfacing:
    """Unexpected product enrichment errors should surface."""

    @pytest.mark.asyncio
    async def test_unexpected_enrichment_error_surfaces(self, monkeypatch, override_auth_optional):
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

        class BrokenAgent:
            async def get_product_enrichment(self, sku: str):
                raise RuntimeError("unexpected enrichment bug")

            async def calculate_dynamic_pricing(self, sku: str):
                return None

        test_client = TestClient(app, raise_server_exceptions=False)
        monkeypatch.setattr(products_routes.product_repo, "get_by_id", fake_get_by_id)
        monkeypatch.setattr(products_routes, "agent_client", BrokenAgent())

        response = test_client.get("/api/products/prod-1")
        assert response.status_code == 500


class TestProductPersonalization:
    """GET /products reorders results for authenticated users."""

    @pytest.mark.asyncio
    async def test_personalized_ordering(self, client, monkeypatch, override_auth_optional_user):
        """Boosted SKUs should appear first."""

        async def fake_query(query, parameters=None):
            return [
                {
                    "id": "p1",
                    "name": "A",
                    "description": "d",
                    "price": 1,
                    "category_id": "c",
                },
                {
                    "id": "p2",
                    "name": "B",
                    "description": "d",
                    "price": 2,
                    "category_id": "c",
                },
                {
                    "id": "p3",
                    "name": "C",
                    "description": "d",
                    "price": 3,
                    "category_id": "c",
                },
            ]

        class FakeAgent:
            async def semantic_search(self, query, limit=20):
                return []

            async def get_user_recommendations(self, user_id=None):
                return {"boosted_skus": ["p3"]}

        monkeypatch.setattr(products_routes.product_repo, "query", fake_query)
        monkeypatch.setattr(products_routes, "agent_client", FakeAgent())

        response = client.get("/api/products")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["id"] == "p3"  # boosted to top
