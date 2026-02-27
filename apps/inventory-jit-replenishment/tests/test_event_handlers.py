"""Unit tests for inventory replenishment event handlers."""

from inventory_jit_replenishment.event_handlers import build_event_handlers


def test_build_event_handlers_includes_inventory_events() -> None:
    handlers = build_event_handlers()
    assert "inventory-events" in handlers
