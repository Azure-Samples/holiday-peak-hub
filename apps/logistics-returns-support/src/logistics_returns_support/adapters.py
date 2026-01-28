"""Adapters for the logistics returns support service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.logistics_adapter import LogisticsConnector
from holiday_peak_lib.adapters.mock_adapters import MockLogisticsAdapter
from holiday_peak_lib.schemas.logistics import LogisticsContext


@dataclass
class ReturnsSupportAdapters:
    """Container for returns support adapters."""

    logistics: LogisticsConnector
    assistant: "ReturnsSupportAssistant"


class ReturnsSupportAssistant:
    """Generate returns support guidance from logistics context."""

    async def build_returns_plan(self, context: LogisticsContext) -> dict[str, Any]:
        shipment = context.shipment
        status = shipment.status
        return {
            "tracking_id": shipment.tracking_id,
            "status": status,
            "eligible_for_return": status in {"delivered", "in_transit"},
            "next_steps": _return_next_steps(status),
        }


def build_returns_support_adapters(
    *, logistics_connector: Optional[LogisticsConnector] = None
) -> ReturnsSupportAdapters:
    """Create adapters for returns support workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    logistics = logistics_connector or LogisticsConnector(adapter=MockLogisticsAdapter())
    assistant = ReturnsSupportAssistant()
    return ReturnsSupportAdapters(logistics=logistics, assistant=assistant)


def _return_next_steps(status: str) -> list[str]:
    if status == "delivered":
        return ["Confirm return reason", "Issue return label", "Schedule pickup"]
    return ["Confirm shipment status", "Offer return window", "Notify support"]
