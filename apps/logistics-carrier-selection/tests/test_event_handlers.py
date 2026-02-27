"""Unit tests for logistics carrier selection event handlers."""

from logistics_carrier_selection.event_handlers import build_event_handlers


def test_build_event_handlers_includes_order_events() -> None:
    handlers = build_event_handlers()
    assert "order-events" in handlers
