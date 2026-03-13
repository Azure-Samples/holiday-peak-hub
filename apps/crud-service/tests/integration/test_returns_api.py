"""Integration tests for customer+staff return/refund lifecycle APIs."""

from unittest.mock import AsyncMock, patch

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from fastapi import Request
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _override_auth():
    async def _auth_override(request: Request) -> User:
        role = request.headers.get("x-role", "customer")
        user_id = request.headers.get("x-user-id", "customer-1")
        roles = ["staff"] if role == "staff" else ["customer"]
        return User(
            user_id=user_id,
            email=f"{user_id}@example.com",
            name=user_id,
            roles=roles,
        )

    app.dependency_overrides[get_current_user] = _auth_override
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _mock_returns_dependencies():
    order_store = {
        "order-1": {
            "id": "order-1",
            "user_id": "customer-1",
            "status": "delivered",
        }
    }
    return_store: dict[str, dict] = {}
    refund_store: dict[str, dict] = {}
    published_lifecycle: list[tuple[str, dict]] = []
    published_refunds: list[dict] = []

    async def fake_get_order(item_id, partition_key=None):
        del partition_key
        item = order_store.get(item_id)
        return dict(item) if item else None

    async def fake_create_return(item):
        return_store[item["id"]] = dict(item)
        return dict(item)

    async def fake_update_return(item):
        return_store[item["id"]] = dict(item)
        return dict(item)

    async def fake_get_return(item_id, partition_key=None):
        del partition_key
        item = return_store.get(item_id)
        return dict(item) if item else None

    async def fake_query_returns(query, parameters=None, partition_key=None):
        del query, parameters, partition_key
        return sorted(
            [dict(item) for item in return_store.values()],
            key=lambda item: item.get("created_at", ""),
            reverse=True,
        )

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

    async def fake_create_refund(item):
        refund_store[item["id"]] = dict(item)
        return dict(item)

    async def fake_publish_return_lifecycle_event(*, event_type, data):
        published_lifecycle.append((event_type, dict(data)))

    async def fake_publish_refund_issued(data):
        published_refunds.append(dict(data))

    with (
        patch(
            "crud_service.routes.returns.order_repo.get_by_id",
            new=AsyncMock(side_effect=fake_get_order),
        ),
        patch(
            "crud_service.routes.returns.return_repo.create",
            new=AsyncMock(side_effect=fake_create_return),
        ),
        patch(
            "crud_service.routes.returns.return_repo.get_by_id",
            new=AsyncMock(side_effect=fake_get_return),
        ),
        patch(
            "crud_service.routes.returns.return_repo.get_by_user",
            new=AsyncMock(side_effect=fake_get_returns_by_user),
        ),
        patch(
            "crud_service.routes.returns.refund_repo.get_by_return_id",
            new=AsyncMock(side_effect=fake_get_refund_by_return_id),
        ),
        patch(
            "crud_service.routes.returns.event_publisher.publish_return_lifecycle_event",
            new=AsyncMock(side_effect=fake_publish_return_lifecycle_event),
        ),
        patch(
            "crud_service.routes.staff.returns.return_repo.query",
            new=AsyncMock(side_effect=fake_query_returns),
        ),
        patch(
            "crud_service.routes.staff.returns.return_repo.get_by_id",
            new=AsyncMock(side_effect=fake_get_return),
        ),
        patch(
            "crud_service.routes.staff.returns.return_repo.update",
            new=AsyncMock(side_effect=fake_update_return),
        ),
        patch(
            "crud_service.routes.staff.returns.refund_repo.get_by_return_id",
            new=AsyncMock(side_effect=fake_get_refund_by_return_id),
        ),
        patch(
            "crud_service.routes.staff.returns.refund_repo.create",
            new=AsyncMock(side_effect=fake_create_refund),
        ),
        patch(
            "crud_service.routes.staff.returns.event_publisher.publish_return_lifecycle_event",
            new=AsyncMock(side_effect=fake_publish_return_lifecycle_event),
        ),
        patch(
            "crud_service.routes.staff.returns.event_publisher.publish_refund_issued",
            new=AsyncMock(side_effect=fake_publish_refund_issued),
        ),
    ):
        yield {
            "returns": return_store,
            "refunds": refund_store,
            "published_lifecycle": published_lifecycle,
            "published_refunds": published_refunds,
        }


@pytest.fixture(name="client")
def fixture_client():
    with TestClient(app) as test_client:
        yield test_client


def test_return_lifecycle_happy_path_with_refund_progression(client, _mock_returns_dependencies):
    """Create -> approve -> receive -> restock -> refund executes fully via API."""
    create_response = client.post(
        "/api/returns",
        headers={"x-role": "customer", "x-user-id": "customer-1"},
        json={"order_id": "order-1", "reason": "Broken item", "items": [{"sku": "SKU-1"}]},
    )
    assert create_response.status_code == 201
    return_id = create_response.json()["id"]

    approve = client.post(
        f"/api/staff/returns/{return_id}/approve",
        headers={"x-role": "staff", "x-user-id": "staff-1"},
        json={"reason": "Validated"},
    )
    receive = client.post(
        f"/api/staff/returns/{return_id}/receive",
        headers={"x-role": "staff", "x-user-id": "staff-1"},
        json={"reason": "Warehouse checked"},
    )
    restock = client.post(
        f"/api/staff/returns/{return_id}/restock",
        headers={"x-role": "staff", "x-user-id": "staff-1"},
        json={"reason": "Restocked"},
    )
    refund = client.post(
        f"/api/staff/returns/{return_id}/refund",
        headers={"x-role": "staff", "x-user-id": "staff-1"},
        json={"reason": "Refund sent"},
    )

    assert approve.status_code == 200
    assert receive.status_code == 200
    assert restock.status_code == 200
    assert refund.status_code == 200
    refund_payload = refund.json()
    assert refund_payload["status"] == "refunded"
    assert refund_payload["refunded_at"] is not None
    assert refund_payload["refund"] is not None

    customer_timeline = client.get(
        f"/api/returns/{return_id}",
        headers={"x-role": "customer", "x-user-id": "customer-1"},
    )
    refund_progress = client.get(
        f"/api/returns/{return_id}/refund",
        headers={"x-role": "customer", "x-user-id": "customer-1"},
    )

    assert customer_timeline.status_code == 200
    assert customer_timeline.json()["status"] == "refunded"
    assert refund_progress.status_code == 200
    assert refund_progress.json()["status"] == "issued"

    lifecycle_event_types = [event_type for event_type, _ in _mock_returns_dependencies["published_lifecycle"]]
    assert lifecycle_event_types == [
        "ReturnRequested",
        "ReturnApproved",
        "ReturnReceived",
        "ReturnRestocked",
        "ReturnRefunded",
    ]
    assert len(_mock_returns_dependencies["published_refunds"]) == 1


def test_invalid_transition_returns_conflict_and_no_event(client, _mock_returns_dependencies):
    """Invalid requested -> restocked transition is rejected and publishes no event."""
    create_response = client.post(
        "/api/returns",
        headers={"x-role": "customer", "x-user-id": "customer-1"},
        json={"order_id": "order-1", "reason": "Wrong size", "items": []},
    )
    assert create_response.status_code == 201
    return_id = create_response.json()["id"]

    invalid = client.post(
        f"/api/staff/returns/{return_id}/restock",
        headers={"x-role": "staff", "x-user-id": "staff-1"},
        json={"reason": "Invalid"},
    )

    assert invalid.status_code == 409
    assert "Invalid return status transition" in invalid.json()["detail"]

    lifecycle_event_types = [event_type for event_type, _ in _mock_returns_dependencies["published_lifecycle"]]
    assert lifecycle_event_types == ["ReturnRequested"]
