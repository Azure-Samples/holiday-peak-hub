"""Inventory and reservation routes."""

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from crud_service.auth import User, get_current_user
from crud_service.repositories import InventoryRepository, ReservationRepository
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter()

ReservationStatus = Literal["created", "confirmed", "released"]

ERR_INVENTORY_NOT_FOUND = "Inventory not found"
ERR_RESERVATION_NOT_FOUND = "Reservation not found"
ERR_NO_MUTABLE_FIELDS = "No mutable fields provided"
ERR_NO_THRESHOLD_FIELDS = "No threshold fields provided"
ERR_INVALID_RESERVED_EXCEEDS_ON_HAND = "reserved_quantity cannot exceed quantity_on_hand"
ERR_INVALID_RESERVED_NEGATIVE = "reserved_quantity cannot be negative"
ERR_INVALID_ON_HAND_NEGATIVE = "quantity_on_hand cannot be negative"
ERR_INSUFFICIENT_AVAILABLE = "Insufficient available inventory"
ERR_RESERVATION_INVENTORY_NOT_FOUND = "Inventory for reservation sku not found"
ERR_RESERVED_LOWER_THAN_RESERVATION = (
    "Inventory reserved quantity is lower than reservation quantity"
)
ERR_RESERVATION_CREATE_FAILED = "Failed to persist reservation"

ALLOWED_RESERVATION_TRANSITIONS: dict[str, set[str]] = {
    "created": {"confirmed", "released"},
    "confirmed": set(),
    "released": set(),
}

inventory_repo = InventoryRepository()
reservation_repo = ReservationRepository()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _compute_health_fields(inventory: dict[str, Any]) -> None:
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


def _append_audit(
    payload: dict[str, Any],
    *,
    action: str,
    actor: User,
    details: dict[str, Any] | None = None,
) -> None:
    entry: dict[str, Any] = {
        "action": action,
        "at": _utc_now_iso(),
        "actor_id": actor.user_id,
        "actor_roles": list(actor.roles or []),
    }
    if details:
        entry["details"] = details
    payload.setdefault("audit_log", []).append(entry)


def _append_status_history(
    payload: dict[str, Any],
    *,
    from_status: str | None,
    to_status: str,
    actor: User,
    reason: str | None = None,
) -> None:
    payload.setdefault("status_history", []).append(
        {
            "from": from_status,
            "to": to_status,
            "at": _utc_now_iso(),
            "actor_id": actor.user_id,
            "reason": reason,
        }
    )


def _has_staff_or_admin(user: User) -> bool:
    return bool({"staff", "admin"}.intersection(set(user.roles or [])))


def _ensure_reservation_access(reservation: dict[str, Any], current_user: User) -> None:
    if _has_staff_or_admin(current_user):
        return

    reservation_owner = str(reservation.get("created_by") or "")
    if reservation_owner != current_user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )


def _ensure_inventory_mutation_access(current_user: User) -> None:
    if _has_staff_or_admin(current_user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Role 'staff' or 'admin' required",
    )


class InventoryResponse(BaseModel):
    """Inventory response model."""

    id: str
    sku: str
    quantity_on_hand: int
    reserved_quantity: int
    available_quantity: int
    reorder_point: int
    safety_stock: int
    low_stock: bool
    health_status: Literal["healthy", "low_stock", "out_of_stock"]
    created_at: str
    updated_at: str
    created_by: str
    updated_by: str
    audit_log: list[dict[str, Any]] = Field(default_factory=list)


class PatchInventoryRequest(BaseModel):
    """Partial inventory patch request."""

    quantity_on_hand: int | None = Field(default=None, ge=0)
    reserved_quantity: int | None = Field(default=None, ge=0)


class PatchThresholdsRequest(BaseModel):
    """Inventory thresholds patch request."""

    reorder_point: int | None = Field(default=None, ge=0)
    safety_stock: int | None = Field(default=None, ge=0)


class InventoryHealthResponse(BaseModel):
    """Inventory health summary response."""

    total_skus: int
    healthy: int
    low_stock: int
    out_of_stock: int
    items: list[InventoryResponse]


class CreateReservationRequest(BaseModel):
    """Create inventory reservation request."""

    sku: str
    quantity: int = Field(gt=0)
    reason: str | None = None

    @field_validator("sku")
    @classmethod
    def _validate_sku(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("sku must not be empty")
        return value

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ReservationActionRequest(BaseModel):
    """Reservation action request."""

    reason: str | None = None

    @field_validator("reason")
    @classmethod
    def _normalize_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class ReservationResponse(BaseModel):
    """Inventory reservation response."""

    id: str
    sku: str
    quantity: int
    status: ReservationStatus
    created_at: str
    updated_at: str
    created_by: str
    updated_by: str
    confirmed_at: str | None = None
    confirmed_by: str | None = None
    released_at: str | None = None
    released_by: str | None = None
    reason: str | None = None
    status_history: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)


def _validate_inventory_quantities(inventory: dict[str, Any]) -> None:
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


@router.get("/inventory/health", response_model=InventoryHealthResponse)
async def get_inventory_health(_current_user: User = Depends(get_current_user)):
    """Return inventory health summary."""
    items = await inventory_repo.query(
        query="SELECT * FROM c ORDER BY c.updated_at DESC OFFSET 0 LIMIT 200",
    )
    responses: list[InventoryResponse] = [InventoryResponse(**item) for item in items]

    healthy = sum(1 for item in responses if item.health_status == "healthy")
    low_stock = sum(1 for item in responses if item.health_status == "low_stock")
    out_of_stock = sum(1 for item in responses if item.health_status == "out_of_stock")

    return InventoryHealthResponse(
        total_skus=len(responses),
        healthy=healthy,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        items=responses,
    )


@router.get("/inventory/{sku}", response_model=InventoryResponse)
async def get_inventory(sku: str, _current_user: User = Depends(get_current_user)):
    """Get inventory by SKU."""
    inventory = await inventory_repo.get_by_id(sku)
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_INVENTORY_NOT_FOUND,
        )
    return InventoryResponse(**inventory)


@router.patch("/inventory/{sku}", response_model=InventoryResponse)
async def patch_inventory(
    sku: str,
    request: PatchInventoryRequest,
    current_user: User = Depends(get_current_user),
):
    """Patch quantity fields for an inventory SKU."""
    _ensure_inventory_mutation_access(current_user)

    inventory = await inventory_repo.get_by_id(sku)
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_INVENTORY_NOT_FOUND,
        )

    changed_fields: list[str] = []
    if request.quantity_on_hand is not None:
        inventory["quantity_on_hand"] = request.quantity_on_hand
        changed_fields.append("quantity_on_hand")
    if request.reserved_quantity is not None:
        inventory["reserved_quantity"] = request.reserved_quantity
        changed_fields.append("reserved_quantity")

    if not changed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_NO_MUTABLE_FIELDS,
        )

    _validate_inventory_quantities(inventory)
    _compute_health_fields(inventory)

    inventory["updated_at"] = _utc_now_iso()
    inventory["updated_by"] = current_user.user_id
    _append_audit(
        inventory,
        action="inventory_patched",
        actor=current_user,
        details={"changed_fields": changed_fields},
    )
    await inventory_repo.update(inventory)
    return InventoryResponse(**inventory)


@router.patch("/inventory/{sku}/thresholds", response_model=InventoryResponse)
async def patch_inventory_thresholds(
    sku: str,
    request: PatchThresholdsRequest,
    current_user: User = Depends(get_current_user),
):
    """Patch thresholds for an inventory SKU."""
    _ensure_inventory_mutation_access(current_user)

    inventory = await inventory_repo.get_by_id(sku)
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_INVENTORY_NOT_FOUND,
        )

    changed_fields: list[str] = []
    if request.reorder_point is not None:
        inventory["reorder_point"] = request.reorder_point
        changed_fields.append("reorder_point")
    if request.safety_stock is not None:
        inventory["safety_stock"] = request.safety_stock
        changed_fields.append("safety_stock")

    if not changed_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ERR_NO_THRESHOLD_FIELDS,
        )

    _validate_inventory_quantities(inventory)
    _compute_health_fields(inventory)

    inventory["updated_at"] = _utc_now_iso()
    inventory["updated_by"] = current_user.user_id
    _append_audit(
        inventory,
        action="thresholds_patched",
        actor=current_user,
        details={"changed_fields": changed_fields},
    )
    await inventory_repo.update(inventory)
    return InventoryResponse(**inventory)


@router.post("/inventory/reservations", response_model=ReservationResponse, status_code=201)
async def create_reservation(
    request: CreateReservationRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a reservation and lock inventory quantity."""
    inventory = await inventory_repo.get_by_id(request.sku)
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_INVENTORY_NOT_FOUND,
        )

    quantity_on_hand = int(inventory.get("quantity_on_hand", 0))
    reserved_quantity = int(inventory.get("reserved_quantity", 0))
    available_quantity = max(quantity_on_hand - reserved_quantity, 0)
    if request.quantity > available_quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_INSUFFICIENT_AVAILABLE,
        )

    now = _utc_now_iso()
    reservation = {
        "id": str(uuid.uuid4()),
        "sku": request.sku,
        "quantity": request.quantity,
        "status": "created",
        "created_at": now,
        "updated_at": now,
        "created_by": current_user.user_id,
        "updated_by": current_user.user_id,
        "reason": request.reason,
        "status_history": [],
        "audit_log": [],
    }
    _append_status_history(
        reservation,
        from_status=None,
        to_status="created",
        actor=current_user,
        reason="Reservation created",
    )
    _append_audit(
        reservation,
        action="reservation_created",
        actor=current_user,
        details={"quantity": request.quantity, "sku": request.sku},
    )

    inventory["reserved_quantity"] = int(inventory.get("reserved_quantity", 0)) + request.quantity
    _validate_inventory_quantities(inventory)
    _compute_health_fields(inventory)
    inventory["updated_at"] = now
    inventory["updated_by"] = current_user.user_id
    _append_audit(
        inventory,
        action="reservation_locked",
        actor=current_user,
        details={"reservation_id": reservation["id"], "quantity": request.quantity},
    )

    await inventory_repo.update(inventory)
    try:
        await reservation_repo.create(reservation)
    except Exception as exc:
        inventory["reserved_quantity"] = max(
            int(inventory.get("reserved_quantity", 0)) - request.quantity,
            0,
        )
        _validate_inventory_quantities(inventory)
        _compute_health_fields(inventory)
        inventory["updated_at"] = _utc_now_iso()
        inventory["updated_by"] = current_user.user_id
        _append_audit(
            inventory,
            action="reservation_lock_rollback",
            actor=current_user,
            details={
                "reservation_id": reservation["id"],
                "quantity": request.quantity,
                "reason": ERR_RESERVATION_CREATE_FAILED,
            },
        )
        await inventory_repo.update(inventory)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ERR_RESERVATION_CREATE_FAILED,
        ) from exc

    return ReservationResponse(**reservation)


@router.get("/inventory/reservations/{reservation_id}", response_model=ReservationResponse)
async def get_reservation(
    reservation_id: str,
    current_user: User = Depends(get_current_user),
):
    """Get reservation by id."""
    reservation = await reservation_repo.get_by_id(reservation_id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_RESERVATION_NOT_FOUND,
        )

    _ensure_reservation_access(reservation, current_user)

    return ReservationResponse(**reservation)


def _ensure_transition_allowed(current_status: str, new_status: str) -> None:
    allowed = ALLOWED_RESERVATION_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid reservation status transition: {current_status} -> {new_status}",
        )


@router.post("/inventory/reservations/{reservation_id}/confirm", response_model=ReservationResponse)
async def confirm_reservation(
    reservation_id: str,
    request: ReservationActionRequest,
    current_user: User = Depends(get_current_user),
):
    """Confirm a reservation; idempotent when already confirmed."""
    reservation = await reservation_repo.get_by_id(reservation_id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_RESERVATION_NOT_FOUND,
        )

    _ensure_reservation_access(reservation, current_user)

    if reservation["status"] == "confirmed":
        return ReservationResponse(**reservation)

    _ensure_transition_allowed(reservation["status"], "confirmed")

    now = _utc_now_iso()
    previous_status = reservation["status"]
    reservation["status"] = "confirmed"
    reservation["updated_at"] = now
    reservation["updated_by"] = current_user.user_id
    reservation["confirmed_at"] = now
    reservation["confirmed_by"] = current_user.user_id

    _append_status_history(
        reservation,
        from_status=previous_status,
        to_status="confirmed",
        actor=current_user,
        reason=request.reason,
    )
    _append_audit(
        reservation,
        action="reservation_confirmed",
        actor=current_user,
        details={"reason": request.reason},
    )

    await reservation_repo.update(reservation)
    return ReservationResponse(**reservation)


@router.post("/inventory/reservations/{reservation_id}/release", response_model=ReservationResponse)
async def release_reservation(
    reservation_id: str,
    request: ReservationActionRequest,
    current_user: User = Depends(get_current_user),
):
    """Release a reservation; idempotent when already released."""
    reservation = await reservation_repo.get_by_id(reservation_id)
    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ERR_RESERVATION_NOT_FOUND,
        )

    _ensure_reservation_access(reservation, current_user)

    if reservation["status"] == "released":
        return ReservationResponse(**reservation)

    _ensure_transition_allowed(reservation["status"], "released")

    inventory = await inventory_repo.get_by_id(reservation["sku"])
    if not inventory:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_RESERVATION_INVENTORY_NOT_FOUND,
        )

    reserved_quantity = int(inventory.get("reserved_quantity", 0))
    if reserved_quantity < int(reservation["quantity"]):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ERR_RESERVED_LOWER_THAN_RESERVATION,
        )

    now = _utc_now_iso()

    previous_status = reservation["status"]
    reservation["status"] = "released"
    reservation["updated_at"] = now
    reservation["updated_by"] = current_user.user_id
    reservation["released_at"] = now
    reservation["released_by"] = current_user.user_id

    _append_status_history(
        reservation,
        from_status=previous_status,
        to_status="released",
        actor=current_user,
        reason=request.reason,
    )
    _append_audit(
        reservation,
        action="reservation_released",
        actor=current_user,
        details={"reason": request.reason},
    )

    inventory["reserved_quantity"] = reserved_quantity - int(reservation["quantity"])
    _validate_inventory_quantities(inventory)
    _compute_health_fields(inventory)
    inventory["updated_at"] = now
    inventory["updated_by"] = current_user.user_id
    _append_audit(
        inventory,
        action="reservation_released",
        actor=current_user,
        details={
            "reservation_id": reservation_id,
            "quantity": reservation["quantity"],
        },
    )

    await reservation_repo.update(reservation)
    await inventory_repo.update(inventory)
    return ReservationResponse(**reservation)
