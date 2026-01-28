"""Adapters for the logistics route issue detection service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.logistics_adapter import LogisticsConnector
from holiday_peak_lib.adapters.mock_adapters import MockLogisticsAdapter
from holiday_peak_lib.schemas.logistics import LogisticsContext


@dataclass
class RouteIssueAdapters:
    """Container for route issue detection adapters."""

    logistics: LogisticsConnector
    detector: "RouteIssueDetector"


class RouteIssueDetector:
    """Detect issues from shipment event timelines."""

    async def detect(self, context: LogisticsContext) -> dict[str, Any]:
        shipment = context.shipment
        status = shipment.status
        delayed = status in {"exception", "delayed"}
        last_event = max(context.events, key=lambda e: e.occurred_at, default=None)
        return {
            "tracking_id": shipment.tracking_id,
            "status": status,
            "delayed": delayed,
            "last_event": last_event.code if last_event else None,
        }


def build_route_issue_adapters(
    *, logistics_connector: Optional[LogisticsConnector] = None
) -> RouteIssueAdapters:
    """Create adapters for route issue detection workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    logistics = logistics_connector or LogisticsConnector(adapter=MockLogisticsAdapter())
    detector = RouteIssueDetector()
    return RouteIssueAdapters(logistics=logistics, detector=detector)
