"""External API DTOs for inventory routes."""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

ReservationStatus = Literal["created", "confirmed", "released"]


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
