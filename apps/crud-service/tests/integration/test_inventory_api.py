"""Integration tests for inventory and reservation APIs."""

from unittest.mock import AsyncMock, patch

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def _override_auth():
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
def _mock_inventory_and_reservation_repos():
    inventory_store: dict[str, dict] = {
        "SKU-100": {
            "id": "SKU-100",
            "sku": "SKU-100",
            "quantity_on_hand": 10,
            "reserved_quantity": 0,
            "available_quantity": 10,
            "reorder_point": 2,
            "safety_stock": 1,
            "low_stock": False,
            "health_status": "healthy",
            "created_at": "2026-03-12T00:00:00+00:00",
            "updated_at": "2026-03-12T00:00:00+00:00",
            "created_by": "seed",
            "updated_by": "seed",
            "audit_log": [],
        }
    }
    reservation_store: dict[str, dict] = {}

    async def fake_inventory_query(*args, **kwargs):
        del args, kwargs
        return [dict(item) for item in inventory_store.values()]

    async def fake_inventory_get(item_id, partition_key=None):
        del partition_key
        item = inventory_store.get(item_id)
        return dict(item) if item else None

    async def fake_inventory_update(item):
        inventory_store[item["id"]] = dict(item)
        return dict(item)

    async def fake_reservation_get(item_id, partition_key=None):
        del partition_key
        item = reservation_store.get(item_id)
        return dict(item) if item else None

    async def fake_reservation_create(item):
        reservation_store[item["id"]] = dict(item)
        return dict(item)

    async def fake_reservation_update(item):
        reservation_store[item["id"]] = dict(item)
        return dict(item)

    with (
        patch(
            "crud_service.routes.inventory.inventory_repo.query",
            new=AsyncMock(side_effect=fake_inventory_query),
        ),
        patch(
            "crud_service.routes.inventory.inventory_repo.get_by_id",
            new=AsyncMock(side_effect=fake_inventory_get),
        ),
        patch(
            "crud_service.routes.inventory.inventory_repo.update",
            new=AsyncMock(side_effect=fake_inventory_update),
        ),
        patch(
            "crud_service.routes.inventory.reservation_repo.get_by_id",
            new=AsyncMock(side_effect=fake_reservation_get),
        ),
        patch(
            "crud_service.routes.inventory.reservation_repo.create",
            new=AsyncMock(side_effect=fake_reservation_create),
        ),
        patch(
            "crud_service.routes.inventory.reservation_repo.update",
            new=AsyncMock(side_effect=fake_reservation_update),
        ),
    ):
        yield


@pytest.fixture(name="client")
def fixture_client():
    with TestClient(app) as test_client:
        yield test_client


def test_inventory_health_and_reservation_flow(client):
    """Health endpoint and create->confirm lifecycle work end-to-end."""
    health_response = client.get("/api/inventory/health")
    assert health_response.status_code == 200
    health_payload = health_response.json()
    assert health_payload["total_skus"] == 1
    assert health_payload["healthy"] == 1

    create_response = client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-100", "quantity": 4, "reason": "checkout hold"},
    )
    assert create_response.status_code == 201
    reservation_id = create_response.json()["id"]

    get_response = client.get(f"/api/inventory/reservations/{reservation_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "created"

    confirm_response = client.post(
        f"/api/inventory/reservations/{reservation_id}/confirm",
        json={"reason": "payment authorized"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"
    assert len(confirm_response.json()["status_history"]) == 2


def test_invalid_transition_and_idempotent_actions(client):
    """Invalid state transitions return conflict; repeated release is idempotent."""
    create_response = client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-100", "quantity": 1},
    )
    reservation_id = create_response.json()["id"]

    release_response = client.post(
        f"/api/inventory/reservations/{reservation_id}/release",
        json={"reason": "manual release"},
    )
    assert release_response.status_code == 200
    assert release_response.json()["status"] == "released"

    idempotent_release = client.post(
        f"/api/inventory/reservations/{reservation_id}/release",
        json={"reason": "retry"},
    )
    assert idempotent_release.status_code == 200
    assert idempotent_release.json()["status"] == "released"

    invalid_confirm = client.post(
        f"/api/inventory/reservations/{reservation_id}/confirm",
        json={"reason": "invalid transition"},
    )
    assert invalid_confirm.status_code == 409
    assert (
        invalid_confirm.json()["detail"]
        == "Invalid reservation status transition: released -> confirmed"
    )


def test_release_after_confirm_is_invalid_transition(client):
    """Confirmed reservations are terminal and cannot be released."""
    create_response = client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-100", "quantity": 1},
    )
    reservation_id = create_response.json()["id"]

    confirm_response = client.post(
        f"/api/inventory/reservations/{reservation_id}/confirm",
        json={"reason": "payment authorized"},
    )
    assert confirm_response.status_code == 200

    release_response = client.post(
        f"/api/inventory/reservations/{reservation_id}/release",
        json={"reason": "should fail"},
    )
    assert release_response.status_code == 409


def test_validation_failures(client):
    """Validation and patch request guards return expected status codes."""
    invalid_create = client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-100", "quantity": 0},
    )
    assert invalid_create.status_code == 422

    invalid_thresholds = client.patch(
        "/api/inventory/SKU-100/thresholds",
        json={},
    )
    assert invalid_thresholds.status_code == 400

    invalid_patch = client.patch(
        "/api/inventory/SKU-100",
        json={},
    )
    assert invalid_patch.status_code == 400


def test_create_reservation_computes_availability_from_quantities(client):
    """Reservation creation should not trust stale persisted available_quantity."""
    stale_patch = client.patch(
        "/api/inventory/SKU-100",
        json={"quantity_on_hand": 10, "reserved_quantity": 0},
    )
    assert stale_patch.status_code == 200

    create_response = client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-100", "quantity": 3, "reason": "cart hold"},
    )

    assert create_response.status_code == 201

    created_reservation = create_response.json()
    reservation_id = created_reservation["id"]
    assert created_reservation["status"] == "created"

    health_response = client.get("/api/inventory/health")
    assert health_response.status_code == 200
    item = health_response.json()["items"][0]
    assert item["reserved_quantity"] == 3
    assert item["available_quantity"] == 7

    get_response = client.get(f"/api/inventory/reservations/{reservation_id}")
    assert get_response.status_code == 200


def test_inventory_mutation_forbidden_for_customer_role(client):
    """Inventory mutation endpoints reject customer-only users."""

    async def _customer_user():
        return User(
            user_id="customer-1",
            email="customer@example.com",
            name="Customer User",
            roles=["customer"],
        )

    app.dependency_overrides[get_current_user] = _customer_user

    patch_response = client.patch(
        "/api/inventory/SKU-100",
        json={"quantity_on_hand": 8},
    )
    thresholds_response = client.patch(
        "/api/inventory/SKU-100/thresholds",
        json={"reorder_point": 4},
    )

    assert patch_response.status_code == 403
    assert patch_response.json()["detail"] == "Role 'staff' or 'admin' required"
    assert thresholds_response.status_code == 403
    assert thresholds_response.json()["detail"] == "Role 'staff' or 'admin' required"


def test_reservation_access_forbidden_for_non_owner_customer(client):
    """Customers cannot operate on another user's reservation."""

    async def _owner_customer_user():
        return User(
            user_id="customer-owner",
            email="owner@example.com",
            name="Owner User",
            roles=["customer"],
        )

    async def _other_customer_user():
        return User(
            user_id="customer-other",
            email="other@example.com",
            name="Other User",
            roles=["customer"],
        )

    app.dependency_overrides[get_current_user] = _owner_customer_user
    create_response = client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-100", "quantity": 1, "reason": "owner hold"},
    )
    assert create_response.status_code == 201
    reservation_id = create_response.json()["id"]

    app.dependency_overrides[get_current_user] = _other_customer_user

    get_response = client.get(f"/api/inventory/reservations/{reservation_id}")
    confirm_response = client.post(
        f"/api/inventory/reservations/{reservation_id}/confirm",
        json={"reason": "attempt"},
    )
    release_response = client.post(
        f"/api/inventory/reservations/{reservation_id}/release",
        json={"reason": "attempt"},
    )

    assert get_response.status_code == 403
    assert get_response.json()["detail"] == "Forbidden"
    assert confirm_response.status_code == 403
    assert confirm_response.json()["detail"] == "Forbidden"
    assert release_response.status_code == 403
    assert release_response.json()["detail"] == "Forbidden"
