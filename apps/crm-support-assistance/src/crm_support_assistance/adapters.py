"""Adapters for the CRM support assistance service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from holiday_peak_lib.adapters.crm_adapter import CRMConnector
from holiday_peak_lib.adapters.mock_adapters import MockCRMAdapter
from holiday_peak_lib.schemas.crm import CRMContext


@dataclass
class SupportAdapters:
    """Container for CRM support assistance adapters."""

    crm: CRMConnector
    assistant: "SupportAssistantAdapter"


class SupportAssistantAdapter:
    """Support guidance generation based on CRM context."""

    async def build_support_brief(
        self, context: CRMContext, *, issue_summary: str | None = None
    ) -> dict[str, Any]:
        interactions = context.interactions
        last_interaction = max(
            interactions, key=lambda item: item.occurred_at, default=None
        )
        sentiment = last_interaction.sentiment if last_interaction else None
        risk = "high" if sentiment in {"negative", "angry"} else "low"
        return {
            "contact_id": context.contact.contact_id,
            "account_id": context.contact.account_id,
            "last_interaction_at": last_interaction.occurred_at.isoformat()
            if last_interaction
            else None,
            "last_channel": last_interaction.channel if last_interaction else None,
            "sentiment": sentiment,
            "risk": risk,
            "issue_summary": issue_summary,
            "next_best_actions": _next_best_actions(context, risk),
        }


def build_support_adapters(
    *, crm_connector: Optional[CRMConnector] = None
) -> SupportAdapters:
    """Create adapters for CRM support assistance workflows.

    Uses mock adapters by default to keep local development lightweight.
    """
    crm = crm_connector or CRMConnector(adapter=MockCRMAdapter())
    assistant = SupportAssistantAdapter()
    return SupportAdapters(crm=crm, assistant=assistant)


def _next_best_actions(context: CRMContext, risk: str) -> list[str]:
    actions = ["Acknowledge issue", "Confirm resolution criteria"]
    if risk == "high":
        actions.append("Escalate to senior support")
    if context.account and context.account.tier:
        actions.append(f"Apply {context.account.tier} account SLA")
    return actions
