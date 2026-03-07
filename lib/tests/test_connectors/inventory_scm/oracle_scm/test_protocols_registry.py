"""Tests for common connector protocols and ConnectorRegistry."""

import pytest

from holiday_peak_lib.connectors.common.protocols import (
    AssetData,
    CustomerData,
    InventoryData,
    OrderData,
    ProductData,
    SegmentData,
)
from holiday_peak_lib.connectors.registry import ConnectorRegistry, default_registry


class TestInventoryData:
    def test_basic_construction(self):
        data = InventoryData(item_number="I1", organization_code="M1", on_hand_quantity=100)
        assert data.on_hand_quantity == 100
        assert data.reserved_quantity == 0

    def test_effective_available_with_explicit_available(self):
        data = InventoryData(
            item_number="I1",
            organization_code="M1",
            on_hand_quantity=100,
            reserved_quantity=20,
            available_quantity=85,
        )
        assert data.effective_available == 85

    def test_effective_available_computed_from_on_hand_minus_reserved(self):
        data = InventoryData(
            item_number="I1",
            organization_code="M1",
            on_hand_quantity=100,
            reserved_quantity=20,
        )
        assert data.effective_available == 80

    def test_effective_available_never_negative(self):
        data = InventoryData(
            item_number="I1",
            organization_code="M1",
            on_hand_quantity=10,
            reserved_quantity=50,
        )
        assert data.effective_available == 0

    def test_attributes_default_empty(self):
        data = InventoryData(item_number="I1", organization_code="M1")
        assert data.attributes == {}


class TestOtherProtocols:
    def test_product_data(self):
        p = ProductData(product_id="P1", name="Widget")
        assert p.name == "Widget"

    def test_asset_data(self):
        a = AssetData(asset_id="A1", name="hero.jpg", url="https://cdn.example.com/hero.jpg")
        assert a.url == "https://cdn.example.com/hero.jpg"

    def test_customer_data(self):
        c = CustomerData(customer_id="C1", email="a@b.com")
        assert c.email == "a@b.com"

    def test_order_data(self):
        o = OrderData(order_id="O1", status="open")
        assert o.status == "open"

    def test_segment_data(self):
        s = SegmentData(segment_id="S1", name="High Value")
        assert s.name == "High Value"


class TestConnectorRegistry:
    def test_register_and_get(self):
        registry = ConnectorRegistry()

        class DummyConnector:
            pass

        registry.register("pim", "dummy", DummyConnector)
        assert registry.get("pim", "dummy") is DummyConnector

    def test_get_unknown_returns_none(self):
        registry = ConnectorRegistry()
        assert registry.get("pim", "nonexistent") is None

    def test_get_unknown_domain_returns_none(self):
        registry = ConnectorRegistry()
        assert registry.get("nonexistent_domain", "vendor") is None

    def test_list_vendors(self):
        registry = ConnectorRegistry()
        registry.register("crm", "salesforce", object)
        registry.register("crm", "dynamics", object)
        vendors = registry.list_vendors("crm")
        assert set(vendors) == {"salesforce", "dynamics"}

    def test_list_vendors_unknown_domain(self):
        registry = ConnectorRegistry()
        assert registry.list_vendors("unknown") == []

    def test_default_registry_exists(self):
        assert isinstance(default_registry, ConnectorRegistry)
