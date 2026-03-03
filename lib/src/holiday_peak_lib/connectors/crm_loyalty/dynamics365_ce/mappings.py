"""Mappings from Dynamics 365 CE OData responses to canonical models.

Each ``map_*`` function accepts a raw OData entity dict and returns the
corresponding ``holiday_peak_lib.integrations.contracts`` model.

Dynamics 365 CE field naming conventions used here:
- Contacts: ``contactid``, ``emailaddress1``, ``firstname``, ``lastname``, ``telephone1``
- Accounts: ``accountid``, ``name``
- Orders (salesorders): ``salesorderid``, ``customerid``, ``statecode``,
  ``totalamount``, ``transactioncurrencyid``, ``createdon``, ``modifiedon``
- Segments (marketing lists): ``listid``, ``listname``, ``description``,
  ``membercount``
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from holiday_peak_lib.integrations.contracts import (
    CustomerData,
    OrderData,
    SegmentData,
)


def _parse_dt(value: Any) -> datetime | None:
    """Parse an OData datetime string into a timezone-aware ``datetime``.

    >>> _parse_dt("2024-01-15T12:00:00Z").year
    2024
    >>> _parse_dt(None) is None
    True
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt
    except (ValueError, TypeError):
        return None


def map_contact_to_customer(contact: dict[str, Any]) -> CustomerData:
    """Map a Dynamics 365 CE contact entity to ``CustomerData``.

    :param contact: Raw OData contact entity dict.
    :returns: Canonical ``CustomerData`` instance.

    >>> data = map_contact_to_customer({
    ...     "contactid": "c-1",
    ...     "emailaddress1": "test@example.com",
    ...     "firstname": "Ada",
    ...     "lastname": "Lovelace",
    ...     "telephone1": "555-0100",
    ... })
    >>> data.customer_id
    'c-1'
    >>> data.email
    'test@example.com'
    """
    return CustomerData(
        customer_id=contact.get("contactid", ""),
        email=contact.get("emailaddress1"),
        first_name=contact.get("firstname"),
        last_name=contact.get("lastname"),
        phone=contact.get("telephone1"),
        segments=[],
        loyalty_tier=contact.get("new_loyaltytier"),
        lifetime_value=contact.get("new_lifetimevalue"),
        preferences=contact.get("new_preferences") or {},
        consent=contact.get("new_consent") or {},
        last_activity=_parse_dt(contact.get("modifiedon")),
    )


def map_salesorder_to_order(order: dict[str, Any]) -> OrderData:
    """Map a Dynamics 365 CE salesorder entity to ``OrderData``.

    :param order: Raw OData salesorder entity dict.
    :returns: Canonical ``OrderData`` instance.

    >>> data = map_salesorder_to_order({
    ...     "salesorderid": "o-1",
    ...     "customerid": "c-1",
    ...     "statecode": 0,
    ...     "totalamount": 99.99,
    ...     "transactioncurrencyid": "USD",
    ...     "createdon": "2024-06-01T10:00:00Z",
    ... })
    >>> data.order_id
    'o-1'
    >>> data.total
    99.99
    """
    status_map = {0: "open", 1: "won", 2: "cancelled"}
    state = order.get("statecode", 0)
    status = status_map.get(state, str(state))

    customer_raw = order.get("customerid")
    customer_id: str | None = None
    if isinstance(customer_raw, dict):
        customer_id = customer_raw.get("contactid") or customer_raw.get("accountid")
    elif isinstance(customer_raw, str):
        customer_id = customer_raw

    return OrderData(
        order_id=order.get("salesorderid", ""),
        customer_id=customer_id,
        status=status,
        total=float(order.get("totalamount") or 0.0),
        currency=order.get("transactioncurrencyid") or "USD",
        items=order.get("order_details") or [],
        shipping_address=order.get("shipto_composite"),
        billing_address=order.get("billto_composite"),
        created_at=_parse_dt(order.get("createdon")),
        updated_at=_parse_dt(order.get("modifiedon")),
    )


def map_marketinglist_to_segment(lst: dict[str, Any]) -> SegmentData:
    """Map a Dynamics 365 CE marketing list to ``SegmentData``.

    :param lst: Raw OData marketing list entity dict.
    :returns: Canonical ``SegmentData`` instance.

    >>> data = map_marketinglist_to_segment({
    ...     "listid": "s-1",
    ...     "listname": "VIP Customers",
    ...     "description": "High value segment",
    ...     "membercount": 42,
    ...     "query": "revenue > 10000",
    ... })
    >>> data.segment_id
    's-1'
    >>> data.member_count
    42
    """
    return SegmentData(
        segment_id=lst.get("listid", ""),
        name=lst.get("listname", ""),
        description=lst.get("description"),
        criteria={"query": lst.get("query")} if lst.get("query") else {},
        member_count=lst.get("membercount"),
    )
