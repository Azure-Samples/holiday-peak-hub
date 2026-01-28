"""Adapters for the CRM campaign intelligence service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from holiday_peak_lib.adapters.crm_adapter import CRMConnector
from holiday_peak_lib.adapters.funnel_adapter import FunnelConnector
from holiday_peak_lib.adapters.mock_adapters import MockCRMAdapter, MockFunnelAdapter
from holiday_peak_lib.schemas.funnel import FunnelContext


@dataclass
class CampaignAdapters:
    """Container for campaign intelligence adapters."""

    crm: CRMConnector
    funnel: FunnelConnector
    analytics: "CampaignAnalyticsAdapter"


class CampaignAnalyticsAdapter:
    """Lightweight analytics for campaign ROI estimation."""

    async def estimate_roi(
        self,
        funnel: FunnelContext,
        *,
        spend: float,
        avg_order_value: float,
    ) -> dict[str, float | int]:
        conversions = _infer_conversions(funnel)
        revenue = conversions * avg_order_value
        roi = 0.0 if spend <= 0 else (revenue - spend) / spend
        return {
            "conversions": conversions,
            "revenue": revenue,
            "spend": spend,
            "roi": roi,
        }


def build_campaign_adapters(
    *,
    crm_connector: Optional[CRMConnector] = None,
    funnel_connector: Optional[FunnelConnector] = None,
) -> CampaignAdapters:
    """Create adapters for campaign intelligence workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    crm = crm_connector or CRMConnector(adapter=MockCRMAdapter())
    funnel = funnel_connector or FunnelConnector(adapter=MockFunnelAdapter())
    analytics = CampaignAnalyticsAdapter()
    return CampaignAdapters(crm=crm, funnel=funnel, analytics=analytics)


def _infer_conversions(funnel: FunnelContext) -> int:
    if not funnel.metrics:
        return 0
    stage_priority = ["purchase", "conversion", "checkout", "click", "view"]
    lookup = {metric.stage.lower(): metric for metric in funnel.metrics}
    for stage in stage_priority:
        metric = lookup.get(stage)
        if metric is not None:
            return metric.count
    return funnel.metrics[-1].count
