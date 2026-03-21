"""Canonical retail event schemas for cross-service Event Hub contracts."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

OrderEventType = Literal["OrderCreated", "OrderUpdated", "OrderCancelled"]
PaymentEventType = Literal["PaymentProcessed", "PaymentFailed", "RefundIssued"]
ReturnEventType = Literal[
    "ReturnRequested",
    "ReturnApproved",
    "ReturnRejected",
    "ReturnReceived",
    "ReturnRestocked",
    "ReturnRefunded",
]
InventoryEventType = Literal["InventoryReserved", "InventoryReleased", "InventoryUpdated"]
ShipmentEventType = Literal["ShipmentCreated", "ShipmentUpdated"]

RETAIL_EVENT_TOPICS: tuple[str, ...] = (
    "order-events",
    "payment-events",
    "return-events",
    "inventory-events",
    "shipment-events",
)


class _RetailEventData(BaseModel):
    model_config = ConfigDict(extra="allow")


class OrderEventData(_RetailEventData):
    """Order event payload with compatibility aliases."""

    order_id: str | None = None
    user_id: str | None = None
    status: str | None = None
    total: float | None = None
    items: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None
    tracking_id: str | None = None
    shipment_id: str | None = None
    timestamp: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_order_id(cls, value: Any) -> Any:
        if isinstance(value, dict) and not value.get("order_id") and value.get("id"):
            value = dict(value)
            value["order_id"] = value["id"]
        return value

    @model_validator(mode="after")
    def _require_order_id(self) -> "OrderEventData":
        if not self.order_id:
            raise ValueError("Order event payload requires order_id (or id)")
        return self


class PaymentEventData(_RetailEventData):
    """Payment/refund event payload."""

    payment_id: str | None = None
    order_id: str | None = None
    user_id: str | None = None
    amount: float | None = None
    status: str | None = None
    transaction_id: str | None = None
    created_at: str | None = None
    occurred_at: str | None = None
    timestamp: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_payment_id(cls, value: Any) -> Any:
        if isinstance(value, dict) and not value.get("payment_id") and value.get("id"):
            value = dict(value)
            value["payment_id"] = value["id"]
        return value

    @model_validator(mode="after")
    def _require_order_id(self) -> "PaymentEventData":
        if not self.order_id:
            raise ValueError("Payment event payload requires order_id")
        return self


class ReturnEventData(_RetailEventData):
    """Return lifecycle event payload."""

    return_id: str | None = None
    order_id: str | None = None
    user_id: str | None = None
    status: str | None = None
    occurred_at: str | None = None
    actor_id: str | None = None
    actor_roles: list[str] = Field(default_factory=list)
    sla: dict[str, Any] = Field(default_factory=dict)
    timestamp: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_return_id(cls, value: Any) -> Any:
        if isinstance(value, dict) and not value.get("return_id") and value.get("id"):
            value = dict(value)
            value["return_id"] = value["id"]
        return value

    @model_validator(mode="after")
    def _require_ids(self) -> "ReturnEventData":
        if not self.return_id:
            raise ValueError("Return event payload requires return_id (or id)")
        if not self.order_id:
            raise ValueError("Return event payload requires order_id")
        return self


class InventoryEventData(_RetailEventData):
    """Inventory lifecycle event payload."""

    sku: str | None = None
    quantity: int | None = None
    user_id: str | None = None
    order_id: str | None = None
    reservation_id: str | None = None
    location_id: str | None = None
    timestamp: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_sku(cls, value: Any) -> Any:
        if isinstance(value, dict) and not value.get("sku") and value.get("product_id"):
            value = dict(value)
            value["sku"] = value["product_id"]
        return value

    @model_validator(mode="after")
    def _require_sku(self) -> "InventoryEventData":
        if not self.sku:
            raise ValueError("Inventory event payload requires sku (or product_id)")
        return self


class ShipmentEventData(_RetailEventData):
    """Shipment lifecycle event payload."""

    shipment_id: str | None = None
    tracking_id: str | None = None
    order_id: str | None = None
    user_id: str | None = None
    status: str | None = None
    carrier: str | None = None
    eta: str | None = None
    timestamp: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_shipment_id(cls, value: Any) -> Any:
        if isinstance(value, dict):
            copy = dict(value)
            if not copy.get("shipment_id") and copy.get("tracking_id"):
                copy["shipment_id"] = copy["tracking_id"]
            if not copy.get("tracking_id") and copy.get("shipment_id"):
                copy["tracking_id"] = copy["shipment_id"]
            if not copy.get("shipment_id") and copy.get("id"):
                copy["shipment_id"] = copy["id"]
                copy.setdefault("tracking_id", copy["id"])
            return copy
        return value

    @model_validator(mode="after")
    def _require_shipment_identifier(self) -> "ShipmentEventData":
        if not self.shipment_id and not self.tracking_id:
            raise ValueError("Shipment event payload requires shipment_id/tracking_id (or id)")
        return self


class _RetailEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _default_timestamp(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        data = value.get("data") if isinstance(value.get("data"), dict) else {}
        timestamp = value.get("timestamp")
        if not timestamp:
            timestamp = (
                data.get("timestamp")
                or data.get("occurred_at")
                or data.get("created_at")
                or datetime.now(UTC).isoformat()
            )

        normalized = dict(value)
        normalized["timestamp"] = str(timestamp)
        return normalized


class OrderEventEnvelope(_RetailEventEnvelope):
    """Order event envelope."""

    event_type: OrderEventType
    data: OrderEventData


class PaymentEventEnvelope(_RetailEventEnvelope):
    """Payment event envelope."""

    event_type: PaymentEventType
    data: PaymentEventData


class ReturnEventEnvelope(_RetailEventEnvelope):
    """Return event envelope."""

    event_type: ReturnEventType
    data: ReturnEventData


class InventoryEventEnvelope(_RetailEventEnvelope):
    """Inventory event envelope."""

    event_type: InventoryEventType
    data: InventoryEventData


class ShipmentEventEnvelope(_RetailEventEnvelope):
    """Shipment event envelope."""

    event_type: ShipmentEventType
    data: ShipmentEventData


RetailEvent = (
    OrderEventEnvelope
    | PaymentEventEnvelope
    | ReturnEventEnvelope
    | InventoryEventEnvelope
    | ShipmentEventEnvelope
)

_RETAIL_TOPIC_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "order-events": TypeAdapter(OrderEventEnvelope),
    "payment-events": TypeAdapter(PaymentEventEnvelope),
    "return-events": TypeAdapter(ReturnEventEnvelope),
    "inventory-events": TypeAdapter(InventoryEventEnvelope),
    "shipment-events": TypeAdapter(ShipmentEventEnvelope),
}
_RETAIL_EVENT_ADAPTER = TypeAdapter(RetailEvent)


def parse_retail_event(
    payload: dict[str, Any],
    *,
    topic: str | None = None,
) -> RetailEvent:
    """Parse a retail event envelope into a canonical typed model."""

    if topic is not None:
        adapter = _RETAIL_TOPIC_ADAPTERS.get(topic)
        if adapter is None:
            raise ValueError(f"Unsupported retail event topic: {topic}")
        return adapter.validate_python(payload)

    return _RETAIL_EVENT_ADAPTER.validate_python(payload)


def build_retail_event_payload(
    *,
    topic: str,
    event_type: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Build and validate a canonical event payload for Event Hub publication."""

    payload = {
        "event_type": event_type,
        "data": data,
        "timestamp": data.get("timestamp") if isinstance(data, dict) else None,
    }
    parsed = parse_retail_event(payload, topic=topic)
    return parsed.model_dump(mode="json")
