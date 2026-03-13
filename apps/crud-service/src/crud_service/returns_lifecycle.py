"""Shared return and refund lifecycle models and transition logic."""

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import HTTPException, status
from pydantic import BaseModel, Field

ReturnStatus = Literal[
    "requested",
    "approved",
    "rejected",
    "received",
    "restocked",
    "refunded",
]

RefundStatus = Literal["issued"]

RETURN_STATUS_TIMESTAMP_FIELD: dict[str, str] = {
    "requested": "requested_at",
    "approved": "approved_at",
    "rejected": "rejected_at",
    "received": "received_at",
    "restocked": "restocked_at",
    "refunded": "refunded_at",
}

ALLOWED_RETURN_TRANSITIONS: dict[str, set[str]] = {
    "requested": {"approved", "rejected"},
    "approved": {"received"},
    "rejected": set(),
    "received": {"restocked"},
    "restocked": {"refunded"},
    "refunded": set(),
}

RETURN_TRANSITION_EVENTS: dict[str, str] = {
    "requested": "ReturnRequested",
    "approved": "ReturnApproved",
    "rejected": "ReturnRejected",
    "received": "ReturnReceived",
    "restocked": "ReturnRestocked",
    "refunded": "ReturnRefunded",
}


class ReturnCreateRequest(BaseModel):
    """Customer return creation request."""

    order_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    items: list[dict[str, Any]] = Field(default_factory=list)


class ReturnTransitionRequest(BaseModel):
    """Staff transition request."""

    reason: str | None = None


class RefundResponse(BaseModel):
    """Refund progression response."""

    id: str
    return_id: str
    order_id: str
    user_id: str
    status: RefundStatus
    created_at: str
    updated_at: str
    issued_at: str
    last_transition_at: str
    requested_at: str
    status_history: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)


class ReturnResponse(BaseModel):
    """Canonical return response for staff and customer APIs."""

    id: str
    order_id: str
    user_id: str
    status: ReturnStatus
    reason: str
    items: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str
    requested_at: str
    approved_at: str | None = None
    rejected_at: str | None = None
    received_at: str | None = None
    restocked_at: str | None = None
    refunded_at: str | None = None
    last_transition_at: str
    status_history: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    refund: RefundResponse | None = None
    idempotent: bool = False


def utc_now_iso() -> str:
    """Return ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def ensure_valid_transition(*, current_status: str, target_status: ReturnStatus) -> None:
    """Validate deterministic lifecycle transition rules."""
    current = current_status
    allowed = ALLOWED_RETURN_TRANSITIONS.get(current)
    if allowed is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Unknown return status: {current_status}",
        )

    if target_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid return status transition: {current_status} -> {target_status}",
        )


def build_sla_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Create SLA timestamp snapshot for event payloads."""
    return {
        "requested_at": payload.get("requested_at"),
        "approved_at": payload.get("approved_at"),
        "rejected_at": payload.get("rejected_at"),
        "received_at": payload.get("received_at"),
        "restocked_at": payload.get("restocked_at"),
        "refunded_at": payload.get("refunded_at"),
        "last_transition_at": payload.get("last_transition_at"),
    }


def append_history(
    payload: dict[str, Any],
    *,
    from_status: str | None,
    to_status: ReturnStatus,
    actor_id: str,
    actor_roles: list[str],
    reason: str | None,
    occurred_at: str,
) -> None:
    """Append transition history and audit entries."""
    payload.setdefault("status_history", []).append(
        {
            "from": from_status,
            "to": to_status,
            "at": occurred_at,
            "actor_id": actor_id,
            "actor_roles": actor_roles,
            "reason": reason,
        }
    )
    payload.setdefault("audit_log", []).append(
        {
            "action": f"return_{to_status}",
            "at": occurred_at,
            "actor_id": actor_id,
            "actor_roles": actor_roles,
            "reason": reason,
        }
    )


def create_return_record(
    *,
    order_id: str,
    user_id: str,
    reason: str,
    items: list[dict[str, Any]],
    actor_id: str,
    actor_roles: list[str],
) -> dict[str, Any]:
    """Initialize canonical return record in requested state."""
    now = utc_now_iso()
    record = {
        "id": str(uuid.uuid4()),
        "order_id": order_id,
        "user_id": user_id,
        "status": "requested",
        "reason": reason,
        "items": items,
        "created_at": now,
        "updated_at": now,
        "requested_at": now,
        "approved_at": None,
        "rejected_at": None,
        "received_at": None,
        "restocked_at": None,
        "refunded_at": None,
        "last_transition_at": now,
        "status_history": [],
        "audit_log": [],
    }
    append_history(
        record,
        from_status=None,
        to_status="requested",
        actor_id=actor_id,
        actor_roles=actor_roles,
        reason=reason,
        occurred_at=now,
    )
    return record


def transition_return_record(
    payload: dict[str, Any],
    *,
    target_status: ReturnStatus,
    actor_id: str,
    actor_roles: list[str],
    reason: str | None,
) -> bool:
    """Apply deterministic lifecycle transition; return True if idempotent no-op."""
    current_status = payload.get("status")
    if not isinstance(current_status, str):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unknown return status: null",
        )
    if current_status == target_status:
        return True

    ensure_valid_transition(current_status=current_status, target_status=target_status)

    occurred_at = utc_now_iso()
    payload["status"] = target_status
    payload["updated_at"] = occurred_at
    payload["last_transition_at"] = occurred_at
    payload[RETURN_STATUS_TIMESTAMP_FIELD[target_status]] = occurred_at

    append_history(
        payload,
        from_status=current_status,
        to_status=target_status,
        actor_id=actor_id,
        actor_roles=actor_roles,
        reason=reason,
        occurred_at=occurred_at,
    )
    return False


def create_refund_record(
    *,
    return_payload: dict[str, Any],
    actor_id: str,
    actor_roles: list[str],
) -> dict[str, Any]:
    """Create refund progression record at the issued point."""
    now = utc_now_iso()
    return {
        "id": str(uuid.uuid4()),
        "return_id": return_payload["id"],
        "order_id": return_payload["order_id"],
        "user_id": return_payload["user_id"],
        "status": "issued",
        "created_at": now,
        "updated_at": now,
        "requested_at": return_payload.get("requested_at"),
        "issued_at": now,
        "last_transition_at": now,
        "status_history": [
            {
                "from": None,
                "to": "issued",
                "at": now,
                "actor_id": actor_id,
                "actor_roles": actor_roles,
            }
        ],
        "audit_log": [
            {
                "action": "refund_issued",
                "at": now,
                "actor_id": actor_id,
                "actor_roles": actor_roles,
            }
        ],
    }


def event_data(
    *,
    payload: dict[str, Any],
    actor_id: str,
    actor_roles: list[str],
    occurred_at: str,
) -> dict[str, Any]:
    """Build return lifecycle event data payload."""
    return {
        "return_id": payload["id"],
        "order_id": payload["order_id"],
        "user_id": payload["user_id"],
        "status": payload["status"],
        "occurred_at": occurred_at,
        "actor_id": actor_id,
        "actor_roles": actor_roles,
        "sla": build_sla_snapshot(payload),
        "timestamp": occurred_at,
    }
