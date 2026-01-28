"""Adapters for the inventory alerts and triggers service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import MockInventoryAdapter
from holiday_peak_lib.schemas.inventory import InventoryContext


@dataclass
class InventoryAlertsAdapters:
    """Container for inventory alert adapters."""

    inventory: InventoryConnector
    analytics: "InventoryAlertsAnalytics"


class InventoryAlertsAnalytics:
    """Build alert triggers from inventory context."""

    async def build_alerts(
        self,
        context: InventoryContext,
        *,
        threshold: int = 5,
    ) -> dict[str, Any]:
        item = context.item
        low_stock = item.available <= threshold
        reserved_pressure = item.reserved > item.available
        status = item.status or ("low" if low_stock else "healthy")
        alerts = []
        if low_stock:
            alerts.append("low_stock")
        if reserved_pressure:
            alerts.append("reserved_exceeds_available")
        return {
            "sku": item.sku,
            "available": item.available,
            "reserved": item.reserved,
            "status": status,
            "alerts": alerts,
            "threshold": threshold,
        }


def build_inventory_alerts_adapters(
    *, inventory_connector: Optional[InventoryConnector] = None
) -> InventoryAlertsAdapters:
    """Create adapters for inventory alert workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    analytics = InventoryAlertsAnalytics()
    return InventoryAlertsAdapters(inventory=inventory, analytics=analytics)
