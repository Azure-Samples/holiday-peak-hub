"""Unit tests for CRM profile aggregation event handlers."""

from crm_profile_aggregation.event_handlers import build_event_handlers


def test_build_event_handlers_includes_user_and_order_events() -> None:
    handlers = build_event_handlers()
    assert "user-events" in handlers
    assert "order-events" in handlers
