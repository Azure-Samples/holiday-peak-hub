"""Adapters for the logistics ETA computation service."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from holiday_peak_lib.adapters import BaseExternalAPIAdapter
from holiday_peak_lib.adapters.logistics_adapter import LogisticsConnector
from holiday_peak_lib.adapters.mock_adapters import MockLogisticsAdapter
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.logistics import LogisticsContext


@dataclass
class EtaComputationAdapters:
    """Container for ETA computation adapters."""

    logistics: LogisticsConnector
    estimator: "EtaEstimator"


class EtaEstimator:
    """Compute ETA based on event timeline."""

    async def compute_eta(self, context: LogisticsContext) -> dict[str, Any]:
        shipment = context.shipment
        base_eta = shipment.eta
        if base_eta:
            return {
                "tracking_id": shipment.tracking_id,
                "eta": base_eta.isoformat(),
                "source": "carrier",
            }
        now = datetime.now(timezone.utc)
        inferred_eta = now + timedelta(days=2)
        return {
            "tracking_id": shipment.tracking_id,
            "eta": inferred_eta.isoformat(),
            "source": "estimated",
        }


def build_eta_adapters(
    *, logistics_connector: Optional[LogisticsConnector] = None
) -> EtaComputationAdapters:
    """Create adapters for ETA computation workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    logistics = logistics_connector or LogisticsConnector(adapter=MockLogisticsAdapter())
    estimator = EtaEstimator()
    return EtaComputationAdapters(logistics=logistics, estimator=estimator)


def register_external_api_tools(mcp: FastAPIMCPServer) -> None:
    """Register ETA API tools with MCP when configured."""
    base_url = os.getenv("ETA_API_URL")
    if not base_url:
        return
    api_key = os.getenv("ETA_API_KEY")
    adapter = BaseExternalAPIAdapter("eta", base_url=base_url, api_key=api_key)
    adapter.add_api_tool("estimate", "POST", "/estimate")
    adapter.register_mcp_tools(mcp)
