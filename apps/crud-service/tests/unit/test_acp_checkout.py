"""Unit tests for ACP checkout routes."""

from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from crud_service.auth import User, get_current_user
from crud_service.main import app
from crud_service.routes import acp_checkout, acp_payments


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


@pytest.mark.asyncio
async def test_create_checkout_session(monkeypatch, client, override_auth):
    async def fake_create(item):
        return item

    monkeypatch.setattr(acp_checkout.session_repo, "create", fake_create)

    response = client.post(
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
async def test_update_checkout_session(monkeypatch, client, override_auth):
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
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    async def fake_get_by_id(session_id, partition_key=None):
        return session

    async def fake_update(item):
        return item

    monkeypatch.setattr(acp_checkout.session_repo, "get_by_id", fake_get_by_id)
    monkeypatch.setattr(acp_checkout.session_repo, "update", fake_update)

    response = client.patch(
        "/acp/checkout/sessions/session-1",
        json={"selected_fulfillment_id": "express"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["selected_fulfillment_id"] == "express"
    assert payload["status"] == "updated"


@pytest.mark.asyncio
async def test_complete_checkout_session(monkeypatch, client, override_auth):
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
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
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
        async def publish_order_created(self, order):
            return None

        async def publish_payment_processed(self, payment):
            return None

    async def fake_get_by_id(session_id, partition_key=None):
        return session

    async def fake_update(item):
        return item

    async def fake_get_token(token_id, partition_key=None):
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

    response = client.post(
        "/acp/checkout/sessions/session-1/complete",
        json={"payment_token": "token-1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"


@pytest.mark.asyncio
async def test_delegate_payment(monkeypatch, client, override_auth):
    async def fake_create(item):
        return item

    monkeypatch.setattr(acp_payments.payment_token_repo, "create", fake_create)

    response = client.post(
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
