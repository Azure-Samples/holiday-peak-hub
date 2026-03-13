"""Unit tests for staff ticket routes."""

from collections.abc import Awaitable, Callable

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from crud_service.routes.staff import tickets
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


@pytest.fixture(name="ticket_store")
def fixture_ticket_store(monkeypatch):
    store: dict[str, dict] = {}

    async def fake_query(query, parameters=None, partition_key=None):
        del query, parameters, partition_key
        return sorted(
            [dict(item) for item in store.values()],
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )

    async def fake_get(item_id, partition_key=None):
        del partition_key
        item = store.get(item_id)
        return dict(item) if item else None

    async def fake_create(item):
        store[item["id"]] = dict(item)
        return dict(item)

    async def fake_update(item):
        store[item["id"]] = dict(item)
        return dict(item)

    monkeypatch.setattr(tickets.ticket_repo, "query", fake_query)
    monkeypatch.setattr(tickets.ticket_repo, "get_by_id", fake_get)
    monkeypatch.setattr(tickets.ticket_repo, "create", fake_create)
    monkeypatch.setattr(tickets.ticket_repo, "update", fake_update)
    return store


def test_create_ticket_staff_success(test_client, ticket_store):
    """Staff can create a ticket and audit fields are present."""
    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="staff-1",
            email="staff@example.com",
            name="Staff User",
            roles=["staff"],
        )
    )

    response = test_client.post(
        "/api/staff/tickets",
        json={
            "user_id": "customer-1",
            "subject": "Order delay",
            "priority": "medium",
            "description": "Package did not move for 3 days",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "open"
    assert payload["audit_log"][0]["action"] == "created"
    assert payload["status_history"][0]["to"] == "open"
    assert payload["id"] in ticket_store


def test_create_ticket_forbidden_for_customer_role(test_client):
    """Customer role cannot access staff ticket mutation endpoints."""
    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="customer-1",
            email="customer@example.com",
            name="Customer User",
            roles=["customer"],
        )
    )

    response = test_client.post(
        "/api/staff/tickets",
        json={
            "user_id": "customer-1",
            "subject": "Need help",
            "priority": "low",
        },
    )

    assert response.status_code == 403


def test_patch_ticket_invalid_status_transition(test_client, ticket_store):
    """Transitioning from resolved to in_progress returns 409."""
    ticket_store["ticket-1"] = {
        "id": "ticket-1",
        "user_id": "customer-1",
        "subject": "Return request",
        "status": "resolved",
        "priority": "medium",
        "created_at": "2026-03-11T00:00:00+00:00",
        "status_history": [],
        "audit_log": [],
    }

    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="staff-2",
            email="staff2@example.com",
            name="Staff User",
            roles=["staff"],
        )
    )

    response = test_client.patch(
        "/api/staff/tickets/ticket-1",
        json={"status": "in_progress", "reason": "Reopening"},
    )

    assert response.status_code == 409


def test_escalate_then_resolve_lifecycle(test_client, ticket_store):
    """Escalate and resolve endpoints mutate status and preserve audit trail."""
    ticket_store["ticket-2"] = {
        "id": "ticket-2",
        "user_id": "customer-2",
        "subject": "Incorrect charge",
        "status": "open",
        "priority": "low",
        "created_at": "2026-03-11T00:00:00+00:00",
        "status_history": [
            {
                "from": None,
                "to": "open",
                "at": "2026-03-11T00:00:00+00:00",
                "actor_id": "seed",
                "reason": "seed",
            }
        ],
        "audit_log": [],
    }

    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="admin-1",
            email="admin@example.com",
            name="Admin User",
            roles=["admin"],
        )
    )

    escalate_response = test_client.post(
        "/api/staff/tickets/ticket-2/escalate",
        json={"reason": "Potential fraud"},
    )
    resolve_response = test_client.post(
        "/api/staff/tickets/ticket-2/resolve",
        json={"reason": "Issue corrected", "resolution_note": "Refund issued"},
    )

    assert escalate_response.status_code == 200
    escalated = escalate_response.json()
    assert escalated["status"] == "escalated"
    assert escalated["priority"] == "high"

    assert resolve_response.status_code == 200
    resolved = resolve_response.json()
    assert resolved["status"] == "resolved"
    assert resolved["resolution_note"] == "Refund issued"
    actions = [entry["action"] for entry in resolved["audit_log"]]
    assert "escalated" in actions
    assert "resolved" in actions


def test_patch_ticket_rejects_noop_update(test_client, ticket_store):
    """Patch without mutable field changes returns 400."""
    ticket_store["ticket-3"] = {
        "id": "ticket-3",
        "user_id": "customer-3",
        "subject": "Need status",
        "status": "open",
        "priority": "medium",
        "created_at": "2026-03-11T00:00:00+00:00",
        "status_history": [],
        "audit_log": [],
    }

    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="staff-3",
            email="staff3@example.com",
            name="Staff User",
            roles=["staff"],
        )
    )

    response = test_client.patch(
        "/api/staff/tickets/ticket-3",
        json={},
    )

    assert response.status_code == 400
