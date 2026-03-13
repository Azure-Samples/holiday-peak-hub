"""Payment routes with Stripe integration."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

import stripe
from crud_service.auth import User, get_current_user
from crud_service.config import get_settings
from crud_service.integrations import get_event_publisher
from crud_service.repositories import OrderRepository
from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()
order_repo = OrderRepository()
ALLOWED_INTENT_STATUSES = {"succeeded", "requires_capture"}


class PaymentRepository(BaseRepository):
    """Repository for persisted payments."""

    def __init__(self):
        super().__init__(container_name="payments")


payment_repo = PaymentRepository()
event_publisher = get_event_publisher()
settings = get_settings()


class CreatePaymentIntentRequest(BaseModel):
    """Create Stripe PaymentIntent request."""

    order_id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    currency: Literal["usd"] = "usd"


class PaymentIntentResponse(BaseModel):
    """Stripe PaymentIntent response."""

    client_secret: str
    payment_intent_id: str
    amount: float
    currency: str
    status: str


class ProcessPaymentRequest(BaseModel):
    """Process payment request."""

    order_id: str = Field(min_length=1)
    payment_method_id: str = Field(min_length=1)
    amount: float = Field(gt=0)


class ConfirmPaymentIntentRequest(BaseModel):
    """Reconcile an already-confirmed Stripe PaymentIntent with an order."""

    order_id: str = Field(min_length=1)
    payment_intent_id: str = Field(min_length=1)


class PaymentResponse(BaseModel):
    """Payment response."""

    id: str
    order_id: str
    amount: float
    status: Literal["completed"]
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


async def _find_existing_payment(order_id: str, transaction_id: str) -> dict | None:
    """Return existing payment for order + Stripe transaction if present."""
    matches = await payment_repo.query(
        query=(
            "SELECT * FROM c WHERE c.order_id = @order_id "
            "AND c.transaction_id = @transaction_id OFFSET 0 LIMIT 1"
        ),
        parameters=[
            {"name": "@order_id", "value": order_id},
            {"name": "@transaction_id", "value": transaction_id},
        ],
    )
    return matches[0] if matches else None


def _extract_order_total(order: dict) -> float | None:
    """Extract and normalize an order total if available."""
    raw_total = order.get("total")
    if not isinstance(raw_total, (int, float)):
        return None
    normalized_total = round(float(raw_total), 2)
    if normalized_total <= 0:
        return None
    return normalized_total


def _assert_request_amount_matches_order(*, request_amount: float, order: dict) -> float:
    """Validate client provided amount against canonical order total."""
    order_total = _extract_order_total(order)
    if order_total is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order total unavailable for payment processing",
        )

    if abs(order_total - round(request_amount, 2)) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount does not match order total",
        )

    return order_total


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

    if order.get("status") == "paid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order is already paid",
        )

    order_total = _assert_request_amount_matches_order(
        request_amount=request.amount,
        order=order,
    )

    stripe_client = _get_stripe_client()

    try:
        # Stripe amounts are in the smallest currency unit (cents for USD)
        amount_cents = round(order_total * 100)
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
        amount=order_total,
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

    existing_order_payment_id = order.get("payment_id")
    if order.get("status") == "paid" and existing_order_payment_id:
        existing_payment = await payment_repo.get_by_id(existing_order_payment_id)
        if (
            existing_payment
            and existing_payment.get("order_id") == request.order_id
            and existing_payment.get("user_id") == current_user.user_id
        ):
            return PaymentResponse(**existing_payment)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Order is already paid",
        )

    order_total = _assert_request_amount_matches_order(
        request_amount=request.amount,
        order=order,
    )

    stripe_client = _get_stripe_client()

    try:
        amount_cents = round(order_total * 100)
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
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider error",
        ) from exc

    if intent.status not in ALLOWED_INTENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment not completed. Status: {intent.status}",
        )

    payment_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    payment = {
        "id": payment_id,
        "order_id": request.order_id,
        "user_id": current_user.user_id,
        "amount": order_total,
        "status": "completed",
        "transaction_id": intent.id,
        "created_at": now,
    }

    await payment_repo.create(payment)

    order["status"] = "paid"
    order["payment_id"] = payment_id
    await order_repo.update(order)

    await event_publisher.publish_payment_processed(payment)

    return PaymentResponse(**payment)


@router.post("/payments/confirm-intent", response_model=PaymentResponse)
async def confirm_payment_intent(
    request: ConfirmPaymentIntentRequest,
    current_user: User = Depends(get_current_user),
):
    """Reconcile a confirmed Stripe PaymentIntent with a real order."""
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
        intent = stripe_client.payment_intents.retrieve(request.payment_intent_id)
    except stripe.StripeError as exc:
        logger.error("Stripe PaymentIntent retrieval failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider error",
        ) from exc

    if intent.status not in ALLOWED_INTENT_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Payment not completed. Status: {intent.status}",
        )

    metadata = getattr(intent, "metadata", {}) or {}
    metadata_order_id = metadata.get("order_id")
    metadata_user_id = metadata.get("user_id")

    if not metadata_order_id or not metadata_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PaymentIntent metadata is incomplete",
        )

    if metadata_order_id != request.order_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="PaymentIntent does not belong to the specified order",
        )

    if metadata_user_id != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    amount_cents = getattr(intent, "amount_received", None)
    if amount_cents is None:
        amount_cents = getattr(intent, "amount", None)
    if not isinstance(amount_cents, (int, float)) or amount_cents <= 0:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Payment provider returned invalid payment amount",
        )

    amount = round(amount_cents / 100, 2)
    order_total = _extract_order_total(order)
    if order_total is not None and abs(order_total - amount) > 0.01:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Confirmed payment amount does not match order total",
        )

    existing_payment = await _find_existing_payment(request.order_id, intent.id)
    if not existing_payment and order.get("payment_id"):
        linked_payment = await payment_repo.get_by_id(order["payment_id"])
        if (
            linked_payment
            and linked_payment.get("order_id") == request.order_id
            and linked_payment.get("transaction_id") == intent.id
        ):
            existing_payment = linked_payment

    if existing_payment:
        payment = existing_payment
    else:
        if order.get("payment_id"):
            linked_payment = await payment_repo.get_by_id(order["payment_id"])
            if linked_payment and linked_payment.get("transaction_id") != intent.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Order already linked to a different payment transaction",
                )
            if not linked_payment and order.get("status") != "paid":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Order has inconsistent payment reference",
                )

        payment_id = order.get("payment_id") or f"pay_{intent.id}"
        payment = {
            "id": payment_id,
            "order_id": request.order_id,
            "user_id": current_user.user_id,
            "amount": amount,
            "status": "completed",
            "transaction_id": intent.id,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await payment_repo.update(payment)

    previous_status = order.get("status")
    if order.get("status") != "paid" or order.get("payment_id") != payment["id"]:
        order["status"] = "paid"
        order["payment_id"] = payment["id"]
        await order_repo.update(order)

    if previous_status != "paid":
        await event_publisher.publish_payment_processed(payment)

    return PaymentResponse(**payment)


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
async def get_payment(payment_id: str, current_user: User = Depends(get_current_user)):
    """Get persisted payment details with ownership and role checks."""
    payment = await payment_repo.get_by_id(payment_id)
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    is_staff_or_admin = bool({"staff", "admin"}.intersection(set(current_user.roles or [])))
    if payment.get("user_id") != current_user.user_id and not is_staff_or_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    return PaymentResponse(**payment)
