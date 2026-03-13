"""Integration tests for staff ticket lifecycle APIs."""

from unittest.mock import AsyncMock, patch

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _override_staff_auth():
    async def _staff_user():
        return User(
            user_id="staff-1",
            email="staff@example.com",
            name="Staff User",
            roles=["staff"],
        )

    app.dependency_overrides[get_current_user] = _staff_user
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _mock_ticket_repo():
    store: dict[str, dict] = {}

    async def fake_query(*args, **kwargs):
        del args, kwargs
        return sorted(
            [dict(item) for item in store.values()],
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )

    async def fake_get(ticket_id, partition_key=None):
        del partition_key
        item = store.get(ticket_id)
        return dict(item) if item else None

    async def fake_create(item):
        store[item["id"]] = dict(item)
        return dict(item)

    async def fake_update(item):
        store[item["id"]] = dict(item)
        return dict(item)

    with (
        patch("crud_service.routes.staff.tickets.ticket_repo.query", new=AsyncMock(side_effect=fake_query)),
        patch("crud_service.routes.staff.tickets.ticket_repo.get_by_id", new=AsyncMock(side_effect=fake_get)),
        patch("crud_service.routes.staff.tickets.ticket_repo.create", new=AsyncMock(side_effect=fake_create)),
        patch("crud_service.routes.staff.tickets.ticket_repo.update", new=AsyncMock(side_effect=fake_update)),
    ):
        yield


@pytest.fixture(name="client")
def fixture_client():
    with TestClient(app) as test_client:
        yield test_client


def test_staff_ticket_lifecycle_flow(client):
    """Create -> update -> escalate -> resolve flow is fully supported."""
    create_response = client.post(
        "/api/staff/tickets",
        json={
            "user_id": "customer-7",
            "subject": "Order not delivered",
            "priority": "medium",
            "description": "Carrier status has not changed",
        },
    )
    assert create_response.status_code == 201
    ticket_id = create_response.json()["id"]

    update_response = client.patch(
        f"/api/staff/tickets/{ticket_id}",
        json={
            "status": "in_progress",
            "assignee_id": "staff-1",
            "note": "Investigating with carrier",
            "reason": "Investigation started",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "in_progress"

    escalate_response = client.post(
        f"/api/staff/tickets/{ticket_id}/escalate",
        json={"reason": "Need logistics manager review"},
    )
    assert escalate_response.status_code == 200
    assert escalate_response.json()["status"] == "escalated"

    resolve_response = client.post(
        f"/api/staff/tickets/{ticket_id}/resolve",
        json={
            "reason": "Carrier confirmed delivery and customer acknowledged",
            "resolution_note": "Delivered at front desk",
        },
    )
    assert resolve_response.status_code == 200
    resolved = resolve_response.json()
    assert resolved["status"] == "resolved"
    assert resolved["resolution_note"] == "Delivered at front desk"

    get_response = client.get(f"/api/staff/tickets/{ticket_id}")
    assert get_response.status_code == 200
    ticket = get_response.json()
    assert len(ticket["status_history"]) >= 4
    actions = [entry["action"] for entry in ticket["audit_log"]]
    assert "created" in actions
    assert "updated" in actions
    assert "escalated" in actions
    assert "resolved" in actions
