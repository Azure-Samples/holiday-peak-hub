"""Unit tests for logistics returns support event handlers."""

from logistics_returns_support.event_handlers import build_event_handlers


def test_build_event_handlers_includes_order_events() -> None:
    handlers = build_event_handlers()
    assert "order-events" in handlers
    assert "return-events" in handlers
