"""Logistics route issue detection agent implementation and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import (
    get_agent_adapters,
    mcp_context_tool,
    register_crud_tools,
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

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        tracking_id = request.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}

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
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "tracking_id": tracking_id,
            "logistics_context": context.model_dump(),
            "issues": issues,
        }


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
    register_crud_tools(mcp)


def _route_instructions() -> str:
    return load_prompt_instructions(__file__, "logistics-route-issue-detection")
