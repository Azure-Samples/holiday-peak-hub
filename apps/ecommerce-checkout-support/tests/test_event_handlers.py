"""Unit tests for checkout support event handlers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from ecommerce_checkout_support.adapters import CheckoutAdapters
from ecommerce_checkout_support.event_handlers import build_event_handlers
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem
from holiday_peak_lib.schemas.pricing import PriceContext, PriceEntry


class FakeEvent:
    """Simple Event Hub event stub."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def body_as_str(self) -> str:
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_handle_order_event_processes_validation():
    """Order events should validate checkout readiness."""
    logger = Mock()
    pricing_ctx = PriceContext(
        sku="SKU-1",
        active=PriceEntry(sku="SKU-1", amount=19.99, currency="USD", promotional=False),
        offers=[],
    )
    inventory_ctx = InventoryContext(
        sku="SKU-1",
        item=InventoryItem(sku="SKU-1", available=10, reserved=0, warehouse_id="W1"),
        warehouses=[],
    )
    mock_pricing = AsyncMock()
    mock_pricing.build_price_context = AsyncMock(return_value=pricing_ctx)
    mock_inventory = AsyncMock()
    mock_inventory.build_inventory_context = AsyncMock(return_value=inventory_ctx)
    mock_validator = AsyncMock()
    mock_validator.validate = AsyncMock(return_value={"status": "ready", "issues": []})
    adapters = CheckoutAdapters(
        pricing=mock_pricing, inventory=mock_inventory, validator=mock_validator
    )
    payload = {
        "event_type": "order.placed",
        "data": {"order_id": "ORD-1", "items": [{"sku": "SKU-1", "quantity": 2}]},
    }

    with (
        patch(
            "ecommerce_checkout_support.event_handlers.configure_logging",
            return_value=logger,
        ),
        patch(
            "ecommerce_checkout_support.event_handlers.build_checkout_adapters",
            return_value=adapters,
        ),
    ):
        handlers = build_event_handlers()
        await handlers["order-events"](None, FakeEvent(payload))

    mock_pricing.build_price_context.assert_called_once_with("SKU-1")
    mock_inventory.build_inventory_context.assert_called_once_with("SKU-1")
    mock_validator.validate.assert_called_once()
    assert logger.info.called


@pytest.mark.asyncio
async def test_handle_inventory_event_fetches_context():
    """Inventory events should fetch context for monitoring."""
    logger = Mock()
    inventory_ctx = InventoryContext(
        sku="SKU-9",
        item=InventoryItem(sku="SKU-9", available=3, reserved=1, warehouse_id="W2"),
        warehouses=[],
    )
    mock_pricing = AsyncMock()
    mock_inventory = AsyncMock()
    mock_inventory.build_inventory_context = AsyncMock(return_value=inventory_ctx)
    mock_validator = AsyncMock()
    adapters = CheckoutAdapters(
        pricing=mock_pricing, inventory=mock_inventory, validator=mock_validator
    )
    payload = {"event_type": "inventory.low_stock", "data": {"sku": "SKU-9"}}

    with (
        patch(
            "ecommerce_checkout_support.event_handlers.configure_logging",
            return_value=logger,
        ),
        patch(
            "ecommerce_checkout_support.event_handlers.build_checkout_adapters",
            return_value=adapters,
        ),
    ):
        handlers = build_event_handlers()
        await handlers["inventory-events"](None, FakeEvent(payload))

    mock_inventory.build_inventory_context.assert_called_once_with("SKU-9")
    assert logger.info.called
