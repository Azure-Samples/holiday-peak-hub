"""Adapters for the inventory reservation validation service."""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Optional

from holiday_peak_lib.adapters import BaseExternalAPIAdapter
from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector
from holiday_peak_lib.adapters.mock_adapters import MockInventoryAdapter
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
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


def register_external_api_tools(mcp: FastAPIMCPServer) -> None:
    """Register warehouse API tools with MCP when configured."""
    base_url = os.getenv("WAREHOUSE_API_URL")
    if not base_url:
        return
    api_key = os.getenv("WAREHOUSE_API_KEY")
    adapter = BaseExternalAPIAdapter("warehouse", base_url=base_url, api_key=api_key)
    adapter.add_api_tool("reserve", "POST", "/reservations")
    adapter.add_api_tool("release", "POST", "/reservations/release")
    adapter.add_api_tool("status", "GET", "/reservations/status")
    adapter.register_mcp_tools(mcp)
