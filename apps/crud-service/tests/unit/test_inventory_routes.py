"""Unit tests for inventory and reservation routes."""

from collections.abc import Awaitable, Callable

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from crud_service.routes import inventory
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


@pytest.fixture(name="inventory_store")
def fixture_inventory_store(monkeypatch):
    store: dict[str, dict] = {
        "SKU-1": {
            "id": "SKU-1",
            "sku": "SKU-1",
            "quantity_on_hand": 20,
            "reserved_quantity": 0,
            "available_quantity": 20,
            "reorder_point": 5,
            "safety_stock": 2,
            "low_stock": False,
            "health_status": "healthy",
            "created_at": "2026-03-12T00:00:00+00:00",
            "updated_at": "2026-03-12T00:00:00+00:00",
            "created_by": "seed",
            "updated_by": "seed",
            "audit_log": [],
        }
    }

    async def fake_query(query, parameters=None, partition_key=None):
        del query, parameters, partition_key
        return [dict(item) for item in store.values()]

    async def fake_get(item_id, partition_key=None):
        del partition_key
        item = store.get(item_id)
        return dict(item) if item else None

    async def fake_update(item):
        store[item["id"]] = dict(item)
        return dict(item)

    monkeypatch.setattr(inventory.inventory_repo, "query", fake_query)
    monkeypatch.setattr(inventory.inventory_repo, "get_by_id", fake_get)
    monkeypatch.setattr(inventory.inventory_repo, "update", fake_update)
    return store


@pytest.fixture(name="reservation_store")
def fixture_reservation_store(monkeypatch):
    store: dict[str, dict] = {}

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

    monkeypatch.setattr(inventory.reservation_repo, "get_by_id", fake_get)
    monkeypatch.setattr(inventory.reservation_repo, "create", fake_create)
    monkeypatch.setattr(inventory.reservation_repo, "update", fake_update)
    return store


def test_inventory_reservation_confirm_release_flow(
    test_client,
    inventory_store,
    reservation_store,
):
    """Reservation lifecycle confirms and keeps inventory reservation locked."""
    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="staff-1",
            email="staff@example.com",
            name="Staff User",
            roles=["staff"],
        )
    )

    create_response = test_client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-1", "quantity": 3, "reason": "Cart hold"},
    )
    assert create_response.status_code == 201
    reservation = create_response.json()
    reservation_id = reservation["id"]
    assert reservation["status"] == "created"
    assert reservation["status_history"][0]["to"] == "created"

    confirm_response = test_client.post(
        f"/api/inventory/reservations/{reservation_id}/confirm",
        json={"reason": "Checkout step approved"},
    )
    assert confirm_response.status_code == 200
    assert confirm_response.json()["status"] == "confirmed"
    assert inventory_store["SKU-1"]["reserved_quantity"] == 3
    assert inventory_store["SKU-1"]["available_quantity"] == 17
    assert reservation_id in reservation_store


def test_confirm_after_release_returns_conflict(
    test_client,
    inventory_store,
    reservation_store,
):
    """Cannot transition reservation from released to confirmed."""
    reservation_store["res-1"] = {
        "id": "res-1",
        "sku": "SKU-1",
        "quantity": 2,
        "status": "released",
        "created_at": "2026-03-12T00:00:00+00:00",
        "updated_at": "2026-03-12T00:00:00+00:00",
        "created_by": "seed",
        "updated_by": "seed",
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

    response = test_client.post(
        "/api/inventory/reservations/res-1/confirm",
        json={"reason": "retry"},
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Invalid reservation status transition: released -> confirmed"
    )
    assert inventory_store["SKU-1"]["reserved_quantity"] == 0


def test_release_after_confirm_returns_conflict(
    test_client,
    inventory_store,
    reservation_store,
):
    """Cannot transition reservation from confirmed to released."""
    reservation_store["res-2"] = {
        "id": "res-2",
        "sku": "SKU-1",
        "quantity": 2,
        "status": "confirmed",
        "created_at": "2026-03-12T00:00:00+00:00",
        "updated_at": "2026-03-12T00:00:00+00:00",
        "created_by": "seed",
        "updated_by": "seed",
        "status_history": [],
        "audit_log": [],
    }

    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="staff-4",
            email="staff4@example.com",
            name="Staff User",
            roles=["staff"],
        )
    )

    response = test_client.post(
        "/api/inventory/reservations/res-2/release",
        json={"reason": "not allowed"},
    )

    assert response.status_code == 409
    assert (
        response.json()["detail"]
        == "Invalid reservation status transition: confirmed -> released"
    )
    assert inventory_store["SKU-1"]["reserved_quantity"] == 0


def test_create_reservation_uses_computed_availability_not_persisted_field(
    test_client,
    inventory_store,
    reservation_store,
):
    """Create reservation computes availability from source quantities."""
    del reservation_store
    inventory_store["SKU-1"]["available_quantity"] = 0
    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="staff-5",
            email="staff5@example.com",
            name="Staff User",
            roles=["staff"],
        )
    )

    create_response = test_client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-1", "quantity": 2, "reason": "cart hold"},
    )

    assert create_response.status_code == 201
    assert inventory_store["SKU-1"]["reserved_quantity"] == 2
    assert inventory_store["SKU-1"]["available_quantity"] == 18


def test_validation_and_noop_failures(test_client, inventory_store, reservation_store):
    """Validation failures and empty patch requests are rejected."""
    del reservation_store
    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="staff-3",
            email="staff3@example.com",
            name="Staff User",
            roles=["staff"],
        )
    )

    invalid_reservation = test_client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-1", "quantity": 0},
    )
    assert invalid_reservation.status_code == 422

    no_threshold_fields = test_client.patch(
        "/api/inventory/SKU-1/thresholds",
        json={},
    )
    assert no_threshold_fields.status_code == 400

    assert inventory_store["SKU-1"]["reorder_point"] == 5
    assert inventory_store["SKU-1"]["safety_stock"] == 2


def test_create_reservation_rolls_back_inventory_when_reservation_persist_fails(
    test_client,
    inventory_store,
    reservation_store,
    monkeypatch,
):
    """Inventory reserved quantity is restored when reservation persistence fails."""
    del reservation_store

    async def failing_reservation_create(_item):
        raise RuntimeError("reservation persistence failure")

    monkeypatch.setattr(inventory.reservation_repo, "create", failing_reservation_create)

    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="staff-6",
            email="staff6@example.com",
            name="Staff User",
            roles=["staff"],
        )
    )

    response = test_client.post(
        "/api/inventory/reservations",
        json={"sku": "SKU-1", "quantity": 4, "reason": "cart hold"},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Failed to persist reservation"
    assert inventory_store["SKU-1"]["reserved_quantity"] == 0
    assert inventory_store["SKU-1"]["available_quantity"] == 20


def test_inventory_mutation_forbidden_for_customer_role(test_client, inventory_store):
    """Inventory mutation endpoints require staff/admin roles."""
    del inventory_store
    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="customer-1",
            email="customer@example.com",
            name="Customer",
            roles=["customer"],
        )
    )

    patch_response = test_client.patch(
        "/api/inventory/SKU-1",
        json={"quantity_on_hand": 18},
    )
    thresholds_response = test_client.patch(
        "/api/inventory/SKU-1/thresholds",
        json={"reorder_point": 3},
    )

    assert patch_response.status_code == 403
    assert patch_response.json()["detail"] == "Role 'staff' or 'admin' required"
    assert thresholds_response.status_code == 403
    assert thresholds_response.json()["detail"] == "Role 'staff' or 'admin' required"


def test_reservation_access_forbidden_for_non_owner_customer(
    test_client,
    inventory_store,
    reservation_store,
):
    """Reservation read/confirm/release are blocked for non-owner customers."""
    del inventory_store
    reservation_store["res-owner"] = {
        "id": "res-owner",
        "sku": "SKU-1",
        "quantity": 1,
        "status": "created",
        "created_at": "2026-03-12T00:00:00+00:00",
        "updated_at": "2026-03-12T00:00:00+00:00",
        "created_by": "customer-owner",
        "updated_by": "customer-owner",
        "status_history": [],
        "audit_log": [],
    }

    app.dependency_overrides[get_current_user] = _override_user(
        User(
            user_id="customer-other",
            email="other@example.com",
            name="Other Customer",
            roles=["customer"],
        )
    )

    get_response = test_client.get("/api/inventory/reservations/res-owner")
    confirm_response = test_client.post(
        "/api/inventory/reservations/res-owner/confirm",
        json={"reason": "attempt"},
    )
    release_response = test_client.post(
        "/api/inventory/reservations/res-owner/release",
        json={"reason": "attempt"},
    )

    assert get_response.status_code == 403
    assert get_response.json()["detail"] == "Forbidden"
    assert confirm_response.status_code == 403
    assert confirm_response.json()["detail"] == "Forbidden"
    assert release_response.status_code == 403
    assert release_response.json()["detail"] == "Forbidden"
