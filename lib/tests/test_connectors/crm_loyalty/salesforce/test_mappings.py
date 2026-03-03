"""Unit tests for Salesforce response → canonical model mappings."""

from __future__ import annotations

import pytest
from holiday_peak_lib.connectors.crm_loyalty.salesforce.mappings import (
    map_campaign_to_segment,
    map_contact_to_customer,
    map_order_to_order_data,
)


class TestMapContactToCustomer:
    def _full_contact(self) -> dict:
        return {
            "Id": "003xx000004TmiKAAS",
            "Email": "jane@example.com",
            "FirstName": "Jane",
            "LastName": "Doe",
            "Phone": "+1-555-0100",
            "loyalty_tier__c": "Gold",
            "Segments__c": "VIP; Newsletter",
            "HasOptedOutOfEmail": False,
            "HasOptedOutOfFax": True,
            "LastActivityDate": "2024-11-01T10:00:00Z",
            "npo02__TotalOppAmount__c": 1250.50,
        }

    def test_maps_basic_fields(self):
        customer = map_contact_to_customer(self._full_contact())
        assert customer.customer_id == "003xx000004TmiKAAS"
        assert customer.email == "jane@example.com"
        assert customer.first_name == "Jane"
        assert customer.last_name == "Doe"
        assert customer.phone == "+1-555-0100"

    def test_maps_loyalty_tier(self):
        customer = map_contact_to_customer(self._full_contact())
        assert customer.loyalty_tier == "Gold"

    def test_maps_segments_from_semicolon_string(self):
        customer = map_contact_to_customer(self._full_contact())
        assert "VIP" in customer.segments
        assert "Newsletter" in customer.segments

    def test_maps_lifetime_value(self):
        customer = map_contact_to_customer(self._full_contact())
        assert customer.lifetime_value == pytest.approx(1250.50)

    def test_maps_consent_flags(self):
        customer = map_contact_to_customer(self._full_contact())
        assert customer.consent["email_opt_in"] is True
        assert customer.consent["fax_opt_in"] is False

    def test_maps_last_activity_date(self):
        customer = map_contact_to_customer(self._full_contact())
        assert customer.last_activity is not None
        assert customer.last_activity.year == 2024

    def test_handles_missing_optional_fields(self):
        minimal = {"Id": "003MIN"}
        customer = map_contact_to_customer(minimal)
        assert customer.customer_id == "003MIN"
        assert customer.email is None
        assert customer.segments == []
        assert customer.lifetime_value is None
        assert customer.last_activity is None

    def test_handles_empty_segments_string(self):
        record = {"Id": "003xx", "Segments__c": ""}
        customer = map_contact_to_customer(record)
        assert customer.segments == []

    def test_handles_none_segments(self):
        record = {"Id": "003xx", "Segments__c": None}
        customer = map_contact_to_customer(record)
        assert customer.segments == []

    def test_handles_string_lifetime_value(self):
        record = {"Id": "003xx", "npo02__TotalOppAmount__c": "500.0"}
        customer = map_contact_to_customer(record)
        assert customer.lifetime_value == pytest.approx(500.0)

    def test_handles_invalid_lifetime_value(self):
        record = {"Id": "003xx", "npo02__TotalOppAmount__c": "N/A"}
        customer = map_contact_to_customer(record)
        assert customer.lifetime_value is None


class TestMapOrderToOrderData:
    def _full_order(self) -> dict:
        return {
            "Id": "801xx000003GXAiAAO",
            "AccountId": "001xx000003GXAiAAO",
            "Status": "Activated",
            "TotalAmount": 149.99,
            "CurrencyIsoCode": "USD",
            "CreatedDate": "2024-11-15T09:30:00Z",
            "LastModifiedDate": "2024-11-16T08:00:00Z",
            "ShipToContactId": "003xx000004TmiKAAS",
            "OrderItems": {
                "records": [
                    {
                        "Product2Id": "01txx0000008OJIAA2",
                        "ProductCode": "SKU-001",
                        "Description": "Widget A",
                        "Quantity": 2,
                        "UnitPrice": 49.99,
                        "TotalPrice": 99.98,
                    }
                ]
            },
        }

    def test_maps_order_id_and_status(self):
        order = map_order_to_order_data(self._full_order())
        assert order.order_id == "801xx000003GXAiAAO"
        assert order.status == "Activated"

    def test_maps_customer_id(self):
        order = map_order_to_order_data(self._full_order())
        assert order.customer_id == "001xx000003GXAiAAO"

    def test_maps_total_and_currency(self):
        order = map_order_to_order_data(self._full_order())
        assert order.total == pytest.approx(149.99)
        assert order.currency == "USD"

    def test_maps_order_items(self):
        order = map_order_to_order_data(self._full_order())
        assert len(order.items) == 1
        item = order.items[0]
        assert item["sku"] == "SKU-001"
        assert item["quantity"] == 2
        assert item["unit_price"] == pytest.approx(49.99)

    def test_maps_timestamps(self):
        order = map_order_to_order_data(self._full_order())
        assert order.created_at is not None
        assert order.created_at.year == 2024
        assert order.updated_at is not None

    def test_maps_shipping_address_from_contact(self):
        order = map_order_to_order_data(self._full_order())
        assert order.shipping_address == {"contact_id": "003xx000004TmiKAAS"}

    def test_handles_missing_order_items(self):
        minimal = {
            "Id": "801MIN",
            "Status": "Draft",
            "TotalAmount": 0.0,
        }
        order = map_order_to_order_data(minimal)
        assert order.items == []
        assert order.shipping_address is None

    def test_handles_none_total_amount(self):
        record = {"Id": "801NULL", "Status": "Draft", "TotalAmount": None}
        order = map_order_to_order_data(record)
        assert order.total == pytest.approx(0.0)

    def test_default_currency_usd(self):
        record = {"Id": "801CUR", "Status": "Draft", "TotalAmount": 10.0}
        order = map_order_to_order_data(record)
        assert order.currency == "USD"


class TestMapCampaignToSegment:
    def _full_campaign(self) -> dict:
        return {
            "Id": "701xx000004TmiKAAS",
            "Name": "Holiday VIP",
            "Description": "Top spenders Q4",
            "Type": "Email",
            "Status": "Active",
            "StartDate": "2024-11-01",
            "EndDate": "2024-12-31",
            "NumberOfContacts": 450,
        }

    def test_maps_segment_id_and_name(self):
        seg = map_campaign_to_segment(self._full_campaign())
        assert seg.segment_id == "701xx000004TmiKAAS"
        assert seg.name == "Holiday VIP"

    def test_maps_description(self):
        seg = map_campaign_to_segment(self._full_campaign())
        assert seg.description == "Top spenders Q4"

    def test_maps_member_count(self):
        seg = map_campaign_to_segment(self._full_campaign())
        assert seg.member_count == 450

    def test_maps_criteria(self):
        seg = map_campaign_to_segment(self._full_campaign())
        assert seg.criteria["type"] == "Email"
        assert seg.criteria["status"] == "Active"
        assert seg.criteria["start_date"] == "2024-11-01"
        assert seg.criteria["end_date"] == "2024-12-31"

    def test_handles_missing_optional_fields(self):
        minimal = {"Id": "701MIN", "Name": "Min"}
        seg = map_campaign_to_segment(minimal)
        assert seg.description is None
        assert seg.member_count is None
        assert seg.criteria["type"] is None
