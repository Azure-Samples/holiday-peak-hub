"""Tests for ACP catalog mapper."""

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.schemas.product import CatalogProduct


def test_acp_mapper_builds_expected_feed_item():
    mapper = AcpCatalogMapper()
    product = CatalogProduct(
        sku="SKU-123",
        name="Trail Runner",
        description="Lightweight running shoe",
        brand="Contoso",
        price=79.5,
        image_url="https://img.example.com/trail.jpg",
    )

    acp = mapper.to_acp_product(product, availability="in_stock", currency="usd")

    assert acp["item_id"] == "SKU-123"
    assert acp["title"] == "Trail Runner"
    assert acp["brand"] == "Contoso"
    assert acp["price"] == "79.50 usd"
    assert acp["availability"] == "in_stock"
    assert acp["is_eligible_search"] is True
    assert acp["return_window"] == 30


def test_acp_mapper_uses_defaults_for_missing_fields():
    mapper = AcpCatalogMapper()
    product = CatalogProduct(sku="SKU-999", name="Mystery Box")

    acp = mapper.to_acp_product(product, availability="unknown")

    assert acp["description"] == ""
    assert str(acp["image_url"]).endswith("placeholder.png")
    assert acp["brand"] == ""
    assert acp["price"] == "0.00 usd"
