"""Tests for ProtocolMapper implementations (ACP and UCP)."""

from __future__ import annotations

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.adapters.ucp_mapper import UcpProtocolMapper
from holiday_peak_lib.schemas.acp import AcpPartnerProfile
from holiday_peak_lib.schemas.truth import ProductStyle, TruthAttribute


def _make_style(**kwargs) -> ProductStyle:
    defaults = {
        "style_id": "STYLE-TEST",
        "name": "Test Product",
        "brand": "TestBrand",
        "category": "footwear",
        "description": "A test product",
        "image_url": "https://example.com/img/test.jpg",
        "completeness_score": 0.85,
    }
    defaults.update(kwargs)
    return ProductStyle(**defaults)


def _make_attrs(**overrides) -> list[TruthAttribute]:
    base = {
        "price": 49.99,
        "currency": "usd",
        "availability": "in_stock",
    }
    base.update(overrides)
    return [
        TruthAttribute(
            attribute_id=f"attr-{i}",
            style_id="STYLE-TEST",
            field_name=k,
            value=v,
            confidence=1.0,
            approved_by="reviewer",
        )
        for i, (k, v) in enumerate(base.items())
    ]


# ---------------------------------------------------------------------------
# UcpProtocolMapper
# ---------------------------------------------------------------------------


def test_ucp_mapper_basic():
    mapper = UcpProtocolMapper()
    style = _make_style()
    attrs = _make_attrs()
    result = mapper.map(style, attrs, {})

    assert result["product_id"] == "STYLE-TEST"
    assert result["title"] == "Test Product"
    assert result["brand"] == "TestBrand"
    assert result["price_amount"] == 49.99
    assert result["currency"] == "usd"
    assert result["availability"] == "in_stock"
    assert result["completeness_score"] == 0.85
    assert result["protocol"] == "ucp"


def test_ucp_mapper_validate_output_passes():
    mapper = UcpProtocolMapper()
    output = {
        "product_id": "X",
        "title": "Y",
        "brand": "B",
        "price_amount": 1.0,
        "currency": "usd",
    }
    assert mapper.validate_output(output, "1.0") is True


def test_ucp_mapper_validate_output_fails_missing_field():
    mapper = UcpProtocolMapper()
    output = {"product_id": "X", "title": "Y", "brand": "B"}
    assert mapper.validate_output(output, "1.0") is False


def test_ucp_mapper_compliance_counts():
    mapper = UcpProtocolMapper()
    style = _make_style()
    attrs = _make_attrs()
    result = mapper.map(style, attrs, {})
    assert result["compliance"]["attribute_count"] == 3
    assert result["compliance"]["approved_attributes"] == 3


def test_ucp_mapper_field_overrides():
    mapper = UcpProtocolMapper()
    style = _make_style()
    attrs = _make_attrs(color="red")
    mapping = {"field_overrides": {"main_color": "color"}}
    result = mapper.map(style, attrs, mapping)
    assert result.get("main_color") == "red"


def test_ucp_mapper_no_attributes():
    mapper = UcpProtocolMapper()
    style = _make_style()
    result = mapper.map(style, [], {})
    assert result["price_amount"] == 0.0
    assert result["currency"] == "usd"


# ---------------------------------------------------------------------------
# AcpCatalogMapper (ProtocolMapper interface)
# ---------------------------------------------------------------------------


def test_acp_mapper_protocol_interface():
    mapper = AcpCatalogMapper()
    style = _make_style()
    attrs = _make_attrs()
    result = mapper.map(style, attrs, {})

    assert result["item_id"] == "STYLE-TEST"
    assert result["title"] == "Test Product"
    assert "49.99" in result["price"]
    assert result["availability"] == "in_stock"


def test_acp_mapper_validate_output_passes():
    mapper = AcpCatalogMapper()
    output = {
        "item_id": "X",
        "title": "Y",
        "description": "D",
        "url": "https://x.com",
        "image_url": "https://x.com/img.jpg",
        "brand": "B",
        "price": "1.00 usd",
    }
    assert mapper.validate_output(output, "1.0") is True


def test_acp_mapper_validate_output_fails():
    mapper = AcpCatalogMapper()
    output = {"item_id": "X", "title": "Y"}
    assert mapper.validate_output(output, "1.0") is False


def test_acp_mapper_partner_policy_filtering():
    mapper = AcpCatalogMapper()
    from holiday_peak_lib.schemas.product import CatalogProduct

    product = CatalogProduct(
        sku="SKU-X",
        name="Widget",
        brand="ACME",
        price=9.99,
    )
    partner = AcpPartnerProfile(
        partner_id="partner-1",
        restricted_fields=["seller_tos", "return_policy"],
    )
    result = mapper.to_acp_product(product, availability="in_stock", partner_profile=partner)
    assert "seller_tos" not in result
    assert "return_policy" not in result
    assert result["item_id"] == "SKU-X"


def test_acp_mapper_legacy_interface_still_works():
    """Ensure the legacy to_acp_product helper is backward-compatible."""
    from holiday_peak_lib.schemas.product import CatalogProduct

    mapper = AcpCatalogMapper()
    product = CatalogProduct(sku="SKU-LEGACY", name="Legacy Item", price=5.0, brand="OldBrand")
    result = mapper.to_acp_product(product, availability="out_of_stock", currency="eur")

    assert result["item_id"] == "SKU-LEGACY"
    assert result["price"] == "5.00 eur"
    assert result["availability"] == "out_of_stock"
    assert result["is_eligible_search"] is True
