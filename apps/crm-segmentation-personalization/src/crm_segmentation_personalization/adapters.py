"""Adapters for the CRM segmentation and personalization service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.crm_adapter import CRMConnector
from holiday_peak_lib.adapters.mock_adapters import MockCRMAdapter
from holiday_peak_lib.schemas.crm import CRMContext


@dataclass
class SegmentationAdapters:
    """Container for CRM segmentation adapters."""

    crm: CRMConnector
    segmenter: "SegmentationAdapter"


class SegmentationAdapter:
    """Heuristic segmentation and personalization rules."""

    async def build_segment(self, context: CRMContext) -> dict[str, Any]:
        interactions = context.interactions
        interaction_count = len(interactions)
        if not context.contact.marketing_opt_in:
            segment = "do-not-contact"
        elif interaction_count == 0:
            segment = "new-lead"
        elif interaction_count >= 5:
            segment = "engaged"
        else:
            segment = "nurture"

        channel = _preferred_channel(interactions)
        personalization = {
            "preferred_channel": channel,
            "recommended_content": _recommended_content(context, segment),
        }
        return {
            "segment": segment,
            "interaction_count": interaction_count,
            "personalization": personalization,
            "tags": context.contact.tags,
            "account_tier": context.account.tier if context.account else None,
        }


def build_segmentation_adapters(
    *, crm_connector: Optional[CRMConnector] = None
) -> SegmentationAdapters:
    """Create adapters for CRM segmentation workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    crm = crm_connector or CRMConnector(adapter=MockCRMAdapter())
    segmenter = SegmentationAdapter()
    return SegmentationAdapters(crm=crm, segmenter=segmenter)


def _preferred_channel(interactions) -> str | None:
    if not interactions:
        return None
    counts: dict[str, int] = {}
    for interaction in interactions:
        counts[interaction.channel] = counts.get(interaction.channel, 0) + 1
    return max(counts, key=counts.get)


def _recommended_content(context: CRMContext, segment: str) -> list[str]:
    if segment == "do-not-contact":
        return ["Respect opt-out; focus on account-level updates."]
    if segment == "new-lead":
        return ["Welcome series", "Onboarding tips", "Product overview"]
    if segment == "engaged":
        return ["Upgrade offer", "Loyalty program", "Cross-sell bundle"]
    return ["Education series", "Case studies", "Trial extension"]
