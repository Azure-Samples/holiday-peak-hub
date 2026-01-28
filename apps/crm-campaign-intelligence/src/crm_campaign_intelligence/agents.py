"""Campaign intelligence agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import CampaignAdapters, build_campaign_adapters


class CampaignIntelligenceAgent(BaseRetailAgent):
    """Agent that generates campaign intelligence insights."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_campaign_adapters()

    @property
    def adapters(self) -> CampaignAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        query = request.get("query", "")
        contact_id = request.get("contact_id")
        account_id = request.get("account_id")
        campaign_id = request.get("campaign_id")
        interaction_limit = int(request.get("interaction_limit", 20))
        funnel_limit = int(request.get("funnel_limit", 20))

        crm_context = None
        if contact_id:
            crm_context = await self.adapters.crm.build_contact_context(
                contact_id, interaction_limit=interaction_limit
            )

        funnel_context = await self.adapters.funnel.build_funnel_context(
            campaign_id=campaign_id,
            account_id=account_id,
            limit=funnel_limit,
        )

        if self.slm or self.llm:
            messages = [
                {
                    "role": "system",
                    "content": _campaign_instructions(self.service_name or "campaign"),
                },
                {
                    "role": "user",
                    "content": {
                        "query": query,
                        "contact_id": contact_id,
                        "account_id": account_id,
                        "campaign_id": campaign_id,
                        "crm_context": crm_context.model_dump() if crm_context else None,
                        "funnel_context": funnel_context.model_dump(),
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "query": query,
            "crm_context": crm_context.model_dump() if crm_context else None,
            "funnel_context": funnel_context.model_dump(),
            "insight": "Campaign intelligence stub response.",
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for campaign intelligence workflows."""
    adapters = getattr(agent, "adapters", build_campaign_adapters())

    async def get_contact_context(payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}
        limit = int(payload.get("interaction_limit", 20))
        context = await adapters.crm.build_contact_context(contact_id, interaction_limit=limit)
        return {"contact_context": context.model_dump() if context else None}

    async def get_funnel_context(payload: dict[str, Any]) -> dict[str, Any]:
        context = await adapters.funnel.build_funnel_context(
            campaign_id=payload.get("campaign_id"),
            account_id=payload.get("account_id"),
            limit=int(payload.get("limit", 20)),
        )
        return {"funnel_context": context.model_dump()}

    async def estimate_campaign_roi(payload: dict[str, Any]) -> dict[str, Any]:
        funnel_context = await adapters.funnel.build_funnel_context(
            campaign_id=payload.get("campaign_id"),
            account_id=payload.get("account_id"),
            limit=int(payload.get("limit", 20)),
        )
        spend = float(payload.get("spend", 0.0))
        avg_order_value = float(payload.get("avg_order_value", 0.0))
        roi = await adapters.analytics.estimate_roi(
            funnel_context, spend=spend, avg_order_value=avg_order_value
        )
        return {"roi": roi, "funnel_context": funnel_context.model_dump()}

    mcp.add_tool("/campaign/contact-context", get_contact_context)
    mcp.add_tool("/campaign/funnel-context", get_funnel_context)
    mcp.add_tool("/campaign/roi", estimate_campaign_roi)


def _campaign_instructions(service_name: str) -> str:
    return (
        f"You are the {service_name} agent. "
        "Be proactive on every request tied to campaign evaluation. "
        "Use CRM context and funnel metrics to summarize performance, "
        "identify drop-off stages, and recommend next actions to improve ROI. "
        "Always include a lightweight monitoring note: what to track next (e.g., "
        "key funnel stage, segment, or channel), and any risks or anomalies to watch. "
        "If data is missing, call it out and propose safe assumptions."
    )
