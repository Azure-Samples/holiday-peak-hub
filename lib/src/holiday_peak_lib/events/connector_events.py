"""Canonical connector synchronization event schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from holiday_peak_lib.events.versioning import (
    CURRENT_EVENT_SCHEMA_VERSION,
    SchemaCompatibilityPolicy,
)
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, model_validator

CONNECTOR_SCHEMA_POLICY = SchemaCompatibilityPolicy(CURRENT_EVENT_SCHEMA_VERSION)


class ConnectorEvent(BaseModel):
    """Base envelope for all connector synchronization events."""

    model_config = ConfigDict(extra="allow")

    schema_version: str = CURRENT_EVENT_SCHEMA_VERSION
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    source_system: str = Field(min_length=1)
    entity_id: str = Field(min_length=1)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    tenant_id: str | None = None
    trace_id: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_schema_version(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        normalized = dict(value)
        normalized["schema_version"] = CONNECTOR_SCHEMA_POLICY.normalize(
            normalized.get("schema_version")
        )
        return normalized


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


def build_connector_event_payload(
    payload: dict[str, Any],
    *,
    schema_version: str | None = None,
) -> dict[str, Any]:
    """Build and validate a canonical connector event payload."""

    envelope = dict(payload)
    envelope["schema_version"] = (
        schema_version if schema_version is not None else envelope.get("schema_version")
    )
    event = parse_connector_event(envelope)
    return event.model_dump(mode="json")
