"""Event models for cross-service integrations."""

from holiday_peak_lib.events.connector_events import (
    ConnectorEvent,
    ConnectorEventUnion,
    CustomerUpdated,
    InventoryUpdated,
    OrderStatusChanged,
    PriceUpdated,
    ProductChanged,
    parse_connector_event,
)

__all__ = [
    "ConnectorEvent",
    "ConnectorEventUnion",
    "ProductChanged",
    "InventoryUpdated",
    "CustomerUpdated",
    "OrderStatusChanged",
    "PriceUpdated",
    "parse_connector_event",
]
