"""Adapters for the logistics carrier selection service."""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any, Optional

from holiday_peak_lib.adapters import BaseExternalAPIAdapter
from holiday_peak_lib.adapters.logistics_adapter import LogisticsConnector
from holiday_peak_lib.adapters.mock_adapters import MockLogisticsAdapter
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.logistics import LogisticsContext


@dataclass
class CarrierSelectionAdapters:
    """Container for carrier selection adapters."""

    logistics: LogisticsConnector
    selector: "CarrierSelector"


class CarrierSelector:
    """Choose a carrier based on shipment attributes."""

    async def select(self, context: LogisticsContext) -> dict[str, Any]:
        shipment = context.shipment
        service = shipment.service_level or "standard"
        carrier = shipment.carrier or ("priority-carrier" if service == "express" else "economy-carrier")
        return {
            "tracking_id": shipment.tracking_id,
            "service_level": service,
            "recommended_carrier": carrier,
            "reason": "matched service level",
        }


def build_carrier_selection_adapters(
    *, logistics_connector: Optional[LogisticsConnector] = None
) -> CarrierSelectionAdapters:
    """Create adapters for carrier selection workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    logistics = logistics_connector or LogisticsConnector(adapter=MockLogisticsAdapter())
    selector = CarrierSelector()
    return CarrierSelectionAdapters(logistics=logistics, selector=selector)


def register_external_api_tools(mcp: FastAPIMCPServer) -> None:
    """Register carrier API tools with MCP when configured."""
    base_url = os.getenv("CARRIER_API_URL")
    if not base_url:
        return
    api_key = os.getenv("CARRIER_API_KEY")
    adapter = BaseExternalAPIAdapter("carrier", base_url=base_url, api_key=api_key)
    adapter.add_api_tool("rates", "POST", "/rates")
    adapter.add_api_tool("services", "GET", "/services")
    adapter.register_mcp_tools(mcp)
