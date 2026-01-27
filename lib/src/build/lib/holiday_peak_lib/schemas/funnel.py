"""Canonical funnel/marketing schemas.

Normalizes funnel metrics for campaign and journey analysis described in the
business summary. Doctests show instantiation with defaults.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class FunnelMetric(BaseModel):
    """Conversion funnel metric for a stage.

    >>> FunnelMetric(stage="view", count=100).count
    100
    """

    stage: str
    count: int
    conversion_rate: Optional[float] = None
    channel: Optional[str] = None
    stage_time_ms: Optional[float] = None
    attributes: dict = Field(default_factory=dict)


class FunnelContext(BaseModel):
    """Aggregate funnel context for agents.

    >>> m = FunnelMetric(stage="click", count=10)
    >>> FunnelContext(campaign_id="cmp", metrics=[m]).metrics[0].stage
    'click'
    """

    campaign_id: Optional[str] = None
    account_id: Optional[str] = None
    metrics: list[FunnelMetric] = Field(default_factory=list)
    updated_at: Optional[datetime] = None
