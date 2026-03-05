"""Canonical connector synchronization event schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, TypeAdapter


class ConnectorEvent(BaseModel):
    """Base envelope for all connector synchronization events."""

    event_id: str = Field(default_factory=lambda: str(uuid4()))
    source_system: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str | None = None
    trace_id: str | None = None


class ProductChanged(ConnectorEvent):
    """Product metadata mutation from PIM/DAM connectors."""

    event_type: Literal["ProductChanged"] = "ProductChanged"
    product_id: str = Field(min_length=1)
    name: str | None = None
    description: str | None = None
    category_id: str | None = None
    image_url: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class InventoryUpdated(ConnectorEvent):
    """Inventory mutation from ERP/WMS connectors."""

    event_type: Literal["InventoryUpdated"] = "InventoryUpdated"
    product_id: str = Field(min_length=1)
    quantity: int
    location_id: str | None = None
    available: bool | None = None


class CustomerUpdated(ConnectorEvent):
    """Customer profile mutation from CRM connectors."""

    event_type: Literal["CustomerUpdated"] = "CustomerUpdated"
    customer_id: str = Field(min_length=1)
    email: str | None = None
    name: str | None = None
    phone: str | None = None
    loyalty_tier: str | None = None
    profile: dict[str, Any] = Field(default_factory=dict)


class OrderStatusChanged(ConnectorEvent):
    """Order lifecycle mutation from OMS connectors."""

    event_type: Literal["OrderStatusChanged"] = "OrderStatusChanged"
    order_id: str = Field(min_length=1)
    status: str = Field(min_length=1)
    status_reason: str | None = None
    tracking_id: str | None = None


class PriceUpdated(ConnectorEvent):
    """Pricing mutation from pricing connectors."""

    event_type: Literal["PriceUpdated"] = "PriceUpdated"
    product_id: str = Field(min_length=1)
    price: float
    currency: str = Field(default="USD", min_length=3, max_length=3)
    effective_from: datetime | None = None


ConnectorEventUnion = (
    ProductChanged | InventoryUpdated | CustomerUpdated | OrderStatusChanged | PriceUpdated
)

_CONNECTOR_EVENT_ADAPTER = TypeAdapter(ConnectorEventUnion)


def parse_connector_event(payload: dict[str, Any]) -> ConnectorEventUnion:
    """Parse a raw payload into a typed connector event model."""

    return _CONNECTOR_EVENT_ADAPTER.validate_python(payload)
