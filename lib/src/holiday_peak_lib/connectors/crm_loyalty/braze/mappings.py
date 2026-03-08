"""Mappings from Braze API payloads to canonical protocol models.

Each function accepts a raw dict (as returned by the Braze REST API) and
returns the equivalent canonical model instance.
"""

from __future__ import annotations

from datetime import datetime

from holiday_peak_lib.integrations.contracts import CustomerData, OrderData, SegmentData


def map_braze_user_to_customer(raw: dict) -> CustomerData:
    """Convert a Braze user object to :class:`CustomerData`.

    The Braze user export endpoint returns a JSON object with fields like
    ``external_id``, ``email``, ``first_name``, ``last_name``, ``phone``,
    ``custom_attributes``, and ``purchases``.  Only the canonical fields
    are extracted; everything else is stored under ``preferences``.

    >>> raw = {
    ...     "external_id": "u1",
    ...     "email": "u@example.com",
    ...     "first_name": "Ada",
    ...     "last_name": "Lovelace",
    ...     "phone": "+1555000000",
    ...     "custom_attributes": {"tier": "gold"},
    ...     "last_used_app": {"time": "2024-01-01T00:00:00Z"},
    ... }
    >>> c = map_braze_user_to_customer(raw)
    >>> c.customer_id
    'u1'
    >>> c.email
    'u@example.com'
    >>> c.loyalty_tier
    'gold'
    """
    custom_attrs: dict = dict(raw.get("custom_attributes") or {})
    loyalty_tier: str | None = custom_attrs.pop("tier", None) or custom_attrs.pop(
        "loyalty_tier", None
    )
    lifetime_value: float | None = None
    raw_ltv = custom_attrs.pop("lifetime_value", None)
    if raw_ltv is not None:
        try:
            lifetime_value = float(raw_ltv)
        except (TypeError, ValueError):
            lifetime_value = None

    segments: list[str] = [s.get("name", "") for s in (raw.get("user_aliases") or [])]

    last_activity: datetime | None = None
    last_used = (raw.get("last_used_app") or {}).get("time")
    if last_used:
        try:
            last_activity = datetime.fromisoformat(last_used.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            last_activity = None

    return CustomerData(
        customer_id=raw.get("external_id") or raw.get("braze_id", ""),
        email=raw.get("email"),
        first_name=raw.get("first_name"),
        last_name=raw.get("last_name"),
        phone=raw.get("phone"),
        segments=segments,
        loyalty_tier=loyalty_tier,
        lifetime_value=lifetime_value,
        preferences=custom_attrs,
        consent={
            "email_subscribe": raw.get("email_subscribe"),
            "push_subscribe": raw.get("push_subscribe"),
        },
        last_activity=last_activity,
    )


def map_braze_purchase_to_order(raw: dict) -> OrderData:
    """Convert a Braze purchase object to :class:`OrderData`.

    Braze purchases are embedded in the user export payload under the
    ``purchases`` key.  Each entry looks like::

        {"product_id": "sku-1", "currency": "USD", "price": 9.99,
         "time": "2024-01-01T12:00:00Z", "quantity": 1}

    >>> raw = {
    ...     "product_id": "sku-1",
    ...     "currency": "USD",
    ...     "price": 9.99,
    ...     "time": "2024-01-01T12:00:00Z",
    ...     "quantity": 1,
    ... }
    >>> o = map_braze_purchase_to_order(raw)
    >>> o.order_id
    'sku-1_2024-01-01T12:00:00Z'
    >>> o.total
    9.99
    """
    product_id = raw.get("product_id", "")
    time_str = raw.get("time", "")
    order_id = f"{product_id}_{time_str}" if product_id else time_str

    created_at: datetime | None = None
    if time_str:
        try:
            created_at = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            created_at = None

    qty = raw.get("quantity", 1)
    price = float(raw.get("price", 0.0))

    return OrderData(
        order_id=order_id,
        status="completed",
        total=price * qty,
        currency=raw.get("currency", "USD"),
        items=[{"product_id": product_id, "quantity": qty, "price": price}],
        created_at=created_at,
    )


def map_braze_segment_to_segment(raw: dict) -> SegmentData:
    """Convert a Braze segment object to :class:`SegmentData`.

    Braze segment list entries look like::

        {"id": "seg-1", "name": "Holiday Shoppers",
         "analytics_tracking_enabled": true}

    >>> raw = {"id": "seg-1", "name": "Holiday Shoppers",
    ...        "analytics_tracking_enabled": True}
    >>> s = map_braze_segment_to_segment(raw)
    >>> s.segment_id
    'seg-1'
    >>> s.name
    'Holiday Shoppers'
    """
    return SegmentData(
        segment_id=raw.get("id", ""),
        name=raw.get("name", ""),
        description=raw.get("description"),
        criteria={"analytics_tracking_enabled": raw.get("analytics_tracking_enabled", False)},
        member_count=raw.get("size"),
    )
