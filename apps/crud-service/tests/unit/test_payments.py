"""Unit tests for payment routes."""

import pytest
from crud_service.auth import User, get_current_user
from crud_service.main import app
from crud_service.routes import payments, webhooks
from fastapi.testclient import TestClient


@pytest.fixture(name="test_client")
def fixture_test_client():
    return TestClient(app)


@pytest.fixture(autouse=True)
def fixture_override_auth():
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


@pytest.fixture(name="override_staff_auth")
def fixture_override_staff_auth():
    async def _override_user():
        return User(
            user_id="staff-1",
            email="staff@example.com",
            name="Staff User",
            roles=["staff"],
        )

    app.dependency_overrides[get_current_user] = _override_user
    yield
    app.dependency_overrides.clear()


# ─── /api/payments/intent ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_payment_intent_order_not_found(monkeypatch, test_client):
    """Returns 404 when the order does not exist."""

    async def fake_get(_order_id, partition_key=None):
        del partition_key
        return None

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)

    response = test_client.post(
        "/api/payments/intent",
        json={"order_id": "nonexistent", "amount": 50.0},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_payment_intent_forbidden(monkeypatch, test_client):
    """Returns 403 when the order belongs to a different user."""

    async def fake_get(_order_id, partition_key=None):
        del partition_key
        return {"user_id": "other-user", "status": "pending"}

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)

    response = test_client.post(
        "/api/payments/intent",
        json={"order_id": "order-1", "amount": 50.0},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_payment_intent_stripe_not_configured(monkeypatch, test_client):
    """Returns 503 when Stripe secret key is not set."""

    async def fake_get(_order_id, partition_key=None):
        del partition_key
        return {"user_id": "user-1", "status": "pending", "total": 50.0}

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)
    monkeypatch.setattr(payments.settings, "stripe_secret_key", None)

    response = test_client.post(
        "/api/payments/intent",
        json={"order_id": "order-1", "amount": 50.0},
    )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_create_payment_intent_success(monkeypatch, test_client):
    """Returns 200 with client_secret when Stripe is configured and order exists."""
    async def fake_get(_order_id, partition_key=None):
        del partition_key
        return {"user_id": "user-1", "status": "pending", "total": 99.99}

    class FakeIntent:
        client_secret = "pi_test_secret_abc"
        id = "pi_test_abc"
        status = "requires_payment_method"

    class FakeIntents:
        def create(self, **_kwargs):
            return FakeIntent()

    class FakeStripeClient:
        payment_intents = FakeIntents()

    def fake_get_stripe_client():
        return FakeStripeClient()

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)
    monkeypatch.setattr(payments.settings, "stripe_secret_key", "sk_test_dummy")
    monkeypatch.setattr(payments, "_get_stripe_client", fake_get_stripe_client)

    response = test_client.post(
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
async def test_process_payment_order_not_found(monkeypatch, test_client):
    """Returns 404 when processing a payment for a missing order."""

    async def fake_get(_order_id, partition_key=None):
        del partition_key
        return None

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)

    response = test_client.post(
        "/api/payments",
        json={"order_id": "missing", "payment_method_id": "pm_test", "amount": 10.0},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_process_payment_success(monkeypatch, test_client):
    """Returns 200 and publishes a payment event on success."""

    order = {"user_id": "user-1", "status": "pending", "total": 49.95}

    async def fake_get(_order_id, partition_key=None):
        del partition_key
        return dict(order)

    async def fake_update(item):
        order.update(item)

    async def fake_publish(_payment):
        return None

    async def fake_create(payment):
        return payment

    class FakeIntent:
        status = "succeeded"
        id = "pi_confirmed"

    class FakeIntents:
        def create(self, **_kwargs):
            return FakeIntent()

    class FakeStripeClient:
        payment_intents = FakeIntents()

    def fake_get_stripe_client():
        return FakeStripeClient()

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)
    monkeypatch.setattr(payments.order_repo, "update", fake_update)
    monkeypatch.setattr(payments.payment_repo, "create", fake_create)
    monkeypatch.setattr(payments.event_publisher, "publish_payment_processed", fake_publish)
    monkeypatch.setattr(payments.settings, "stripe_secret_key", "sk_test_dummy")
    monkeypatch.setattr(payments, "_get_stripe_client", fake_get_stripe_client)

    response = test_client.post(
        "/api/payments",
        json={"order_id": "order-1", "payment_method_id": "pm_test_card", "amount": 49.95},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["transaction_id"] == "pi_confirmed"
    assert order["status"] == "paid"


# ─── /api/payments/confirm-intent ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_confirm_payment_intent_success(monkeypatch, test_client):
    """Reconciles succeeded PaymentIntent, persists payment, and marks order paid."""
    order = {
        "id": "order-1",
        "user_id": "user-1",
        "status": "pending",
        "total": 49.95,
    }
    published = []

    async def fake_get_order(_order_id, partition_key=None):
        del partition_key
        return dict(order)

    async def fake_update_order(item):
        order.update(item)

    async def fake_payment_query(query, parameters=None, partition_key=None):
        del query, parameters, partition_key
        return []

    async def fake_payment_update(_payment):
        return None

    async def fake_publish(payment):
        published.append(payment)

    class FakeIntent:
        id = "pi_confirmed_1"
        status = "succeeded"
        amount_received = 4995
        metadata = {"order_id": "order-1", "user_id": "user-1"}

    class FakeIntents:
        def retrieve(self, _intent_id):
            return FakeIntent()

    class FakeStripeClient:
        payment_intents = FakeIntents()

    def fake_get_stripe_client():
        return FakeStripeClient()

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get_order)
    monkeypatch.setattr(payments.order_repo, "update", fake_update_order)
    monkeypatch.setattr(payments.payment_repo, "query", fake_payment_query)
    monkeypatch.setattr(payments.payment_repo, "update", fake_payment_update)
    monkeypatch.setattr(payments.event_publisher, "publish_payment_processed", fake_publish)
    monkeypatch.setattr(payments, "_get_stripe_client", fake_get_stripe_client)

    response = test_client.post(
        "/api/payments/confirm-intent",
        json={"order_id": "order-1", "payment_intent_id": "pi_confirmed_1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["transaction_id"] == "pi_confirmed_1"
    assert payload["amount"] == 49.95
    assert order["status"] == "paid"
    assert order["payment_id"] == payload["id"]
    assert len(published) == 1


@pytest.mark.asyncio
async def test_confirm_payment_intent_idempotent_retry(monkeypatch, test_client):
    """Returns existing payment and avoids duplicate publish when already paid."""
    order = {
        "id": "order-1",
        "user_id": "user-1",
        "status": "paid",
        "payment_id": "pay_existing",
        "total": 49.95,
    }
    existing_payment = {
        "id": "pay_existing",
        "order_id": "order-1",
        "user_id": "user-1",
        "amount": 49.95,
        "status": "completed",
        "transaction_id": "pi_confirmed_1",
        "created_at": "2026-03-12T00:00:00+00:00",
    }
    published = []

    async def fake_get_order(_order_id, partition_key=None):
        del partition_key
        return dict(order)

    async def fake_update_order(_item):
        raise AssertionError("Order should not be updated for idempotent retry")

    async def fake_payment_query(query, parameters=None, partition_key=None):
        del query, partition_key
        assert parameters is not None
        return [dict(existing_payment)]

    async def fake_publish(payment):
        published.append(payment)

    class FakeIntent:
        id = "pi_confirmed_1"
        status = "succeeded"
        amount_received = 4995
        metadata = {"order_id": "order-1", "user_id": "user-1"}

    class FakeIntents:
        def retrieve(self, _intent_id):
            return FakeIntent()

    class FakeStripeClient:
        payment_intents = FakeIntents()

    def fake_get_stripe_client():
        return FakeStripeClient()

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get_order)
    monkeypatch.setattr(payments.order_repo, "update", fake_update_order)
    monkeypatch.setattr(payments.payment_repo, "query", fake_payment_query)
    monkeypatch.setattr(payments.event_publisher, "publish_payment_processed", fake_publish)
    monkeypatch.setattr(payments, "_get_stripe_client", fake_get_stripe_client)

    response = test_client.post(
        "/api/payments/confirm-intent",
        json={"order_id": "order-1", "payment_intent_id": "pi_confirmed_1"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == "pay_existing"
    assert published == []


@pytest.mark.asyncio
async def test_confirm_payment_intent_repairs_paid_order_without_payment_record(
    monkeypatch, test_client
):
    """Creates missing payment record when webhook already set order as paid."""
    order = {
        "id": "order-1",
        "user_id": "user-1",
        "status": "paid",
        "payment_id": "pay_webhook_only",
        "total": 32.0,
    }
    upserted: list[dict] = []
    published = []

    async def fake_get_order(_order_id, partition_key=None):
        del partition_key
        return dict(order)

    async def fake_payment_query(query, parameters=None, partition_key=None):
        del query, parameters, partition_key
        return []

    async def fake_payment_get(_payment_id, partition_key=None):
        del _payment_id, partition_key
        return None

    async def fake_payment_update(payment):
        upserted.append(dict(payment))
        return payment

    async def fake_publish(payment):
        published.append(payment)

    class FakeIntent:
        id = "pi_confirmed_2"
        status = "succeeded"
        amount_received = 3200
        metadata = {"order_id": "order-1", "user_id": "user-1"}

    class FakeIntents:
        def retrieve(self, _intent_id):
            return FakeIntent()

    class FakeStripeClient:
        payment_intents = FakeIntents()

    def fake_get_stripe_client():
        return FakeStripeClient()

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get_order)
    monkeypatch.setattr(payments.payment_repo, "query", fake_payment_query)
    monkeypatch.setattr(payments.payment_repo, "get_by_id", fake_payment_get)
    monkeypatch.setattr(payments.payment_repo, "update", fake_payment_update)
    monkeypatch.setattr(payments.event_publisher, "publish_payment_processed", fake_publish)
    monkeypatch.setattr(payments, "_get_stripe_client", fake_get_stripe_client)

    response = test_client.post(
        "/api/payments/confirm-intent",
        json={"order_id": "order-1", "payment_intent_id": "pi_confirmed_2"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "pay_webhook_only"
    assert payload["amount"] == 32.0
    assert len(upserted) == 1
    assert published == []


@pytest.mark.asyncio
async def test_create_payment_intent_rejects_amount_mismatch(monkeypatch, test_client):
    """Returns 400 when client amount does not match order total."""

    async def fake_get(_order_id, partition_key=None):
        del partition_key
        return {"user_id": "user-1", "status": "pending", "total": 88.0}

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get)
    monkeypatch.setattr(payments.settings, "stripe_secret_key", "sk_test_dummy")

    response = test_client.post(
        "/api/payments/intent",
        json={"order_id": "order-1", "amount": 99.0},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_confirm_payment_intent_rejects_missing_metadata(monkeypatch, test_client):
    """Returns 400 when Stripe intent metadata is incomplete."""
    order = {
        "id": "order-1",
        "user_id": "user-1",
        "status": "pending",
        "total": 49.95,
    }

    async def fake_get_order(_order_id, partition_key=None):
        del partition_key
        return dict(order)

    class FakeIntent:
        id = "pi_missing_meta"
        status = "succeeded"
        amount_received = 4995
        metadata = {}

    class FakeIntents:
        def retrieve(self, _intent_id):
            return FakeIntent()

    class FakeStripeClient:
        payment_intents = FakeIntents()

    def fake_get_stripe_client():
        return FakeStripeClient()

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get_order)
    monkeypatch.setattr(payments, "_get_stripe_client", fake_get_stripe_client)

    response = test_client.post(
        "/api/payments/confirm-intent",
        json={"order_id": "order-1", "payment_intent_id": "pi_missing_meta"},
    )

    assert response.status_code == 400


@pytest.mark.asyncio
async def test_confirm_payment_intent_rejects_invalid_provider_amount(monkeypatch, test_client):
    """Returns 502 when Stripe returns an invalid amount for confirmed intent."""
    order = {
        "id": "order-1",
        "user_id": "user-1",
        "status": "pending",
        "total": 49.95,
    }

    async def fake_get_order(_order_id, partition_key=None):
        del partition_key
        return dict(order)

    class FakeIntent:
        id = "pi_bad_amount"
        status = "succeeded"
        amount_received = None
        amount = None
        metadata = {"order_id": "order-1", "user_id": "user-1"}

    class FakeIntents:
        def retrieve(self, _intent_id):
            return FakeIntent()

    class FakeStripeClient:
        payment_intents = FakeIntents()

    def fake_get_stripe_client():
        return FakeStripeClient()

    monkeypatch.setattr(payments.order_repo, "get_by_id", fake_get_order)
    monkeypatch.setattr(payments, "_get_stripe_client", fake_get_stripe_client)

    response = test_client.post(
        "/api/payments/confirm-intent",
        json={"order_id": "order-1", "payment_intent_id": "pi_bad_amount"},
    )

    assert response.status_code == 502


# ─── /api/payments/{payment_id} ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_payment_not_found(monkeypatch, test_client):
    """Returns 404 when the payment does not exist."""

    async def fake_get(_payment_id, partition_key=None):
        del partition_key
        return None

    monkeypatch.setattr(payments.payment_repo, "get_by_id", fake_get)

    response = test_client.get("/api/payments/pay_missing")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_payment_forbidden_for_other_customer(monkeypatch, test_client):
    """Returns 403 for customer trying to view another user's payment."""

    async def fake_get(payment_id, partition_key=None):
        del partition_key
        return {
            "id": payment_id,
            "order_id": "order-1",
            "user_id": "other-user",
            "amount": 10.0,
            "status": "completed",
            "transaction_id": "pi_123",
            "created_at": "2026-03-12T00:00:00+00:00",
        }

    monkeypatch.setattr(payments.payment_repo, "get_by_id", fake_get)

    response = test_client.get("/api/payments/pay_other")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_payment_staff_can_view_any(monkeypatch, test_client, override_staff_auth):
    """Allows staff to view payments for any user."""
    del override_staff_auth

    async def fake_get(payment_id, partition_key=None):
        del partition_key
        return {
            "id": payment_id,
            "order_id": "order-2",
            "user_id": "customer-22",
            "amount": 29.99,
            "status": "completed",
            "transaction_id": "pi_staff",
            "created_at": "2026-03-12T00:00:00+00:00",
        }

    monkeypatch.setattr(payments.payment_repo, "get_by_id", fake_get)

    response = test_client.get("/api/payments/pay_any")
    assert response.status_code == 200
    assert response.json()["id"] == "pay_any"


# ─── /webhooks/stripe ─────────────────────────────────────────────────────────


def test_stripe_webhook_missing_secret(test_client):
    """Returns 503 when webhook secret is not configured."""
    # settings.stripe_webhook_secret is None by default in tests
    response = test_client.post(
        "/webhooks/stripe",
        content=b'{"type":"payment_intent.succeeded"}',
        headers={"stripe-signature": "t=1,v1=abc"},
    )
    assert response.status_code == 503


def test_stripe_webhook_bad_signature(monkeypatch, test_client):
    """Returns 400 when signature verification fails."""
    import stripe

    monkeypatch.setattr(webhooks.settings, "stripe_webhook_secret", "whsec_test")

    def fake_construct(payload, sig, secret):
        raise stripe.SignatureVerificationError("bad sig", sig)

    monkeypatch.setattr(stripe.Webhook, "construct_event", fake_construct)

    response = test_client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=bad"},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_stripe_webhook_payment_succeeded(monkeypatch, test_client):
    """Processes payment_intent.succeeded and updates the order."""
    import stripe

    order = {"user_id": "user-1", "status": "pending", "order_id": "order-1"}

    async def fake_get(_order_id, partition_key=None):
        del partition_key
        return dict(order)

    async def fake_update(item):
        order.update(item)

    async def fake_publish(_payment):
        return None

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

    response = test_client.post(
        "/webhooks/stripe",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=ok"},
    )
    assert response.status_code == 200
    assert response.json() == {"received": True}
    assert order["status"] == "paid"
