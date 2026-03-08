"""Unit tests for Salsify PIM data mappings."""

from __future__ import annotations

import pytest
from holiday_peak_lib.connectors.pim.salsify.mappings import map_asset, map_product
from holiday_peak_lib.integrations.contracts import AssetData, ProductData

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

SAMPLE_PRODUCT: dict = {
    "salsify:id": "sku-001",
    "Product Name": "Widget",
    "Product Description": "A fine widget",
    "Short Description": "Widget short",
    "Brand": "Acme",
    "salsify:updated_at": "2024-01-15T10:00:00Z",
    "salsify:digital_assets": [
        {"salsify:url": "https://cdn.salsify.com/images/widget.jpg"},
        {"salsify:url": "https://cdn.salsify.com/images/widget-2.jpg"},
    ],
    "salsify:relations": [
        {"salsify:id": "sku-002"},
    ],
    "Product Status": "active",
    "CustomAttr": "custom_value",
}

SAMPLE_ASSET: dict = {
    "salsify:id": "asset-1",
    "salsify:url": "https://cdn.salsify.com/images/asset-1.jpg",
    "salsify:content_type": "image/jpeg",
    "salsify:filename": "product.jpg",
    "salsify:size": 54321,
    "salsify:width": 800,
    "salsify:height": 600,
    "salsify:name": "Product Main Image",
    "salsify:tags": ["hero", "front"],
    "extra_meta": "value",
}


# ---------------------------------------------------------------------------
# TestMapProduct
# ---------------------------------------------------------------------------


class TestMapProduct:
    """Tests for salsify.mappings.map_product."""

    def test_full_mapping(self):
        product = map_product(SAMPLE_PRODUCT)
        assert isinstance(product, ProductData)
        assert product.sku == "sku-001"
        assert product.title == "Widget"
        assert product.description == "A fine widget"
        assert product.short_description == "Widget short"
        assert product.brand == "Acme"
        assert product.source_system == "salsify"
        assert product.status == "active"
        assert len(product.images) == 2
        assert product.images[0] == "https://cdn.salsify.com/images/widget.jpg"
        assert product.variants == ["sku-002"]
        assert product.last_modified is not None
        # Custom attributes should be in the attributes dict
        assert product.attributes.get("CustomAttr") == "custom_value"

    def test_minimal_product(self):
        raw = {"salsify:id": "sku-min"}
        product = map_product(raw)
        assert product.sku == "sku-min"
        assert product.title == ""
        assert product.description is None
        assert product.brand is None
        assert product.images == []
        assert product.variants == []

    def test_missing_id(self):
        product = map_product({})
        assert product.sku == ""

    def test_bad_date_ignored(self):
        raw = {"salsify:id": "x", "salsify:updated_at": "not-a-date"}
        product = map_product(raw)
        assert product.last_modified is None

    def test_no_digital_assets(self):
        raw = {"salsify:id": "x", "salsify:digital_assets": []}
        assert map_product(raw).images == []

    def test_digital_assets_without_url(self):
        raw = {"salsify:id": "x", "salsify:digital_assets": [{"salsify:name": "no-url"}]}
        assert map_product(raw).images == []

    def test_status_defaults_to_active(self):
        raw = {"salsify:id": "x"}
        assert map_product(raw).status == "active"

    def test_custom_status(self):
        raw = {"salsify:id": "x", "Product Status": "discontinued"}
        assert map_product(raw).status == "discontinued"


# ---------------------------------------------------------------------------
# TestMapAsset
# ---------------------------------------------------------------------------


class TestMapAsset:
    """Tests for salsify.mappings.map_asset."""

    def test_full_mapping(self):
        asset = map_asset(SAMPLE_ASSET)
        assert isinstance(asset, AssetData)
        assert asset.id == "asset-1"
        assert asset.url == "https://cdn.salsify.com/images/asset-1.jpg"
        assert asset.content_type == "image/jpeg"
        assert asset.filename == "product.jpg"
        assert asset.size_bytes == 54321
        assert asset.width == 800
        assert asset.height == 600
        assert asset.alt_text == "Product Main Image"
        assert asset.tags == ["hero", "front"]
        # Non-salsify keys go to metadata
        assert asset.metadata.get("extra_meta") == "value"

    def test_minimal_asset(self):
        raw = {"salsify:id": "min", "salsify:url": "https://example.com/img.png"}
        asset = map_asset(raw)
        assert asset.id == "min"
        assert asset.url == "https://example.com/img.png"
        assert asset.content_type == "application/octet-stream"

    def test_empty_asset(self):
        asset = map_asset({})
        assert asset.id == ""
        assert asset.url == ""

    def test_tags_default_empty(self):
        raw = {"salsify:id": "x", "salsify:url": "u"}
        assert map_asset(raw).tags == []

    def test_metadata_excludes_salsify_keys(self):
        raw = {
            "salsify:id": "x",
            "salsify:url": "u",
            "salsify:content_type": "image/png",
            "custom_key": "custom_val",
        }
        asset = map_asset(raw)
        assert "custom_key" in asset.metadata
        assert "salsify:id" not in asset.metadata
