"""End-to-end tests for checkout flow."""

import pytest


@pytest.mark.e2e
def test_full_checkout_flow(client, mock_auth_token, mock_event_hub, mock_cosmos_db):
    """
    Test complete checkout flow:
    1. Add product to cart
    2. Get cart
    3. Create order
    4. Verify order created
    5. Verify OrderCreated event published
    """
    add_response = client.post(
        "/api/cart/items",
        json={"product_id": "test-laptop", "quantity": 1},
        headers=mock_auth_token,
    )
    assert add_response.status_code == 200

    cart_response = client.get("/api/cart", headers=mock_auth_token)
    assert cart_response.status_code == 200
    cart_payload = cart_response.json()
    assert cart_payload["user_id"] == "test-user"
    assert len(cart_payload["items"]) == 1

    order_response = client.post(
        "/api/orders",
        json={
            "shipping_address_id": "addr-1",
            "payment_method_id": "pm-1",
        },
        headers=mock_auth_token,
    )
    assert order_response.status_code == 200
    order_payload = order_response.json()
    assert order_payload["status"] == "pending"
    assert order_payload["user_id"] == "test-user"
    assert order_payload["total"] > 0

    list_orders_response = client.get("/api/orders", headers=mock_auth_token)
    assert list_orders_response.status_code == 200
    orders_payload = list_orders_response.json()
    assert len(orders_payload) == 1
    assert orders_payload[0]["id"] == order_payload["id"]

    cart_after_checkout = client.get("/api/cart", headers=mock_auth_token)
    assert cart_after_checkout.status_code == 200
    assert cart_after_checkout.json()["items"] == []

    assert any(
        event["topic"] == "order-events"
        and event["event_type"] == "OrderCreated"
        and event["data"].get("id") == order_payload["id"]
        for event in mock_event_hub
    )
