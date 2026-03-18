"""Unit tests for CRM support assistance event handlers."""

from crm_support_assistance.event_handlers import build_event_handlers


def test_build_event_handlers_includes_order_events() -> None:
    handlers = build_event_handlers()
    assert "order-events" in handlers
    assert "return-events" in handlers
