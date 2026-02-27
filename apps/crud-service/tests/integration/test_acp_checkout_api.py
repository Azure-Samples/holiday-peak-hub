"""Integration tests for ACP checkout endpoints."""

from crud_service.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_acp_checkout_requires_auth():
    response = client.post(
        "/acp/checkout/sessions",
        json={"items": [{"sku": "sku-1", "quantity": 1, "unit_price": 10.0}]},
    )
    assert response.status_code == 401


def test_acp_delegate_payment_requires_auth():
    response = client.post(
        "/acp/payments/delegate",
        json={
            "payment_method_id": "pm_123",
            "allowance": {"amount": 10.0, "currency": "USD"},
        },
    )
    assert response.status_code == 401
