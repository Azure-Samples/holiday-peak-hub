"""ACP delegate payment routes."""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from crud_service.auth import User, get_current_user
from crud_service.config import get_settings
from crud_service.repositories import PaymentTokenRepository

router = APIRouter()
settings = get_settings()
payment_token_repo = PaymentTokenRepository()


class Allowance(BaseModel):
    """Delegated payment allowance constraints."""

    amount: float = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)
    merchant_id: str | None = None
    expires_at: str | None = None


class DelegatePaymentRequest(BaseModel):
    """Request to create a delegated payment token."""

    payment_method_id: str
    allowance: Allowance
    risk_signals: dict[str, Any] | None = None


class DelegatePaymentResponse(BaseModel):
    """Delegated payment token response."""

    token: str
    allowance: Allowance
    status: str
    created_at: str
    expires_at: str | None = None


@router.post("/payments/delegate", response_model=DelegatePaymentResponse)
async def delegate_payment(
    request: DelegatePaymentRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create a delegated payment token with allowance constraints.

    This is a demo PSP implementation for ACP flows.
    """
    token = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    allowance = request.allowance
    currency = allowance.currency.upper()
    merchant_id = allowance.merchant_id or settings.merchant_id

    record = {
        "id": token,
        "user_id": current_user.user_id,
        "payment_method_id": request.payment_method_id,
        "allowance": {
            "amount": allowance.amount,
            "currency": currency,
            "merchant_id": merchant_id,
            "expires_at": allowance.expires_at,
        },
        "risk_signals": request.risk_signals or {},
        "status": "active",
        "created_at": created_at,
        "expires_at": allowance.expires_at,
    }

    await payment_token_repo.create(record)

    return DelegatePaymentResponse(
        token=token,
        allowance=Allowance(
            amount=allowance.amount,
            currency=currency,
            merchant_id=merchant_id,
            expires_at=allowance.expires_at,
        ),
        status="active",
        created_at=created_at,
        expires_at=allowance.expires_at,
    )
