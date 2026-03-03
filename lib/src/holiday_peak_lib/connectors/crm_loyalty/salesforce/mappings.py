"""Mappings from Salesforce API responses to canonical domain models.

Salesforce objects mapped:
- Contact / Account  → CustomerData
- Order              → OrderData
- CampaignMember     → SegmentData (via Campaign)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from holiday_peak_lib.integrations.contracts import CustomerData, OrderData, SegmentData


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO 8601 datetime string returned by Salesforce."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def map_contact_to_customer(record: dict[str, Any]) -> CustomerData:
    """Map a Salesforce Contact (optionally with Account) to ``CustomerData``.

    Salesforce fields consumed:
        Id, Email, FirstName, LastName, Phone,
        Account.Name, Account.Industry,
        npo02__TotalOppAmount__c (lifetime value placeholder),
        loyalty_tier__c, Segments__c.

    >>> data = map_contact_to_customer({
    ...     "Id": "003xx000004TmiKAAS",
    ...     "Email": "jane@example.com",
    ...     "FirstName": "Jane",
    ...     "LastName": "Doe",
    ...     "Phone": "+1-555-0100",
    ...     "loyalty_tier__c": "Gold",
    ... })
    >>> data.customer_id
    '003xx000004TmiKAAS'
    >>> data.email
    'jane@example.com'
    >>> data.loyalty_tier
    'Gold'
    """
    segments: list[str] = []
    raw_segments = record.get("Segments__c") or ""
    if raw_segments:
        segments = [s.strip() for s in raw_segments.split(";") if s.strip()]

    lifetime_value: float | None = None
    ltv_raw = record.get("npo02__TotalOppAmount__c") or record.get("Total_Revenue__c")
    if ltv_raw is not None:
        try:
            lifetime_value = float(ltv_raw)
        except (TypeError, ValueError):
            pass

    return CustomerData(
        customer_id=record["Id"],
        email=record.get("Email"),
        first_name=record.get("FirstName"),
        last_name=record.get("LastName"),
        phone=record.get("Phone"),
        segments=segments,
        loyalty_tier=record.get("loyalty_tier__c"),
        lifetime_value=lifetime_value,
        preferences=record.get("preferences__c") or {},
        consent={
            "email_opt_in": record.get("HasOptedOutOfEmail") is False,
            "fax_opt_in": record.get("HasOptedOutOfFax") is False,
        },
        last_activity=_parse_dt(record.get("LastActivityDate")),
    )


def map_order_to_order_data(record: dict[str, Any]) -> OrderData:
    """Map a Salesforce Order record to ``OrderData``.

    >>> od = map_order_to_order_data({
    ...     "Id": "801xx000003GXAiAAO",
    ...     "AccountId": "001xx000003GXAiAAO",
    ...     "Status": "Activated",
    ...     "TotalAmount": 149.99,
    ...     "CurrencyIsoCode": "USD",
    ... })
    >>> od.order_id
    '801xx000003GXAiAAO'
    >>> od.status
    'Activated'
    """
    items: list[dict] = []
    order_items = record.get("OrderItems") or {}
    for item in order_items.get("records", []):
        items.append(
            {
                "product_id": item.get("Product2Id"),
                "sku": item.get("ProductCode"),
                "name": item.get("Description"),
                "quantity": item.get("Quantity"),
                "unit_price": item.get("UnitPrice"),
                "total_price": item.get("TotalPrice"),
            }
        )

    shipping: dict | None = None
    if record.get("ShipToContactId"):
        shipping = {"contact_id": record["ShipToContactId"]}

    return OrderData(
        order_id=record["Id"],
        customer_id=record.get("AccountId"),
        status=record.get("Status", "Unknown"),
        total=float(record.get("TotalAmount") or 0.0),
        currency=record.get("CurrencyIsoCode", "USD"),
        items=items,
        shipping_address=shipping,
        created_at=_parse_dt(record.get("CreatedDate")),
        updated_at=_parse_dt(record.get("LastModifiedDate")),
    )


def map_campaign_to_segment(record: dict[str, Any]) -> SegmentData:
    """Map a Salesforce Campaign record to ``SegmentData``.

    >>> seg = map_campaign_to_segment({
    ...     "Id": "701xx000004TmiKAAS",
    ...     "Name": "Holiday VIP",
    ...     "Description": "Top spenders Q4",
    ...     "NumberOfContacts": 450,
    ... })
    >>> seg.segment_id
    '701xx000004TmiKAAS'
    >>> seg.name
    'Holiday VIP'
    >>> seg.member_count
    450
    """
    return SegmentData(
        segment_id=record["Id"],
        name=record.get("Name", ""),
        description=record.get("Description"),
        criteria={
            "type": record.get("Type"),
            "status": record.get("Status"),
            "start_date": record.get("StartDate"),
            "end_date": record.get("EndDate"),
        },
        member_count=record.get("NumberOfContacts"),
    )
