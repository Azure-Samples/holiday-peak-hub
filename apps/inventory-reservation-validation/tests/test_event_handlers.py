"""Unit tests for reservation validation event handlers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from inventory_reservation_validation.adapters import ReservationValidationAdapters
from inventory_reservation_validation.event_handlers import build_event_handlers


class FakeEvent:
    """Simple Event Hub event stub."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def body_as_str(self) -> str:
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_handle_order_event_validates_reservations():
    """Order events should validate reservation quantities."""
    logger = Mock()
    inventory_ctx = InventoryContext(
        sku="SKU-5",
        item=InventoryItem(sku="SKU-5", available=8, reserved=2, warehouse_id="W1"),
        warehouses=[],
    )
    mock_inventory = AsyncMock()
    mock_inventory.build_inventory_context = AsyncMock(return_value=inventory_ctx)
    mock_validator = AsyncMock()
    mock_validator.validate = AsyncMock(return_value={"sku": "SKU-5", "approved": True})
    adapters = ReservationValidationAdapters(inventory=mock_inventory, validator=mock_validator)
    payload = {
        "event_type": "order.placed",
        "data": {"order_id": "ORD-9", "items": [{"sku": "SKU-5", "quantity": 3}]},
    }

    with (
        patch(
            "inventory_reservation_validation.event_handlers.configure_logging",
            return_value=logger,
        ),
        patch(
            "inventory_reservation_validation.event_handlers.build_reservation_validation_adapters",
            return_value=adapters,
        ),
    ):
        handlers = build_event_handlers()
        await handlers["order-events"](None, FakeEvent(payload))

    mock_inventory.build_inventory_context.assert_called_once_with("SKU-5")
    mock_validator.validate.assert_called_once()
    assert logger.info.called
