"""Unit tests for inventory health check event handlers."""

from inventory_health_check.event_handlers import build_event_handlers


def test_build_event_handlers_includes_order_and_inventory_events() -> None:
    handlers = build_event_handlers()
    assert "order-events" in handlers
    assert "inventory-events" in handlers
