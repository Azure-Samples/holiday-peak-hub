"""XDM profile-to-canonical model mappings for Adobe Experience Platform.

Translates raw XDM (Experience Data Model) payloads returned by the
Profile Access API into the framework's ``CustomerData`` and
``SegmentData`` canonical models.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from holiday_peak_lib.integrations.contracts import CustomerData, OrderData, SegmentData


def _iso(value: Any) -> datetime | None:
    """Safely parse an ISO-8601 string to a timezone-aware ``datetime``."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _extract_realized_segments(attrs: dict[str, Any]) -> list[str]:
    """Return segment IDs whose status is 'realized' in the UPS membership map."""
    ups: dict[str, Any] = attrs.get("segmentMembership", {}).get("ups", {})
    if not isinstance(ups, dict):
        return []
    return [
        m.get("segmentID", {}).get("_id", "") for m in ups.values() if m.get("status") == "realized"
    ]


def xdm_to_customer(entity: dict[str, Any]) -> CustomerData:
    """Map an XDM entity payload to ``CustomerData``.

    The AEP Profile Access API wraps profile attributes inside
    ``entity._aepMemberships`` (segment memberships) and the XDM
    Person / ContactDetails schemas.  This mapping handles the most
    common top-level field locations used by the default ExperienceEvent
    XDM schema.

    Args:
        entity: Raw JSON object from ``GET /data/core/ups/access/entities``.

    Returns:
        A populated ``CustomerData`` instance.
    """
    attrs: dict[str, Any] = entity.get("entity", entity)

    # Identity
    customer_id: str = str(attrs.get("identities", [{}])[0].get("id", "") or attrs.get("_id", ""))

    # Person name
    person: dict[str, Any] = attrs.get("person", {})
    person_name: dict[str, Any] = person.get("name", {})
    first_name: str | None = person_name.get("firstName") or None
    last_name: str | None = person_name.get("lastName") or None

    # Contact details
    work_email: dict[str, Any] = attrs.get("workEmail", {})
    personal_email: dict[str, Any] = attrs.get("personalEmail", {})
    email: str | None = work_email.get("address") or personal_email.get("address") or None

    home_phone: dict[str, Any] = attrs.get("homePhone", {})
    mobile_phone: dict[str, Any] = attrs.get("mobilePhone", {})
    phone: str | None = home_phone.get("number") or mobile_phone.get("number") or None

    # Segments / audiences from AEP memberships
    segments: list[str] = _extract_realized_segments(attrs)

    # Loyalty
    loyalty_dict: dict[str, Any] = attrs.get("loyalty", {})
    loyalty_tier: str | None = loyalty_dict.get("tier") or None
    lifetime_value: float | None = loyalty_dict.get("lifetimeValue") or None

    # Preferences / consent
    preferences: dict[str, Any] = attrs.get("preferences", {})
    consent: dict[str, Any] = attrs.get("consents", {})

    # Last activity
    last_activity_raw = attrs.get("timeSeriesEvents", [{}])
    last_activity: datetime | None = None
    if isinstance(last_activity_raw, list) and last_activity_raw:
        last_activity = _iso(last_activity_raw[-1].get("timestamp"))

    return CustomerData(
        customer_id=customer_id,
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        segments=segments,
        loyalty_tier=loyalty_tier,
        lifetime_value=lifetime_value,
        preferences=preferences,
        consent=consent,
        last_activity=last_activity,
    )


def audience_to_segment(audience: dict[str, Any]) -> SegmentData:
    """Map an AEP audience object to ``SegmentData``.

    Args:
        audience: Raw JSON object from ``GET /segmentation/audiences``.

    Returns:
        A populated ``SegmentData`` instance.
    """
    return SegmentData(
        segment_id=audience.get("id", ""),
        name=audience.get("name", ""),
        description=audience.get("description"),
        criteria=audience.get("expression", {}),
        member_count=audience.get("totalProfiles"),
    )


def export_record_to_order(record: dict[str, Any]) -> OrderData:
    """Map a profile export record to an ``OrderData`` instance.

    AEP export jobs return flattened XDM ExperienceEvent records.  This
    mapper handles the common ``commerce.order`` schema.

    Args:
        record: A single row from a profile export job result.

    Returns:
        A populated ``OrderData`` instance.
    """
    commerce: dict[str, Any] = record.get("commerce", {})
    order: dict[str, Any] = commerce.get("order", {})
    items_raw: list[dict[str, Any]] = record.get("productListItems", [])
    return OrderData(
        order_id=order.get("purchaseID", record.get("_id", "")),
        customer_id=record.get("endUserIDs", {}).get("_experience", {}).get("aaid", {}).get("id"),
        status=commerce.get("purchases", {}).get("value", "unknown"),
        total=float(order.get("priceTotal", 0.0)),
        currency=order.get("currencyCode", "USD"),
        items=[
            {
                "sku": item.get("SKU", ""),
                "name": item.get("name", ""),
                "quantity": item.get("quantity", 1),
                "price": float(item.get("priceTotal", 0.0)),
            }
            for item in items_raw
        ],
        created_at=_iso(record.get("timestamp")),
    )
