"""Webhook routes for third-party integrations."""

import logging
import uuid
from datetime import datetime

import stripe
from crud_service.config import get_settings
from crud_service.integrations import get_event_publisher
from crud_service.repositories import OrderRepository
from fastapi import APIRouter, Header, HTTPException, Request, status

logger = logging.getLogger(__name__)

router = APIRouter()
order_repo = OrderRepository()
event_publisher = get_event_publisher()
settings = get_settings()


@router.post("/webhooks/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="stripe-signature"),
):
    """
    Handle Stripe webhook events.

    Verifies the Stripe-Signature header and processes relevant events:
    - payment_intent.succeeded  → update order to "paid", publish event
    - payment_intent.payment_failed → log the failure
    """
    if not settings.stripe_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret not configured",
        )

    payload = await request.body()

    try:
        event = stripe.Webhook.construct_event(
            payload, stripe_signature, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError as exc:
        logger.warning("Invalid Stripe webhook signature: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        ) from exc

    event_type = event["type"]
    logger.info("Received Stripe webhook: %s", event_type)

    if event_type == "payment_intent.succeeded":
        intent = event["data"]["object"]
        order_id = intent.get("metadata", {}).get("order_id")
        user_id = intent.get("metadata", {}).get("user_id")

        if order_id and user_id:
            order = await order_repo.get_by_id(order_id, partition_key=user_id)
            if order and order.get("status") != "paid":
                payment_id = str(uuid.uuid4())
                now = datetime.utcnow().isoformat()

                order["status"] = "paid"
                order["payment_id"] = payment_id
                await order_repo.update(order)

                await event_publisher.publish_payment_processed(
                    {
                        "id": payment_id,
                        "order_id": order_id,
                        "user_id": user_id,
                        "amount": intent["amount"] / 100,
                        "status": "completed",
                        "transaction_id": intent["id"],
                        "created_at": now,
                    }
                )

    elif event_type == "payment_intent.payment_failed":
        intent = event["data"]["object"]
        order_id = intent.get("metadata", {}).get("order_id")
        logger.warning(
            "Payment failed for order %s: %s",
            order_id,
            intent.get("last_payment_error"),
        )

    return {"received": True}
