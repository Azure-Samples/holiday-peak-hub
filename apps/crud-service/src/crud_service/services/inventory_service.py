"""Business logic for inventory and reservation operations."""

from datetime import datetime, timezone
from typing import Any

from crud_service.auth import User
from fastapi import HTTPException, status

ERR_INVALID_RESERVED_EXCEEDS_ON_HAND = "reserved_quantity cannot exceed quantity_on_hand"
ERR_INVALID_RESERVED_NEGATIVE = "reserved_quantity cannot be negative"
ERR_INVALID_ON_HAND_NEGATIVE = "quantity_on_hand cannot be negative"

ALLOWED_RESERVATION_TRANSITIONS: dict[str, set[str]] = {
    "created": {"confirmed", "released"},
    "confirmed": set(),
    "released": set(),
}


def utc_now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


def compute_health_fields(inventory: dict[str, Any]) -> None:
    """Compute inventory health projection fields in-place."""
    quantity_on_hand = int(inventory.get("quantity_on_hand", 0))
    reserved_quantity = int(inventory.get("reserved_quantity", 0))
    reorder_point = int(inventory.get("reorder_point", 0))

    available_quantity = max(quantity_on_hand - reserved_quantity, 0)
    inventory["available_quantity"] = available_quantity
    inventory["low_stock"] = available_quantity <= reorder_point

    if available_quantity == 0:
        inventory["health_status"] = "out_of_stock"
    elif inventory["low_stock"]:
        inventory["health_status"] = "low_stock"
    else:
        inventory["health_status"] = "healthy"


def append_audit(
    payload: dict[str, Any],
    *,
    action: str,
    actor: User,
    details: dict[str, Any] | None = None,
) -> None:
    """Append an audit event to a mutable payload."""
    entry: dict[str, Any] = {
        "action": action,
        "at": utc_now_iso(),
        "actor_id": actor.user_id,
        "actor_roles": list(actor.roles or []),
    }
    if details:
        entry["details"] = details
    payload.setdefault("audit_log", []).append(entry)


def append_status_history(
    payload: dict[str, Any],
    *,
    from_status: str | None,
    to_status: str,
    actor: User,
    reason: str | None = None,
) -> None:
    """Append a reservation status transition entry."""
    payload.setdefault("status_history", []).append(
        {
            "from": from_status,
            "to": to_status,
            "at": utc_now_iso(),
            "actor_id": actor.user_id,
            "reason": reason,
        }
    )


def validate_inventory_quantities(inventory: dict[str, Any]) -> None:
    """Validate inventory quantity invariants."""
    quantity_on_hand = int(inventory.get("quantity_on_hand", 0))
    reserved_quantity = int(inventory.get("reserved_quantity", 0))
    if quantity_on_hand < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_INVALID_ON_HAND_NEGATIVE,
        )
    if reserved_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_INVALID_RESERVED_NEGATIVE,
        )
    if reserved_quantity > quantity_on_hand:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_INVALID_RESERVED_EXCEEDS_ON_HAND,
        )


def ensure_transition_allowed(current_status: str, new_status: str) -> None:
    """Validate reservation transition against allowed state machine."""
    allowed = ALLOWED_RESERVATION_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid reservation status transition: {current_status} -> {new_status}",
        )
