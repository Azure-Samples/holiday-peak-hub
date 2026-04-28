"""CRM support assistance agent implementation and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.memory import (
    CacheConfig,
    inject_session_id,
    resolve_cache_key,
    try_cache_read,
)
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import get_agent_adapters

from .adapters import SupportAdapters, build_support_adapters


class SupportAssistanceAgent(BaseRetailAgent):
    """Agent that prepares CRM support guidance and next actions."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_support_adapters()

    @property
    def adapters(self) -> SupportAdapters:
        return self._adapters

    _cache_config = CacheConfig(
        service="crm-support-assistance",
        entity_prefix="support",
        ttl_seconds=180,
        entity_key_field="contact_id",
    )

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        contact_id = request.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}

        cache_key = resolve_cache_key(request, self._cache_config)
        cached = await try_cache_read(self.hot_memory, cache_key, ttl_seconds=180)
        if cached is not None:
            return cached

        issue_summary = request.get("issue_summary")
        interaction_limit = int(request.get("interaction_limit", 20))
        context = await self.adapters.crm.build_contact_context(
            contact_id, interaction_limit=interaction_limit
        )
        if not context:
            return {"error": "contact not found", "contact_id": contact_id}

        brief = await self.adapters.assistant.build_support_brief(
            context, issue_summary=issue_summary
        )

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _support_instructions()},
                {
                    "role": "user",
                    "content": {
                        "query": request.get("query", ""),
                        "contact_id": contact_id,
                        "issue_summary": issue_summary,
                        "crm_context": context.model_dump(),
                        "support_brief": brief,
                    },
                },
            ]
            result = await self.invoke_model(
                request=inject_session_id(request, self._cache_config), messages=messages
            )
            self.background_cache_write(cache_key, result, ttl_seconds=180)
            return result

        result = {
            "service": self.service_name,
            "contact_id": contact_id,
            "crm_context": context.model_dump(),
            "support_brief": brief,
        }
        self.background_cache_write(cache_key, result, ttl_seconds=180)
        return result


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for CRM support assistance workflows."""
    adapters = get_agent_adapters(agent, build_support_adapters)

    async def get_contact_context(payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}
        limit = int(payload.get("interaction_limit", 20))
        context = await adapters.crm.build_contact_context(contact_id, interaction_limit=limit)
        return {"crm_context": context.model_dump() if context else None}

    async def get_interaction_summary(payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}
        interactions = await adapters.crm.get_interactions(contact_id, limit=10)
        summary = [
            {
                "interaction_id": i.interaction_id,
                "channel": i.channel,
                "occurred_at": i.occurred_at.isoformat(),
                "sentiment": i.sentiment,
            }
            for i in interactions
        ]
        return {"interactions": summary}

    async def get_support_brief(payload: dict[str, Any]) -> dict[str, Any]:
        contact_id = payload.get("contact_id")
        if not contact_id:
            return {"error": "contact_id is required"}
        context = await adapters.crm.build_contact_context(contact_id)
        if not context:
            return {"error": "contact not found", "contact_id": contact_id}
        brief = await adapters.assistant.build_support_brief(
            context, issue_summary=payload.get("issue_summary")
        )
        return {"support_brief": brief}

    mcp.add_tool("/crm/support/brief", get_support_brief)
    mcp.add_tool("/crm/support/contact-context", get_contact_context)
    mcp.add_tool("/crm/support/interaction-summary", get_interaction_summary)


def _support_instructions() -> str:
    return load_prompt_instructions(__file__, "crm-support-assistance")
