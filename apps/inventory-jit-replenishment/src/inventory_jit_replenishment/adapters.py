"""Adapters for the inventory JIT replenishment service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import MockInventoryAdapter
from holiday_peak_lib.schemas.inventory import InventoryContext


@dataclass
class InventoryReplenishmentAdapters:
    """Container for JIT replenishment adapters."""

    inventory: InventoryConnector
    planner: "ReplenishmentPlanner"


class ReplenishmentPlanner:
    """Compute reorder quantities using simple heuristics."""

    async def build_replenishment_plan(
        self,
        context: InventoryContext,
        *,
        target_stock: int = 20,
    ) -> dict[str, Any]:
        item = context.item
        effective_available = max(item.available - item.reserved, 0)
        reorder_qty = max(target_stock - effective_available, 0)
        return {
            "sku": item.sku,
            "available": item.available,
            "reserved": item.reserved,
            "target_stock": target_stock,
            "recommended_reorder_qty": reorder_qty,
            "lead_time_days": item.lead_time_days,
            "safety_stock": item.safety_stock,
        }


def build_replenishment_adapters(
    *, inventory_connector: Optional[InventoryConnector] = None
) -> InventoryReplenishmentAdapters:
    """Create adapters for JIT replenishment workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    inventory = inventory_connector or InventoryConnector(adapter=MockInventoryAdapter())
    planner = ReplenishmentPlanner()
    return InventoryReplenishmentAdapters(inventory=inventory, planner=planner)
