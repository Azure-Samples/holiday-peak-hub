"""Unit tests for SAP S/4HANA OData → domain model mappings."""

from __future__ import annotations

from datetime import timezone

import pytest
from holiday_peak_lib.connectors.inventory_scm.sap_s4hana.mappings import (
    _parse_datetime,
    map_material_stock_to_inventory,
    map_product_to_product_data,
    map_warehouse_bin_stock_to_inventory,
)
from holiday_peak_lib.integrations.contracts import InventoryData, ProductData

# ---------------------------------------------------------------------------
# _parse_datetime
# ---------------------------------------------------------------------------


class TestParseDatetime:
    def test_iso_string(self):
        dt = _parse_datetime("2024-12-01T10:00:00Z")
        assert dt is not None
        assert dt.year == 2024
        assert dt.tzinfo is not None

    def test_odata_v2_date(self):
        # /Date(0)/ = epoch
        dt = _parse_datetime("/Date(0)/")
        assert dt is not None
        assert dt.year == 1970

    def test_odata_v2_date_with_offset(self):
        dt = _parse_datetime("/Date(1609459200000+0000)/")
        assert dt is not None
        assert dt.year == 2021

    def test_none_returns_none(self):
        assert _parse_datetime(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_datetime("") is None

    def test_invalid_string_returns_none(self):
        assert _parse_datetime("not-a-date") is None


# ---------------------------------------------------------------------------
# map_material_stock_to_inventory
# ---------------------------------------------------------------------------


class TestMapMaterialStock:
    def _record(self, **overrides):
        base = {
            "Material": "MAT-001",
            "Plant": "1000",
            "StorageLocation": "0001",
            "MatlStkInAcctMod": "500.000",
            "QtyInTransit": "10.000",
            "QtyInQualityInspection": "5.000",
            "ReorderThresholdQuantity": "100",
            "LastChangeDateTime": "2024-06-01T08:00:00Z",
        }
        base.update(overrides)
        return base

    def test_basic_mapping(self):
        inv = map_material_stock_to_inventory(self._record())
        assert isinstance(inv, InventoryData)
        assert inv.sku == "MAT-001"
        assert inv.location_id == "1000"
        assert inv.location_name == "1000/0001"
        assert inv.available_qty == 500
        assert inv.reserved_qty == 10
        assert inv.on_order_qty == 5
        assert inv.reorder_point == 100
        assert inv.last_updated is not None

    def test_product_field_as_sku(self):
        record = self._record()
        record.pop("Material")
        record["Product"] = "PROD-XYZ"
        inv = map_material_stock_to_inventory(record)
        assert inv.sku == "PROD-XYZ"

    def test_missing_optional_fields(self):
        inv = map_material_stock_to_inventory({"Material": "X", "Plant": "Y"})
        assert inv.available_qty == 0
        assert inv.reserved_qty == 0
        assert inv.reorder_point is None
        assert inv.last_updated is None

    def test_location_name_no_storage_loc(self):
        inv = map_material_stock_to_inventory({"Material": "X", "Plant": "P1"})
        assert inv.location_name == "P1"

    def test_zero_quantities(self):
        inv = map_material_stock_to_inventory(
            {"Material": "X", "Plant": "P1", "MatlStkInAcctMod": "0"}
        )
        assert inv.available_qty == 0


# ---------------------------------------------------------------------------
# map_warehouse_bin_stock_to_inventory
# ---------------------------------------------------------------------------


class TestMapWarehouseBinStock:
    def _record(self, **overrides):
        base = {
            "Product": "PROD-001",
            "Warehouse": "WH01",
            "StorageBin": "A-01-01",
            "StockQty": "200.000",
            "ReservedQty": "20.000",
            "LastChangeDate": "2024-07-01T00:00:00Z",
        }
        base.update(overrides)
        return base

    def test_basic_mapping(self):
        inv = map_warehouse_bin_stock_to_inventory(self._record())
        assert isinstance(inv, InventoryData)
        assert inv.sku == "PROD-001"
        assert inv.location_id == "WH01"
        assert inv.location_name == "WH01/A-01-01"
        assert inv.available_qty == 200
        assert inv.reserved_qty == 20

    def test_material_fallback(self):
        record = self._record()
        record.pop("Product")
        record["Material"] = "MAT-002"
        inv = map_warehouse_bin_stock_to_inventory(record)
        assert inv.sku == "MAT-002"


# ---------------------------------------------------------------------------
# map_product_to_product_data
# ---------------------------------------------------------------------------


class TestMapProductData:
    def _record(self, **overrides):
        base = {
            "Product": "SKU-001",
            "Brand": "CoolBrand",
            "ProductGroup": "ELECTRONICS",
            "CrossPlantStatus": "00",
            "LastChangeDate": "2024-08-01T00:00:00Z",
            "to_Description": [
                {"Language": "EN", "ProductDescription": "Cool Widget"},
                {"Language": "DE", "ProductDescription": "Cooles Widget"},
            ],
        }
        base.update(overrides)
        return base

    def test_basic_mapping(self):
        prod = map_product_to_product_data(self._record())
        assert isinstance(prod, ProductData)
        assert prod.sku == "SKU-001"
        assert prod.title == "Cool Widget"
        assert prod.brand == "CoolBrand"
        assert prod.category_path == ["ELECTRONICS"]
        assert prod.status == "active"
        assert prod.source_system == "sap_s4hana"

    def test_inactive_status(self):
        prod = map_product_to_product_data(self._record(CrossPlantStatus="02"))
        assert prod.status == "inactive"

    def test_title_falls_back_to_first_description(self):
        record = self._record()
        record["to_Description"] = [{"Language": "DE", "ProductDescription": "Cooles Widget"}]
        prod = map_product_to_product_data(record)
        assert prod.title == "Cooles Widget"

    def test_title_falls_back_to_sku(self):
        record = self._record()
        record["to_Description"] = []
        prod = map_product_to_product_data(record)
        assert prod.title == "SKU-001"

    def test_string_description(self):
        record = self._record()
        record["to_Description"] = "Plain text desc"
        prod = map_product_to_product_data(record)
        assert prod.title == "Plain text desc"

    def test_material_field_as_sku(self):
        record = self._record()
        record.pop("Product")
        record["Material"] = "MAT-LEGACY"
        prod = map_product_to_product_data(record)
        assert prod.sku == "MAT-LEGACY"

    def test_extra_fields_in_attributes(self):
        record = self._record(GrossWeight="1.5", NetWeight="1.2")
        prod = map_product_to_product_data(record)
        assert "GrossWeight" in prod.attributes
        assert "NetWeight" in prod.attributes
