"""Tests for Oracle SCM response → InventoryData mappings."""

from datetime import datetime

import pytest

from holiday_peak_lib.connectors.inventory_scm.oracle_scm.mappings import (
    _parse_datetime,
    map_on_hand_quantities,
    map_on_hand_quantity,
)


class TestParseDatetime:
    """Test the _parse_datetime helper."""

    def test_iso_with_microseconds_and_timezone(self):
        result = _parse_datetime("2024-01-15T12:00:00.000000+00:00")
        assert isinstance(result, datetime)
        assert result.year == 2024

    def test_iso_without_timezone(self):
        result = _parse_datetime("2024-06-01T08:30:00")
        assert isinstance(result, datetime)

    def test_date_only(self):
        result = _parse_datetime("2024-12-31")
        assert isinstance(result, datetime)

    def test_none_returns_none(self):
        assert _parse_datetime(None) is None

    def test_empty_string_returns_none(self):
        assert _parse_datetime("") is None

    def test_invalid_string_returns_none(self):
        assert _parse_datetime("not-a-date") is None


class TestMapOnHandQuantity:
    """Test mapping a single onHandQuantities record."""

    def test_basic_mapping(self):
        raw = {
            "ItemNumber": "ITEM-001",
            "OrganizationCode": "M1",
            "OrganizationId": 101,
            "Description": "Widget A",
            "PrimaryOnHandQuantity": 100.0,
            "ReservedQuantity": 20.0,
            "PrimaryUOMCode": "EA",
            "SubinventoryCode": "FGS",
            "LocatorName": "ROW1-BIN2",
            "LotNumber": "LOT-2024",
            "LotExpirationDate": "2025-12-31",
            "LastUpdateDate": "2024-01-15T09:00:00",
        }
        data = map_on_hand_quantity(raw)

        assert data.item_number == "ITEM-001"
        assert data.organization_code == "M1"
        assert data.organization_id == 101
        assert data.description == "Widget A"
        assert data.on_hand_quantity == 100.0
        assert data.reserved_quantity == 20.0
        assert data.unit_of_measure == "EA"
        assert data.subinventory_code == "FGS"
        assert data.locator == "ROW1-BIN2"
        assert data.lot_number == "LOT-2024"
        assert isinstance(data.expiration_date, datetime)
        assert isinstance(data.last_updated, datetime)

    def test_effective_available_uses_on_hand_minus_reserved(self):
        raw = {
            "ItemNumber": "ITEM-002",
            "OrganizationCode": "M2",
            "PrimaryOnHandQuantity": 50.0,
            "ReservedQuantity": 10.0,
        }
        data = map_on_hand_quantity(raw)
        assert data.effective_available == 40.0

    def test_effective_available_uses_available_quantity_when_set(self):
        raw = {
            "ItemNumber": "ITEM-003",
            "OrganizationCode": "M3",
            "PrimaryOnHandQuantity": 50.0,
            "ReservedQuantity": 10.0,
            "AvailableQuantity": 45.0,
        }
        data = map_on_hand_quantity(raw)
        # available_quantity not in the known keys → goes into attributes
        # effective_available falls back to on_hand - reserved since available_quantity is None
        assert data.effective_available == 40.0
        assert "AvailableQuantity" in data.attributes

    def test_effective_available_never_negative(self):
        raw = {
            "ItemNumber": "ITEM-004",
            "OrganizationCode": "M4",
            "PrimaryOnHandQuantity": 5.0,
            "ReservedQuantity": 20.0,
        }
        data = map_on_hand_quantity(raw)
        assert data.effective_available == 0.0

    def test_missing_optional_fields_default_to_none(self):
        raw = {"ItemNumber": "ITEM-005", "OrganizationCode": "M5"}
        data = map_on_hand_quantity(raw)
        assert data.description is None
        assert data.lot_number is None
        assert data.unit_of_measure is None

    def test_unknown_keys_go_into_attributes(self):
        raw = {
            "ItemNumber": "ITEM-006",
            "OrganizationCode": "M6",
            "CustomField": "custom_value",
        }
        data = map_on_hand_quantity(raw)
        assert data.attributes.get("CustomField") == "custom_value"

    def test_zero_quantities(self):
        raw = {
            "ItemNumber": "ITEM-007",
            "OrganizationCode": "M7",
            "PrimaryOnHandQuantity": 0,
            "ReservedQuantity": 0,
        }
        data = map_on_hand_quantity(raw)
        assert data.on_hand_quantity == 0.0
        assert data.reserved_quantity == 0.0

    def test_null_quantities_default_to_zero(self):
        raw = {
            "ItemNumber": "ITEM-008",
            "OrganizationCode": "M8",
            "PrimaryOnHandQuantity": None,
            "ReservedQuantity": None,
        }
        data = map_on_hand_quantity(raw)
        assert data.on_hand_quantity == 0.0
        assert data.reserved_quantity == 0.0


class TestMapOnHandQuantities:
    """Test mapping a list of onHandQuantities records."""

    def test_empty_list(self):
        assert map_on_hand_quantities([]) == []

    def test_multiple_records(self):
        records = [
            {"ItemNumber": "A", "OrganizationCode": "M1", "PrimaryOnHandQuantity": 10},
            {"ItemNumber": "B", "OrganizationCode": "M2", "PrimaryOnHandQuantity": 20},
        ]
        result = map_on_hand_quantities(records)
        assert len(result) == 2
        assert result[0].item_number == "A"
        assert result[1].item_number == "B"
        assert result[1].on_hand_quantity == 20.0
