"""Adapters for the inventory health check service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import MockInventoryAdapter
from holiday_peak_lib.schemas.inventory import InventoryContext


@dataclass
class InventoryHealthAdapters:
    """Container for inventory health check adapters."""

    inventory: InventoryConnector
    analytics: "InventoryHealthAnalytics"


class InventoryHealthAnalytics:
    """Detect anomalies and health signals in inventory context."""

    async def evaluate_health(self, context: InventoryContext) -> dict[str, Any]:
        item = context.item
        issues = []
        if item.available < 0:
            issues.append("negative_available")
        if item.reserved > item.available:
            issues.append("reserved_exceeds_available")
        if not context.warehouses:
            issues.append("no_warehouse_stock")
        return {
            "sku": item.sku,
            "available": item.available,
            "reserved": item.reserved,
            "issues": issues,
            "health": "degraded" if issues else "healthy",
        }


def build_inventory_health_adapters(
    *, inventory_connector: Optional[InventoryConnector] = None
) -> InventoryHealthAdapters:
    """Create adapters for inventory health workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    analytics = InventoryHealthAnalytics()
    return InventoryHealthAdapters(inventory=inventory, analytics=analytics)
