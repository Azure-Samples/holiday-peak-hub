"""Unit tests for inventory alerts event handlers."""

from inventory_alerts_triggers.event_handlers import build_event_handlers


def test_build_event_handlers_includes_inventory_events() -> None:
    handlers = build_event_handlers()
    assert "inventory-events" in handlers
