"""Unit tests for product ACP transformation event handlers."""

from product_management_acp_transformation.event_handlers import build_event_handlers


def test_build_event_handlers_includes_product_events() -> None:
    handlers = build_event_handlers()
    assert "product-events" in handlers
