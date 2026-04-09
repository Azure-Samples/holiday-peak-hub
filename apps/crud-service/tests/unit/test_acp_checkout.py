"""Unit tests for ACP checkout routes."""

from copy import deepcopy
from datetime import datetime, timezone

import pytest
from crud_service.auth import User, get_current_user
from crud_service.integrations.event_publisher import EventPublisher
from crud_service.main import app
from crud_service.routes import acp_checkout, acp_payments
from fastapi.testclient import TestClient


@pytest.fixture(name="api_client")
def fixture_api_client():
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
@pytest.mark.usefixtures("override_auth")
async def test_create_checkout_session(monkeypatch, api_client):
    async def fake_create(item):
        return item

    monkeypatch.setattr(acp_checkout.session_repo, "create", fake_create)

    response = api_client.post(
        "/acp/checkout/sessions",
        json={
            "items": [
                {
                    "sku": "sku-1",
                    "quantity": 2,
                    "unit_price": 10.0,
                    "currency": "USD",
                }
            ]
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "created"
    assert payload["items"][0]["sku"] == "sku-1"


@pytest.mark.asyncio
@pytest.mark.usefixtures("override_auth")
async def test_update_checkout_session(monkeypatch, api_client):
    session = {
        "id": "session-1",
        "user_id": "user-1",
        "status": "created",
        "buyer": {"id": "user-1", "email": "user@example.com", "name": "Test User"},
        "items": [
            {
                "sku": "sku-1",
                "quantity": 1,
                "unit_price": 10.0,
                "currency": "USD",
            }
        ],
        "shipping_address": None,
        "fulfillment_options": [
            {
                "id": "standard",
                "label": "Standard Shipping",
                "amount": 5.99,
                "currency": "USD",
                "eta": "5-7 days",
            },
            {
                "id": "express",
                "label": "Express Shipping",
                "amount": 14.99,
                "currency": "USD",
                "eta": "2-3 days",
            },
        ],
        "selected_fulfillment_id": "standard",
        "totals": {
            "subtotal": 10.0,
            "shipping": 5.99,
            "tax": 0.8,
            "total": 16.79,
            "currency": "USD",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    async def fake_get_by_id(session_id, partition_key=None):
        _ = session_id
        _ = partition_key
        return session

    async def fake_update(item):
        return item

    monkeypatch.setattr(acp_checkout.session_repo, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(acp_checkout.session_repo, "update", fake_update)

    response = api_client.patch(
        "/acp/checkout/sessions/session-1",
        json={"selected_fulfillment_id": "express"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_fulfillment_id"] == "express"
    assert payload["status"] == "updated"


@pytest.mark.asyncio
@pytest.mark.usefixtures("override_auth")
async def test_complete_checkout_session(monkeypatch, api_client):
    session = {
        "id": "session-1",
        "user_id": "user-1",
        "status": "created",
        "buyer": {"id": "user-1", "email": "user@example.com", "name": "Test User"},
        "items": [
            {
                "sku": "sku-1",
                "quantity": 1,
                "unit_price": 20.0,
                "currency": "USD",
            }
        ],
        "shipping_address": None,
        "fulfillment_options": [],
        "selected_fulfillment_id": None,
        "totals": {
            "subtotal": 20.0,
            "shipping": 0.0,
            "tax": 1.6,
            "total": 21.6,
            "currency": "USD",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    token = {
        "id": "token-1",
        "user_id": "user-1",
        "status": "active",
        "allowance": {
            "amount": 50.0,
            "currency": "USD",
            "merchant_id": "holiday-peak-hub",
            "expires_at": None,
        },
    }

    class FakePublisher:
        async def publish_order_created(self, _order, **_kwargs):
            return None

        async def publish_payment_processed(self, _payment, **_kwargs):
            return None

    async def fake_get_by_id(session_id, partition_key=None):
        _ = session_id
        _ = partition_key
        return session

    async def fake_update(item):
        return item

    async def fake_get_token(token_id, partition_key=None):
        _ = token_id
        _ = partition_key
        return token

    async def fake_update_token(item):
        return item

    async def fake_create_order(item):
        return item

    monkeypatch.setattr(acp_checkout.session_repo, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(acp_checkout.session_repo, "update", fake_update)
    monkeypatch.setattr(acp_checkout.payment_token_repo, "get_by_id", fake_get_token)
    monkeypatch.setattr(acp_checkout.payment_token_repo, "update", fake_update_token)
    monkeypatch.setattr(acp_checkout.order_repo, "create", fake_create_order)
    monkeypatch.setattr(acp_checkout, "event_publisher", FakePublisher())

    response = api_client.post(
        "/acp/checkout/sessions/session-1/complete",
        json={"payment_token": "token-1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"


@pytest.mark.asyncio
@pytest.mark.usefixtures("override_auth")
async def test_complete_checkout_session_rolls_back_on_terminal_publish_failure(
    monkeypatch,
    api_client,
):
    original_session = {
        "id": "session-1",
        "user_id": "user-1",
        "status": "created",
        "buyer": {"id": "user-1", "email": "user@example.com", "name": "Test User"},
        "items": [
            {
                "sku": "sku-1",
                "quantity": 1,
                "unit_price": 20.0,
                "currency": "USD",
            }
        ],
        "shipping_address": None,
        "fulfillment_options": [],
        "selected_fulfillment_id": None,
        "totals": {
            "subtotal": 20.0,
            "shipping": 0.0,
            "tax": 1.6,
            "total": 21.6,
            "currency": "USD",
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    original_token = {
        "id": "token-1",
        "user_id": "user-1",
        "status": "active",
        "allowance": {
            "amount": 50.0,
            "currency": "USD",
            "merchant_id": "holiday-peak-hub",
            "expires_at": None,
        },
    }
    session_store = deepcopy(original_session)
    token_store = deepcopy(original_token)
    orders_store: dict[str, dict] = {}

    async def fake_get_by_id(session_id, partition_key=None):
        _ = session_id
        _ = partition_key
        return deepcopy(session_store)

    async def fake_update_session(item):
        session_store.clear()
        session_store.update(deepcopy(item))
        return deepcopy(item)

    async def fake_get_token(token_id, partition_key=None):
        _ = token_id
        _ = partition_key
        return deepcopy(token_store)

    async def fake_update_token(item):
        token_store.clear()
        token_store.update(deepcopy(item))
        return deepcopy(item)

    async def fake_create_order(item):
        orders_store[item["id"]] = deepcopy(item)
        return deepcopy(item)

    async def fake_delete_order(order_id, partition_key=None):
        _ = partition_key
        orders_store.pop(order_id, None)

    class SuccessfulProducer:
        def __init__(self) -> None:
            self.batch_count = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def send_batch(self, _events):
            self.batch_count += 1

    class FailingProducer:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def send_batch(self, _events):
            raise TimeoutError("payment topic unavailable")

    order_events_producer = SuccessfulProducer()
    publisher = EventPublisher()
    publisher.__dict__["_producers"] = {
        "order-events": order_events_producer,
        "payment-events": FailingProducer(),
    }

    monkeypatch.setattr(acp_checkout.session_repo, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(acp_checkout.session_repo, "update", fake_update_session)
    monkeypatch.setattr(acp_checkout.payment_token_repo, "get_by_id", fake_get_token)
    monkeypatch.setattr(acp_checkout.payment_token_repo, "update", fake_update_token)
    monkeypatch.setattr(acp_checkout.order_repo, "create", fake_create_order)
    monkeypatch.setattr(acp_checkout.order_repo, "delete", fake_delete_order)
    monkeypatch.setattr(acp_checkout, "event_publisher", publisher)

    response = api_client.post(
        "/acp/checkout/sessions/session-1/complete",
        json={"payment_token": "token-1"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Event publish failed",
        "type": "EventPublishError",
        "topic": "payment-events",
        "event_type": "PaymentProcessed",
        "category": "transient",
        "profile": "critical_saga",
    }
    assert order_events_producer.batch_count == 1
    assert session_store == original_session
    assert token_store == original_token
    assert orders_store == {}


@pytest.mark.asyncio
@pytest.mark.usefixtures("override_auth")
async def test_delegate_payment(monkeypatch, api_client):
    async def fake_create(item):
        return item

    monkeypatch.setattr(acp_payments.payment_token_repo, "create", fake_create)

    response = api_client.post(
        "/acp/payments/delegate",
        json={
            "payment_method_id": "pm_123",
            "allowance": {
                "amount": 25.0,
                "currency": "USD",
            },
            "risk_signals": {"ip": "127.0.0.1"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "active"
    assert payload["allowance"]["currency"] == "USD"
