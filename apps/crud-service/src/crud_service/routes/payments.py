"""Payment routes with Stripe integration."""

import logging
import uuid
from datetime import datetime

import stripe
from crud_service.auth import User, get_current_user
from crud_service.config import get_settings
from crud_service.integrations import get_event_publisher
from crud_service.repositories import OrderRepository
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter()
order_repo = OrderRepository()
event_publisher = get_event_publisher()
settings = get_settings()


class CreatePaymentIntentRequest(BaseModel):
    """Create Stripe PaymentIntent request."""

    order_id: str
    amount: float
    currency: str = "usd"


class PaymentIntentResponse(BaseModel):
    """Stripe PaymentIntent response."""

    client_secret: str
    payment_intent_id: str
    amount: float
    currency: str
    status: str


class ProcessPaymentRequest(BaseModel):
    """Process payment request."""

    order_id: str
    payment_method_id: str
    amount: float


class PaymentResponse(BaseModel):
    """Payment response."""

    id: str
    order_id: str
    amount: float
    status: str
    transaction_id: str | None = None
    created_at: str


def _get_stripe_client() -> stripe.StripeClient:
    """Return a configured Stripe client."""
    if not settings.stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured",
        )
    return stripe.StripeClient(settings.stripe_secret_key)


@router.post("/payments/intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    request: CreatePaymentIntentRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a Stripe PaymentIntent for client-side confirmation.

    Returns a client_secret that the frontend uses with Stripe.js to
    collect and confirm the payment without raw card data touching the server.
    """
    order = await order_repo.get_by_id(request.order_id, partition_key=current_user.user_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    stripe_client = _get_stripe_client()

    try:
        # Stripe amounts are in the smallest currency unit (cents for USD)
        amount_cents = round(request.amount * 100)
        intent = stripe_client.payment_intents.create(
            amount=amount_cents,
            currency=request.currency.lower(),
            metadata={
                "order_id": request.order_id,
                "user_id": current_user.user_id,
            },
        )
    except stripe.StripeError as exc:
        logger.error("Stripe PaymentIntent creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider error",
        ) from exc

    return PaymentIntentResponse(
        client_secret=intent.client_secret,
        payment_intent_id=intent.id,
        amount=request.amount,
        currency=request.currency.lower(),
        status=intent.status,
    )


@router.post("/payments", response_model=PaymentResponse)
async def process_payment(
    request: ProcessPaymentRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Confirm a payment for an order using Stripe.

    Attaches the payment method to a new PaymentIntent and immediately
    confirms it server-side.  Publishes PaymentProcessed event on success.
    """
    order = await order_repo.get_by_id(request.order_id, partition_key=current_user.user_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order["user_id"] != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    stripe_client = _get_stripe_client()

    try:
        amount_cents = round(request.amount * 100)
        intent = stripe_client.payment_intents.create(
            amount=amount_cents,
            currency="usd",
            payment_method=request.payment_method_id,
            confirm=True,
            metadata={
                "order_id": request.order_id,
                "user_id": current_user.user_id,
            },
        )
    except stripe.StripeError as exc:
        logger.error("Stripe payment confirmation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=str(exc),
        ) from exc

    if intent.status not in {"succeeded", "requires_capture"}:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment not completed. Status: {intent.status}",
        )

    payment_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    payment = {
        "id": payment_id,
        "order_id": request.order_id,
        "user_id": current_user.user_id,
        "amount": request.amount,
        "status": "completed",
        "transaction_id": intent.id,
        "created_at": now,
    }

    order["status"] = "paid"
    order["payment_id"] = payment_id
    await order_repo.update(order)

    await event_publisher.publish_payment_processed(payment)

    return PaymentResponse(**payment)


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str, current_user: User = Depends(get_current_user)):
    """Get payment details."""
    # TODO: Implement payment retrieval from PostgreSQL
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Payment retrieval not yet implemented",
    )
