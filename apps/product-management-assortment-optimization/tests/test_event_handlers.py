"""Unit tests for product assortment optimization event handlers."""

from product_management_assortment_optimization.event_handlers import build_event_handlers


def test_build_event_handlers_includes_order_and_product_events() -> None:
    handlers = build_event_handlers()
    assert "order-events" in handlers
    assert "product-events" in handlers
