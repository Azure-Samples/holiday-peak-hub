"""Adapters for the CRM profile aggregation service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.crm_adapter import CRMConnector
from holiday_peak_lib.adapters.mock_adapters import MockCRMAdapter
from holiday_peak_lib.schemas.crm import CRMContext


@dataclass
class ProfileAdapters:
    """Container for CRM profile aggregation adapters."""

    crm: CRMConnector
    analytics: "ProfileAnalyticsAdapter"


class ProfileAnalyticsAdapter:
    """Lightweight analytics for aggregating CRM profile insights."""

    async def summarize_profile(self, context: CRMContext) -> dict[str, Any]:
        interactions = context.interactions
        channels = [interaction.channel for interaction in interactions]
        last_interaction = max(
            interactions, key=lambda item: item.occurred_at, default=None
        )
        engagement_score = min(len(interactions) / 10, 1.0)
        return {
            "contact_id": context.contact.contact_id,
            "account_id": context.contact.account_id,
            "marketing_opt_in": context.contact.marketing_opt_in,
            "interaction_count": len(interactions),
            "recent_channels": list(dict.fromkeys(channels)),
            "last_interaction_at": last_interaction.occurred_at.isoformat()
            if last_interaction
            else None,
            "engagement_score": engagement_score,
            "tags": context.contact.tags,
        }


def build_profile_adapters(
    *, crm_connector: Optional[CRMConnector] = None
) -> ProfileAdapters:
    """Create adapters for CRM profile aggregation workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    crm = crm_connector or CRMConnector(adapter=MockCRMAdapter())
    analytics = ProfileAnalyticsAdapter()
    return ProfileAdapters(crm=crm, analytics=analytics)
