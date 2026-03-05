"""Unit tests for payment routes."""

import pytest
from crud_service.auth import User, get_current_user
from crud_service.config import get_settings
from crud_service.main import app
from crud_service.routes import payments, webhooks
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


# ─── /api/payments/intent ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_payment_intent_order_not_found(monkeypatch, client, override_auth):
    """Returns 404 when the order does not exist."""

    async def fake_get(order_id, partition_key=None):
        return None

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)

    response = client.post(
        "/api/payments/intent",
        json={"order_id": "nonexistent", "amount": 50.0},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_payment_intent_forbidden(monkeypatch, client, override_auth):
    """Returns 403 when the order belongs to a different user."""

    async def fake_get(order_id, partition_key=None):
        return {"user_id": "other-user", "status": "pending"}

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)

    response = client.post(
        "/api/payments/intent",
        json={"order_id": "order-1", "amount": 50.0},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_payment_intent_stripe_not_configured(monkeypatch, client, override_auth):
    """Returns 503 when Stripe secret key is not set."""

    async def fake_get(order_id, partition_key=None):
        return {"user_id": "user-1", "status": "pending"}

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)
    monkeypatch.setattr(payments.settings, "stripe_secret_key", None)

    response = client.post(
        "/api/payments/intent",
        json={"order_id": "order-1", "amount": 50.0},
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_create_payment_intent_success(monkeypatch, client, override_auth):
    """Returns 200 with client_secret when Stripe is configured and order exists."""
    import stripe

    async def fake_get(order_id, partition_key=None):
        return {"user_id": "user-1", "status": "pending"}

    class FakeIntent:
        client_secret = "pi_test_secret_abc"
        id = "pi_test_abc"
        status = "requires_payment_method"

    class FakeIntents:
        def create(self, **kwargs):
            return FakeIntent()

    class FakeStripeClient:
        payment_intents = FakeIntents()

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)
    monkeypatch.setattr(payments.settings, "stripe_secret_key", "sk_test_dummy")
    monkeypatch.setattr(payments, "_get_stripe_client", lambda: FakeStripeClient())

    response = client.post(
        "/api/payments/intent",
        json={"order_id": "order-1", "amount": 99.99},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["client_secret"] == "pi_test_secret_abc"
    assert payload["payment_intent_id"] == "pi_test_abc"
    assert payload["amount"] == 99.99


# ─── /api/payments ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_process_payment_order_not_found(monkeypatch, client, override_auth):
    """Returns 404 when processing a payment for a missing order."""

    async def fake_get(order_id, partition_key=None):
        return None

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)

    response = client.post(
        "/api/payments",
        json={"order_id": "missing", "payment_method_id": "pm_test", "amount": 10.0},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_process_payment_success(monkeypatch, client, override_auth):
    """Returns 200 and publishes a payment event on success."""

    order = {"user_id": "user-1", "status": "pending"}

    async def fake_get(order_id, partition_key=None):
        return dict(order)

    async def fake_update(item):
        order.update(item)

    async def fake_publish(payment):
        pass

    class FakeIntent:
        status = "succeeded"
        id = "pi_confirmed"

    class FakeIntents:
        def create(self, **kwargs):
            return FakeIntent()

    class FakeStripeClient:
        payment_intents = FakeIntents()

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)
    monkeypatch.setattr(payments.order_repo, "update", fake_update)
    monkeypatch.setattr(payments.event_publisher, "publish_payment_processed", fake_publish)
    monkeypatch.setattr(payments.settings, "stripe_secret_key", "sk_test_dummy")
    monkeypatch.setattr(payments, "_get_stripe_client", lambda: FakeStripeClient())

    response = client.post(
        "/api/payments",
        json={"order_id": "order-1", "payment_method_id": "pm_test_card", "amount": 49.95},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["transaction_id"] == "pi_confirmed"
    assert order["status"] == "paid"


# ─── /webhooks/stripe ─────────────────────────────────────────────────────────


def test_stripe_webhook_missing_secret(client):
    """Returns 503 when webhook secret is not configured."""
    # settings.stripe_webhook_secret is None by default in tests
    response = client.post(
        "/webhooks/stripe",
        content=b'{"type":"payment_intent.succeeded"}',
        headers={"stripe-signature": "t=1,v1=abc"},
    )
    assert response.status_code == 503


def test_stripe_webhook_bad_signature(monkeypatch, client):
    """Returns 400 when signature verification fails."""
    import stripe

    monkeypatch.setattr(webhooks.settings, "stripe_webhook_secret", "whsec_test")

    def fake_construct(payload, sig, secret):
        raise stripe.SignatureVerificationError("bad sig", sig)

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct)

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=bad"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_stripe_webhook_payment_succeeded(monkeypatch, client):
    """Processes payment_intent.succeeded and updates the order."""
    import stripe

    order = {"user_id": "user-1", "status": "pending", "order_id": "order-1"}

    async def fake_get(order_id, partition_key=None):
        return dict(order)

    async def fake_update(item):
        order.update(item)

    async def fake_publish(payment):
        pass

    monkeypatch.setattr(webhooks.settings, "stripe_webhook_secret", "whsec_test")
    monkeypatch.setattr(webhooks.order_repo, "get_by_id", fake_get)
    monkeypatch.setattr(webhooks.order_repo, "update", fake_update)
    monkeypatch.setattr(webhooks.event_publisher, "publish_payment_processed", fake_publish)

    fake_event = {
        "type": "payment_intent.succeeded",
        "data": {
            "object": {
                "id": "pi_abc",
                "amount": 5000,
                "metadata": {"order_id": "order-1", "user_id": "user-1"},
            }
        },
    }

    monkeypatch.setattr(stripe.Webhook, "construct_event", lambda *a, **k: fake_event)

    response = client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=ok"},
    )
    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert order["status"] == "paid"
