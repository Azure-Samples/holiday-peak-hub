"""Mappings from Oracle Fusion Cloud SCM API responses to canonical models.

Oracle Fusion Cloud REST resources use camelCase JSON keys. This module
translates those payloads into :class:`~holiday_peak_lib.connectors.common.protocols.InventoryData`
objects that agents and downstream services can consume uniformly.
"""

from datetime import datetime
from typing import Any, Optional

from holiday_peak_lib.connectors.common.protocols import InventoryData


def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-8601 string (with or without timezone) into a datetime.

    Returns ``None`` when *value* is empty or cannot be parsed.

    >>> _parse_datetime("2024-01-15T12:00:00") is not None
    True
    >>> _parse_datetime(None) is None
    True
    >>> _parse_datetime("") is None
    True
    """
    if not value:
        return None
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def map_on_hand_quantity(raw: dict[str, Any]) -> InventoryData:
    """Map an Oracle *onHandQuantities* resource record to :class:`InventoryData`.

    Oracle key reference (REST 11.13.18.05):
    - ``ItemNumber``           → item_number
    - ``OrganizationCode``     → organization_code
    - ``OrganizationId``       → organization_id
    - ``Description``          → description
    - ``PrimaryOnHandQuantity`` → on_hand_quantity
    - ``ReservedQuantity``     → reserved_quantity
    - ``PrimaryUOMCode``       → unit_of_measure
    - ``SubinventoryCode``     → subinventory_code
    - ``LocatorName``          → locator
    - ``LotNumber``            → lot_number
    - ``LotExpirationDate``    → expiration_date
    - ``LastUpdateDate``       → last_updated

    >>> record = {
    ...     "ItemNumber": "ITEM-001",
    ...     "OrganizationCode": "M1",
    ...     "PrimaryOnHandQuantity": 50.0,
    ...     "ReservedQuantity": 10.0,
    ... }
    >>> data = map_on_hand_quantity(record)
    >>> data.item_number
    'ITEM-001'
    >>> data.on_hand_quantity
    50.0
    >>> data.effective_available
    40.0
    """
    return InventoryData(
        item_number=raw.get("ItemNumber", ""),
        organization_code=raw.get("OrganizationCode", ""),
        organization_id=raw.get("OrganizationId"),
        description=raw.get("Description"),
        on_hand_quantity=float(raw.get("PrimaryOnHandQuantity") or 0),
        reserved_quantity=float(raw.get("ReservedQuantity") or 0),
        unit_of_measure=raw.get("PrimaryUOMCode"),
        subinventory_code=raw.get("SubinventoryCode"),
        locator=raw.get("LocatorName"),
        lot_number=raw.get("LotNumber"),
        expiration_date=_parse_datetime(raw.get("LotExpirationDate")),
        last_updated=_parse_datetime(raw.get("LastUpdateDate")),
        attributes={
            k: v
            for k, v in raw.items()
            if k
            not in {
                "ItemNumber",
                "OrganizationCode",
                "OrganizationId",
                "Description",
                "PrimaryOnHandQuantity",
                "ReservedQuantity",
                "PrimaryUOMCode",
                "SubinventoryCode",
                "LocatorName",
                "LotNumber",
                "LotExpirationDate",
                "LastUpdateDate",
            }
        },
    )


def map_on_hand_quantities(raw_list: list[dict[str, Any]]) -> list[InventoryData]:
    """Map a list of Oracle onHandQuantities records to canonical models.

    >>> records = [
    ...     {"ItemNumber": "A", "OrganizationCode": "M1", "PrimaryOnHandQuantity": 5},
    ...     {"ItemNumber": "B", "OrganizationCode": "M2", "PrimaryOnHandQuantity": 10},
    ... ]
    >>> result = map_on_hand_quantities(records)
    >>> [r.item_number for r in result]
    ['A', 'B']
    """
    return [map_on_hand_quantity(r) for r in raw_list]
