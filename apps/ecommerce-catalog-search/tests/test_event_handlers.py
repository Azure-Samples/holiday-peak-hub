"""Unit tests for catalog search event handlers."""

from ecommerce_catalog_search.event_handlers import build_event_handlers


def test_build_event_handlers_includes_product_events() -> None:
    handlers = build_event_handlers()
    assert "product-events" in handlers
    assert callable(handlers["product-events"])
