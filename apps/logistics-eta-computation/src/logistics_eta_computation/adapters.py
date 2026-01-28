"""Adapters for the logistics ETA computation service."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from holiday_peak_lib.adapters.logistics_adapter import LogisticsConnector
from holiday_peak_lib.adapters.mock_adapters import MockLogisticsAdapter
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
        now = datetime.utcnow()
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
