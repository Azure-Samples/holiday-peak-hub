"""CRM profile aggregation agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import ProfileAdapters, build_profile_adapters


class ProfileAggregationAgent(BaseRetailAgent):
    """Agent that aggregates CRM profile context for downstream use."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_profile_adapters()

    @property
    def adapters(self) -> ProfileAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        contact_id = request.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}

        interaction_limit = int(request.get("interaction_limit", 20))
        context = await self.adapters.crm.build_contact_context(
            contact_id, interaction_limit=interaction_limit
        )
        if not context:
            return {"error": "contact not found", "contact_id": contact_id}

        summary = await self.adapters.analytics.summarize_profile(context)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _profile_instructions()},
                {
                    "role": "user",
                    "content": {
                        "query": request.get("query", ""),
                        "contact_id": contact_id,
                        "profile_context": context.model_dump(),
                        "profile_summary": summary,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "contact_id": contact_id,
            "profile_context": context.model_dump(),
            "profile_summary": summary,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for CRM profile aggregation workflows."""
    adapters = getattr(agent, "adapters", build_profile_adapters())

    async def get_contact_context(payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}
        limit = int(payload.get("interaction_limit", 20))
        context = await adapters.crm.build_contact_context(contact_id, interaction_limit=limit)
        return {"profile_context": context.model_dump() if context else None}

    async def get_profile_summary(payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}
        limit = int(payload.get("interaction_limit", 20))
        context = await adapters.crm.build_contact_context(contact_id, interaction_limit=limit)
        if not context:
            return {"error": "contact not found", "contact_id": contact_id}
        summary = await adapters.analytics.summarize_profile(context)
        return {"profile_summary": summary}

    async def get_account_summary(payload: dict[str, Any]) -> dict[str, Any]:
        account_id = payload.get("account_id")
        contact_id = payload.get("contact_id")
        if not account_id and not contact_id:
            return {"error": "account_id or contact_id is required"}
        if not account_id and contact_id:
            context = await adapters.crm.build_contact_context(contact_id)
            account_id = context.account.account_id if context and context.account else None
        if not account_id:
            return {"error": "account not found"}
        account = await adapters.crm.get_account(account_id)
        return {"account": account.model_dump() if account else None}

    mcp.add_tool("/crm/profile/context", get_contact_context)
    mcp.add_tool("/crm/profile/summary", get_profile_summary)
    mcp.add_tool("/crm/profile/account", get_account_summary)


def _profile_instructions() -> str:
    return (
        "You are a CRM profile aggregation agent. "
        "Summarize key profile signals (identity, account, engagement, channels). "
        "Highlight gaps and suggest data to collect next. "
        "Return concise bullets focused on actionable context."
    )
