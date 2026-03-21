"""Unit tests for order status event handlers."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from ecommerce_order_status.event_handlers import build_event_handlers


def test_build_event_handlers_includes_order_events() -> None:
    handlers = build_event_handlers()
    assert "order-events" in handlers
    assert callable(handlers["order-events"])


@pytest.mark.asyncio
async def test_order_event_handler_validates_and_processes_event(monkeypatch) -> None:
    context = SimpleNamespace(
        shipment=SimpleNamespace(status="in_transit"),
        events=[{"kind": "scan"}],
    )
    logistics = SimpleNamespace(build_logistics_context=AsyncMock(return_value=context))
    resolver = SimpleNamespace(resolve_tracking_id=AsyncMock(return_value="T-order-1"))
    adapters = SimpleNamespace(logistics=logistics, resolver=resolver)

    monkeypatch.setattr(
        "ecommerce_order_status.event_handlers.build_order_status_adapters",
        lambda: adapters,
    )

    handlers = build_event_handlers()
    event = MagicMock()
    event.body_as_str.return_value = json.dumps(
        {
            "event_type": "OrderCreated",
            "data": {
                "id": "order-1",
                "user_id": "user-1",
                "items": [],
                "total": 10.0,
                "status": "pending",
            },
        }
    )

    await handlers["order-events"](MagicMock(), event)

    resolver.resolve_tracking_id.assert_awaited_once_with("order-1")
    logistics.build_logistics_context.assert_awaited_once_with("T-order-1")


@pytest.mark.asyncio
async def test_order_event_handler_skips_invalid_payload(monkeypatch) -> None:
    logistics = SimpleNamespace(build_logistics_context=AsyncMock())
    resolver = SimpleNamespace(resolve_tracking_id=AsyncMock())
    adapters = SimpleNamespace(logistics=logistics, resolver=resolver)

    monkeypatch.setattr(
        "ecommerce_order_status.event_handlers.build_order_status_adapters",
        lambda: adapters,
    )

    handlers = build_event_handlers()
    event = MagicMock()
    event.body_as_str.return_value = json.dumps(
        {
            "event_type": "OrderCreated",
            "data": {
                "user_id": "user-1",
            },
        }
    )

    await handlers["order-events"](MagicMock(), event)

    resolver.resolve_tracking_id.assert_not_called()
    logistics.build_logistics_context.assert_not_called()


@pytest.mark.asyncio
async def test_order_event_handler_skips_malformed_json(monkeypatch) -> None:
    logistics = SimpleNamespace(build_logistics_context=AsyncMock())
    resolver = SimpleNamespace(resolve_tracking_id=AsyncMock())
    adapters = SimpleNamespace(logistics=logistics, resolver=resolver)

    monkeypatch.setattr(
        "ecommerce_order_status.event_handlers.build_order_status_adapters",
        lambda: adapters,
    )

    handlers = build_event_handlers()
    event = MagicMock()
    event.body_as_str.return_value = "{invalid"

    await handlers["order-events"](MagicMock(), event)

    resolver.resolve_tracking_id.assert_not_called()
    logistics.build_logistics_context.assert_not_called()
