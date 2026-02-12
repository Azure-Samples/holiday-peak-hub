"""ACP checkout session routes."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from crud_service.auth import User, get_current_user
from crud_service.config import get_settings
from crud_service.integrations import get_agent_client, get_event_publisher
from crud_service.repositories import (
    CheckoutSessionRepository,
    OrderRepository,
    PaymentTokenRepository,
)

router = APIRouter()
settings = get_settings()
agent_client = get_agent_client()
session_repo = CheckoutSessionRepository()
payment_token_repo = PaymentTokenRepository()
order_repo = OrderRepository()
event_publisher = get_event_publisher()


class ACPCheckoutItem(BaseModel):
    """Checkout line item."""

    sku: str
    quantity: int = Field(..., gt=0)
    unit_price: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class ACPBuyerInfo(BaseModel):
    """Buyer information."""

    id: str | None = None
    email: str | None = None
    name: str | None = None
    phone: str | None = None


class ACPAddress(BaseModel):
    """Shipping address."""

    line1: str
    line2: str | None = None
    city: str
    state: str | None = None
    postal_code: str
    country: str


class ACPFulfillmentOption(BaseModel):
    """Fulfillment option for checkout."""

    id: str
    label: str
    amount: float
    currency: str
    eta: str | None = None


class ACPCheckoutTotals(BaseModel):
    """Checkout totals."""

    subtotal: float
    shipping: float
    tax: float
    total: float
    currency: str


class CreateCheckoutSessionRequest(BaseModel):
    """Create ACP checkout session request."""

    items: list[ACPCheckoutItem]
    buyer: ACPBuyerInfo | None = None
    shipping_address: ACPAddress | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=3)


class UpdateCheckoutSessionRequest(BaseModel):
    """Update ACP checkout session request."""

    items: list[ACPCheckoutItem] | None = None
    shipping_address: ACPAddress | None = None
    selected_fulfillment_id: str | None = None


class CompleteCheckoutRequest(BaseModel):
    """Complete ACP checkout session request."""

    payment_token: str


class CheckoutSessionResponse(BaseModel):
    """ACP checkout session response."""

    id: str
    status: str
    buyer: ACPBuyerInfo | None
    items: list[ACPCheckoutItem]
    shipping_address: ACPAddress | None
    fulfillment_options: list[ACPFulfillmentOption]
    selected_fulfillment_id: str | None
    totals: ACPCheckoutTotals
    created_at: str
    updated_at: str


def _default_fulfillment_options(currency: str) -> list[dict[str, Any]]:
    return [
        {
            "id": "standard",
            "label": "Standard Shipping",
            "amount": 5.99,
            "currency": currency,
            "eta": "5-7 days",
        },
        {
            "id": "express",
            "label": "Express Shipping",
            "amount": 14.99,
            "currency": currency,
            "eta": "2-3 days",
        },
    ]


def _calculate_totals(
    items: list[ACPCheckoutItem],
    fulfillment: dict[str, Any] | None,
    currency: str,
) -> dict[str, Any]:
    subtotal = sum(item.unit_price * item.quantity for item in items if item.unit_price)
    shipping = fulfillment.get("amount", 0.0) if fulfillment else 0.0
    tax = round(subtotal * 0.08, 2)
    total = round(subtotal + shipping + tax, 2)
    return {
        "subtotal": subtotal,
        "shipping": shipping,
        "tax": tax,
        "total": total,
        "currency": currency,
    }


def _normalize_currency(value: str | None) -> str:
    return (value or "USD").upper()


async def _resolve_prices(
    items: list[ACPCheckoutItem],
    currency: str,
) -> list[ACPCheckoutItem]:
    for item in items:
        if item.unit_price is None:
            price = await agent_client.calculate_dynamic_pricing(item.sku)
            if price is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Missing price for sku {item.sku}",
                )
            item.unit_price = price
        item.currency = _normalize_currency(item.currency or currency)
        if item.currency != currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="All items must use the same currency",
            )
    return items


def _merge_buyer(request_buyer: ACPBuyerInfo | None, current_user: User) -> ACPBuyerInfo:
    buyer = request_buyer or ACPBuyerInfo()
    if buyer.id is None:
        buyer.id = current_user.user_id
    if buyer.email is None:
        buyer.email = current_user.email
    if buyer.name is None:
        buyer.name = current_user.name
    return buyer


@router.post("/checkout/sessions", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a new ACP checkout session."""
    if not request.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one item is required",
        )

    currency = _normalize_currency(request.currency or request.items[0].currency)
    items = await _resolve_prices(request.items, currency)
    fulfillment_options = _default_fulfillment_options(currency)
    selected_fulfillment_id = fulfillment_options[0]["id"] if fulfillment_options else None
    selected_fulfillment = fulfillment_options[0] if fulfillment_options else None
    totals = _calculate_totals(items, selected_fulfillment, currency)
    now = datetime.utcnow().isoformat()

    session = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.user_id,
        "status": "created",
        "buyer": _merge_buyer(request.buyer, current_user).model_dump(),
        "items": [item.model_dump() for item in items],
        "shipping_address": request.shipping_address.model_dump()
        if request.shipping_address
        else None,
        "fulfillment_options": fulfillment_options,
        "selected_fulfillment_id": selected_fulfillment_id,
        "totals": totals,
        "created_at": now,
        "updated_at": now,
    }

    stored = await session_repo.create(session)
    return CheckoutSessionResponse(**stored)


@router.get("/checkout/sessions/{session_id}", response_model=CheckoutSessionResponse)
async def get_checkout_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Retrieve an ACP checkout session."""
    session = await session_repo.get_by_id(session_id, partition_key=current_user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return CheckoutSessionResponse(**session)


@router.patch("/checkout/sessions/{session_id}", response_model=CheckoutSessionResponse)
async def update_checkout_session(
    session_id: str,
    request: UpdateCheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
):
    """Update items, shipping address, or fulfillment selection."""
    session = await session_repo.get_by_id(session_id, partition_key=current_user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.get("status") in {"completed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not editable",
        )

    currency = _normalize_currency(session.get("totals", {}).get("currency"))
    if request.items is not None:
        items = await _resolve_prices(request.items, currency)
        session["items"] = [item.model_dump() for item in items]
    if request.shipping_address is not None:
        session["shipping_address"] = request.shipping_address.model_dump()
    if request.selected_fulfillment_id is not None:
        fulfillment_options = session.get("fulfillment_options", [])
        if not any(opt.get("id") == request.selected_fulfillment_id for opt in fulfillment_options):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid fulfillment option",
            )
        session["selected_fulfillment_id"] = request.selected_fulfillment_id

    fulfillment_options = session.get("fulfillment_options", [])
    selected_option = None
    for option in fulfillment_options:
        if option.get("id") == session.get("selected_fulfillment_id"):
            selected_option = option
            break

    items = [ACPCheckoutItem(**item) for item in session.get("items", [])]
    session["totals"] = _calculate_totals(items, selected_option, currency)
    session["status"] = "updated"
    session["updated_at"] = datetime.utcnow().isoformat()

    stored = await session_repo.update(session)
    return CheckoutSessionResponse(**stored)


@router.post(
    "/checkout/sessions/{session_id}/complete",
    response_model=CheckoutSessionResponse,
)
async def complete_checkout_session(
    session_id: str,
    request: CompleteCheckoutRequest,
    current_user: User = Depends(get_current_user),
):
    """Complete an ACP checkout session with a delegated payment token."""
    session = await session_repo.get_by_id(session_id, partition_key=current_user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.get("status") in {"completed", "cancelled"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session cannot be completed",
        )

    token = await payment_token_repo.get_by_id(
        request.payment_token,
        partition_key=current_user.user_id,
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment token not found",
        )
    if token.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment token is not active",
        )

    allowance = token.get("allowance", {})
    expires_at = allowance.get("expires_at")
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at) < datetime.utcnow():
                token["status"] = "expired"
                token["expired_at"] = datetime.utcnow().isoformat()
                await payment_token_repo.update(token)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Payment token expired",
                )
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid payment token expiry",
            ) from exc
    currency = _normalize_currency(allowance.get("currency"))
    totals = session.get("totals", {})
    if currency != _normalize_currency(totals.get("currency")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment token currency mismatch",
        )
    if allowance.get("merchant_id") != settings.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment token merchant mismatch",
        )
    if float(allowance.get("amount", 0)) < float(totals.get("total", 0)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment token allowance insufficient",
        )

    token["status"] = "used"
    token["used_at"] = datetime.utcnow().isoformat()
    await payment_token_repo.update(token)

    session["status"] = "completed"
    session["payment_token"] = request.payment_token
    session["updated_at"] = datetime.utcnow().isoformat()

    stored = await session_repo.update(session)

    items = [ACPCheckoutItem(**item) for item in session.get("items", [])]
    order_items = [
        {
            "product_id": item.sku,
            "quantity": item.quantity,
            "price": item.unit_price,
        }
        for item in items
    ]
    order = {
        "id": str(uuid.uuid4()),
        "user_id": current_user.user_id,
        "items": order_items,
        "total": totals.get("total", 0.0),
        "status": "paid",
        "shipping_address": session.get("shipping_address"),
        "created_at": datetime.utcnow().isoformat(),
        "source": "acp",
    }
    await order_repo.create(order)

    payment_event = {
        "id": str(uuid.uuid4()),
        "order_id": order["id"],
        "user_id": current_user.user_id,
        "amount": totals.get("total", 0.0),
        "status": "completed",
        "created_at": datetime.utcnow().isoformat(),
        "token_id": request.payment_token,
    }
    await event_publisher.publish_order_created(order)
    await event_publisher.publish_payment_processed(payment_event)

    return CheckoutSessionResponse(**stored)


@router.delete("/checkout/sessions/{session_id}", response_model=CheckoutSessionResponse)
async def cancel_checkout_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """Cancel an ACP checkout session."""
    session = await session_repo.get_by_id(session_id, partition_key=current_user.user_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.get("status") == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed session cannot be cancelled",
        )

    session["status"] = "cancelled"
    session["updated_at"] = datetime.utcnow().isoformat()

    stored = await session_repo.update(session)
    return CheckoutSessionResponse(**stored)
