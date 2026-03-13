"""Unit tests for customer returns routes."""

from collections.abc import Awaitable, Callable

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from crud_service.routes import returns
from fastapi.testclient import TestClient


@pytest.fixture(name="test_client")
def fixture_test_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    yield
    app.dependency_overrides.clear()


def _override_user(user: User) -> Callable[[], Awaitable[User]]:
    async def _provider() -> User:
        return user

    return _provider


@pytest.fixture(name="stores")
def fixture_stores(monkeypatch):
    order_store = {
        "order-1": {
            "id": "order-1",
            "user_id": "customer-1",
            "status": "delivered",
        }
    }
    return_store: dict[str, dict] = {}
    refund_store: dict[str, dict] = {}

    async def fake_get_order(order_id, partition_key=None):
        del partition_key
        order = order_store.get(order_id)
        return dict(order) if order else None

    async def fake_create_return(item):
        return_store[item["id"]] = dict(item)
        return dict(item)

    async def fake_get_return(item_id, partition_key=None):
        del partition_key
        item = return_store.get(item_id)
        return dict(item) if item else None

    async def fake_get_returns_by_user(user_id, limit=100):
        del limit
        return [
            dict(item)
            for item in return_store.values()
            if item.get("user_id") == user_id
        ]

    async def fake_get_refund_by_return_id(return_id):
        for item in refund_store.values():
            if item.get("return_id") == return_id:
                return dict(item)
        return None

    monkeypatch.setattr(returns.order_repo, "get_by_id", fake_get_order)
    monkeypatch.setattr(returns.return_repo, "create", fake_create_return)
    monkeypatch.setattr(returns.return_repo, "get_by_id", fake_get_return)
    monkeypatch.setattr(returns.return_repo, "get_by_user", fake_get_returns_by_user)
    monkeypatch.setattr(returns.refund_repo, "get_by_return_id", fake_get_refund_by_return_id)

    published: list[tuple[str, dict]] = []

    async def fake_publish_return_lifecycle_event(*, event_type, data):
        published.append((event_type, dict(data)))

    monkeypatch.setattr(
        returns.event_publisher,
        "publish_return_lifecycle_event",
        fake_publish_return_lifecycle_event,
    )

    return {
        "orders": order_store,
        "returns": return_store,
        "refunds": refund_store,
        "published": published,
    }


def test_create_return_success_sets_requested_state_and_publishes_event(test_client, stores):
    """Customer return creation persists requested state with SLA timestamps."""
    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="customer-1",
            email="customer@example.com",
            name="Customer",
            roles=["customer"],
        )
    )

    response = test_client.post(
        "/api/returns",
        json={"order_id": "order-1", "reason": "Damaged", "items": [{"sku": "SKU-1"}]},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "requested"
    assert payload["requested_at"] is not None
    assert payload["last_transition_at"] == payload["requested_at"]
    assert len(stores["published"]) == 1
    assert stores["published"][0][0] == "ReturnRequested"


def test_create_return_validation_failure(test_client):
    """Missing required request fields returns validation error."""
    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="customer-1",
            email="customer@example.com",
            name="Customer",
            roles=["customer"],
        )
    )

    response = test_client.post(
        "/api/returns",
        json={"order_id": "order-1"},
    )

    assert response.status_code == 422


def test_get_return_forbidden_when_not_owner(test_client, stores):
    """Customers cannot read returns that belong to another user."""
    return_id = "return-1"
    stores["returns"][return_id] = {
        "id": return_id,
        "order_id": "order-1",
        "user_id": "customer-2",
        "status": "requested",
        "reason": "wrong size",
        "items": [],
        "created_at": "2026-03-12T00:00:00+00:00",
        "updated_at": "2026-03-12T00:00:00+00:00",
        "requested_at": "2026-03-12T00:00:00+00:00",
        "approved_at": None,
        "rejected_at": None,
        "received_at": None,
        "restocked_at": None,
        "refunded_at": None,
        "last_transition_at": "2026-03-12T00:00:00+00:00",
        "status_history": [],
        "audit_log": [],
    }

    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="customer-1",
            email="customer@example.com",
            name="Customer",
            roles=["customer"],
        )
    )

    response = test_client.get(f"/api/returns/{return_id}")
    assert response.status_code == 403


def test_get_refund_progress_not_found(test_client, stores):
    """Refund progression endpoint returns 404 when refund does not exist."""
    return_id = "return-2"
    stores["returns"][return_id] = {
        "id": return_id,
        "order_id": "order-1",
        "user_id": "customer-1",
        "status": "restocked",
        "reason": "wrong size",
        "items": [],
        "created_at": "2026-03-12T00:00:00+00:00",
        "updated_at": "2026-03-12T00:00:00+00:00",
        "requested_at": "2026-03-12T00:00:00+00:00",
        "approved_at": "2026-03-12T00:10:00+00:00",
        "rejected_at": None,
        "received_at": "2026-03-12T00:20:00+00:00",
        "restocked_at": "2026-03-12T00:30:00+00:00",
        "refunded_at": None,
        "last_transition_at": "2026-03-12T00:30:00+00:00",
        "status_history": [],
        "audit_log": [],
    }

    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="customer-1",
            email="customer@example.com",
            name="Customer",
            roles=["customer"],
        )
    )

    response = test_client.get(f"/api/returns/{return_id}/refund")
    assert response.status_code == 404
