"""Logistics route issue detection agent implementation and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.memory import (
    CacheConfig,
    cache_write,
    inject_session_id,
    resolve_cache_key,
    try_cache_read,
)
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import (
    get_agent_adapters,
    mcp_context_tool,
)

from .adapters import RouteIssueAdapters, build_route_issue_adapters


class RouteIssueDetectionAgent(BaseRetailAgent):
    """Agent that detects route issues for shipments."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_route_issue_adapters()

    @property
    def adapters(self) -> RouteIssueAdapters:
        return self._adapters

    _cache_config = CacheConfig(
        service="logistics-route-issue-detection",
        entity_prefix="route",
        ttl_seconds=180,
        entity_key_field="tracking_id",
        fallback_entity_fields=("shipment_id", "route_id"),
    )

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        tracking_id = request.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}

        cache_key = resolve_cache_key(request, self._cache_config)
        cached = await try_cache_read(self.hot_memory, cache_key, ttl_seconds=180)
        if cached is not None:
            return cached

        context = await self.adapters.logistics.build_logistics_context(str(tracking_id))
        if not context:
            return {"error": "shipment not found", "tracking_id": tracking_id}

        issues = await self.adapters.detector.detect(context)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _route_instructions()},
                {
                    "role": "user",
                    "content": {
                        "tracking_id": tracking_id,
                        "logistics_context": context.model_dump(),
                        "issues": issues,
                    },
                },
            ]
            result = await self.invoke_model(
                request=inject_session_id(request, self._cache_config), messages=messages
            )
            await cache_write(self.hot_memory, cache_key, result, ttl_seconds=180)
            return result

        response = {
            "service": self.service_name,
            "tracking_id": tracking_id,
            "logistics_context": context.model_dump(),
            "issues": issues,
        }
        await cache_write(self.hot_memory, cache_key, response, ttl_seconds=180)
        return response


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for route issue detection workflows."""
    adapters = get_agent_adapters(agent, build_route_issue_adapters)

    get_logistics_context = mcp_context_tool(
        adapters.logistics.build_logistics_context,
        id_param="tracking_id",
        result_key="logistics_context",
    )

    async def detect_issues(payload: dict[str, Any]) -> dict[str, Any]:
        tracking_id = payload.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}
        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        if not context:
            return {"error": "shipment not found", "tracking_id": tracking_id}
        issues = await adapters.detector.detect(context)
        return {"issues": issues}

    mcp.add_tool("/logistics/route/context", get_logistics_context)
    mcp.add_tool("/logistics/route/issues", detect_issues)


def _route_instructions() -> str:
    return load_prompt_instructions(__file__, "logistics-route-issue-detection")
