"""Unit tests for product normalization event handlers."""

from product_management_normalization_classification.event_handlers import (
    build_event_handlers,
)


def test_build_event_handlers_includes_product_events() -> None:
    handlers = build_event_handlers()
    assert "product-events" in handlers
