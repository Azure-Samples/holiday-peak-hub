"""Unit tests for CRM campaign intelligence event handlers."""

from crm_campaign_intelligence.event_handlers import build_event_handlers


def test_build_event_handlers_includes_expected_events() -> None:
    handlers = build_event_handlers()
    assert "user-events" in handlers
    assert "order-events" in handlers
    assert "payment-events" in handlers
