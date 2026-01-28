"""Adapters for the inventory reservation validation service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import MockInventoryAdapter
from holiday_peak_lib.schemas.inventory import InventoryContext


@dataclass
class ReservationValidationAdapters:
    """Container for reservation validation adapters."""

    inventory: InventoryConnector
    validator: "ReservationValidator"


class ReservationValidator:
    """Validate reservation requests against available stock."""

    async def validate(
        self,
        context: InventoryContext,
        *,
        request_qty: int,
    ) -> dict[str, Any]:
        item = context.item
        effective_available = max(item.available - item.reserved, 0)
        approved = request_qty <= effective_available
        backorder_qty = max(request_qty - effective_available, 0)
        return {
            "sku": item.sku,
            "requested_qty": request_qty,
            "available": item.available,
            "reserved": item.reserved,
            "effective_available": effective_available,
            "approved": approved,
            "backorder_qty": backorder_qty,
        }


def build_reservation_validation_adapters(
    *, inventory_connector: Optional[InventoryConnector] = None
) -> ReservationValidationAdapters:
    """Create adapters for reservation validation workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    validator = ReservationValidator()
    return ReservationValidationAdapters(inventory=inventory, validator=validator)
