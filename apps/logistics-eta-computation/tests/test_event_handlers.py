"""Unit tests for logistics ETA event handlers."""

from logistics_eta_computation.event_handlers import build_event_handlers


def test_build_event_handlers_includes_order_events() -> None:
    handlers = build_event_handlers()
    assert "order-events" in handlers
    assert "shipment-events" in handlers
