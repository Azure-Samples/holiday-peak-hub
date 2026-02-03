"""Unit tests for order status event handlers."""

from ecommerce_order_status.event_handlers import build_event_handlers


def test_build_event_handlers_includes_order_events() -> None:
    handlers = build_event_handlers()
    assert "order-events" in handlers
    assert callable(handlers["order-events"])
