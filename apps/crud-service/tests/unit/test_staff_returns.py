"""Unit tests for staff return lifecycle routes."""

from collections.abc import Awaitable, Callable

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from crud_service.routes.staff import returns
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
    return_store: dict[str, dict] = {
        "return-1": {
            "id": "return-1",
            "order_id": "order-1",
            "user_id": "customer-1",
            "status": "requested",
            "reason": "Damaged",
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
    }
    refund_store: dict[str, dict] = {}

    async def fake_query(query, parameters=None, partition_key=None):
        del query, parameters, partition_key
        return sorted(
            [dict(item) for item in return_store.values()],
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )

    async def fake_get_return(item_id, partition_key=None):
        del partition_key
        item = return_store.get(item_id)
        return dict(item) if item else None

    async def fake_update_return(item):
        return_store[item["id"]] = dict(item)
        return dict(item)

    async def fake_get_refund_by_return_id(return_id):
        for item in refund_store.values():
            if item.get("return_id") == return_id:
                return dict(item)
        return None

    async def fake_create_refund(item):
        refund_store[item["id"]] = dict(item)
        return dict(item)

    monkeypatch.setattr(returns.return_repo, "query", fake_query)
    monkeypatch.setattr(returns.return_repo, "get_by_id", fake_get_return)
    monkeypatch.setattr(returns.return_repo, "update", fake_update_return)
    monkeypatch.setattr(returns.refund_repo, "get_by_return_id", fake_get_refund_by_return_id)
    monkeypatch.setattr(returns.refund_repo, "create", fake_create_refund)

    published_lifecycle: list[tuple[str, dict]] = []
    published_refunds: list[dict] = []

    async def fake_publish_return_lifecycle_event(*, event_type, data):
        published_lifecycle.append((event_type, dict(data)))

    async def fake_publish_refund_issued(data):
        published_refunds.append(dict(data))

    monkeypatch.setattr(
        returns.event_publisher,
        "publish_return_lifecycle_event",
        fake_publish_return_lifecycle_event,
    )
    monkeypatch.setattr(returns.event_publisher, "publish_refund_issued", fake_publish_refund_issued)

    return {
        "returns": return_store,
        "refunds": refund_store,
        "published_lifecycle": published_lifecycle,
        "published_refunds": published_refunds,
    }


def _as_staff() -> Callable[[], Awaitable[User]]:
    return _override_user(
        User(
            user_id="staff-1",
            email="staff@example.com",
            name="Staff",
            roles=["staff"],
        )
    )


def _as_admin() -> Callable[[], Awaitable[User]]:
    return _override_user(
        User(
            user_id="admin-1",
            email="admin@example.com",
            name="Admin",
            roles=["admin"],
        )
    )


def _as_customer() -> Callable[[], Awaitable[User]]:
    return _override_user(
        User(
            user_id="customer-1",
            email="customer@example.com",
            name="Customer",
            roles=["customer"],
        )
    )


def test_approve_transition_success_and_event_publish(test_client, stores):
    """Requested -> approved transition succeeds and emits one event."""
    app.dependency_overrides[get_current_user] = _as_staff()

    response = test_client.post("/api/staff/returns/return-1/approve", json={"reason": "Valid"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "approved"
    assert payload["approved_at"] is not None
    assert len(stores["published_lifecycle"]) == 1
    assert stores["published_lifecycle"][0][0] == "ReturnApproved"


def test_invalid_transition_returns_conflict(test_client, stores):
    """Invalid deterministic transition returns conflict."""
    del stores
    app.dependency_overrides[get_current_user] = _as_staff()

    response = test_client.post("/api/staff/returns/return-1/restock", json={"reason": "Invalid"})

    assert response.status_code == 409
    assert "Invalid return status transition" in response.json()["detail"]


def test_idempotent_terminal_transition_no_duplicate_event(test_client, stores):
    """Repeating same transition returns idempotent marker and no extra event."""
    app.dependency_overrides[get_current_user] = _as_staff()

    first = test_client.post("/api/staff/returns/return-1/reject", json={"reason": "Policy"})
    second = test_client.post("/api/staff/returns/return-1/reject", json={"reason": "Retry"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["idempotent"] is True
    assert len(stores["published_lifecycle"]) == 1
    assert stores["published_lifecycle"][0][0] == "ReturnRejected"


def test_refund_transition_creates_refund_and_publishes_events(test_client, stores):
    """Restocked -> refunded creates refund record and emits lifecycle/payment events."""
    app.dependency_overrides[get_current_user] = _as_staff()

    stores["returns"]["return-2"] = {
        "id": "return-2",
        "order_id": "order-2",
        "user_id": "customer-2",
        "status": "restocked",
        "reason": "Wrong item",
        "items": [],
        "created_at": "2026-03-12T00:00:00+00:00",
        "updated_at": "2026-03-12T00:30:00+00:00",
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

    response = test_client.post("/api/staff/returns/return-2/refund", json={"reason": "Refunded"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "refunded"
    assert payload["refund"] is not None
    assert payload["refunded_at"] is not None
    assert len(stores["published_refunds"]) == 1
    assert len(stores["published_lifecycle"]) == 1
    assert stores["published_lifecycle"][0][0] == "ReturnRefunded"

    refund_response = test_client.get("/api/staff/returns/return-2/refund")
    assert refund_response.status_code == 200
    assert refund_response.json()["status"] == "issued"


def test_idempotent_refund_repairs_missing_refund_record(test_client, stores):
    """Idempotent refund retry backfills refund record when missing."""
    app.dependency_overrides[get_current_user] = _as_staff()

    stores["returns"]["return-3"] = {
        "id": "return-3",
        "order_id": "order-3",
        "user_id": "customer-3",
        "status": "refunded",
        "reason": "Wrong item",
        "items": [],
        "created_at": "2026-03-12T00:00:00+00:00",
        "updated_at": "2026-03-12T00:45:00+00:00",
        "requested_at": "2026-03-12T00:00:00+00:00",
        "approved_at": "2026-03-12T00:10:00+00:00",
        "rejected_at": None,
        "received_at": "2026-03-12T00:20:00+00:00",
        "restocked_at": "2026-03-12T00:30:00+00:00",
        "refunded_at": "2026-03-12T00:45:00+00:00",
        "last_transition_at": "2026-03-12T00:45:00+00:00",
        "status_history": [],
        "audit_log": [],
    }

    response = test_client.post("/api/staff/returns/return-3/refund", json={"reason": "Retry"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "refunded"
    assert payload["idempotent"] is True
    assert payload["refund"] is not None
    assert payload["refund"]["status"] == "issued"
    assert len(stores["published_refunds"]) == 0
    assert len(stores["published_lifecycle"]) == 0


def test_staff_returns_allow_admin_role(test_client, stores):
    """Staff return routes allow admin in addition to staff."""
    del stores
    app.dependency_overrides[get_current_user] = _as_admin()

    response = test_client.get("/api/staff/returns/")

    assert response.status_code == 200


def test_staff_returns_forbid_customer_role(test_client, stores):
    """Staff return routes reject customer-only users."""
    del stores
    app.dependency_overrides[get_current_user] = _as_customer()

    response = test_client.get("/api/staff/returns/")

    assert response.status_code == 403
    assert response.json()["detail"] == "Role 'staff' or 'admin' required"
