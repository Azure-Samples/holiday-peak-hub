"""Logistics returns support agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import ReturnsSupportAdapters, build_returns_support_adapters


class ReturnsSupportAgent(BaseRetailAgent):
    """Agent that provides returns support guidance."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_returns_support_adapters()

    @property
    def adapters(self) -> ReturnsSupportAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        tracking_id = request.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}

        context = await self.adapters.logistics.build_logistics_context(str(tracking_id))
        if not context:
            return {"error": "shipment not found", "tracking_id": tracking_id}

        plan = await self.adapters.assistant.build_returns_plan(context)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _returns_instructions()},
                {
                    "role": "user",
                    "content": {
                        "tracking_id": tracking_id,
                        "logistics_context": context.model_dump(),
                        "returns_plan": plan,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "tracking_id": tracking_id,
            "logistics_context": context.model_dump(),
            "returns_plan": plan,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for returns support workflows."""
    adapters = getattr(agent, "adapters", build_returns_support_adapters())

    async def get_logistics_context(payload: dict[str, Any]) -> dict[str, Any]:
        tracking_id = payload.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}
        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        return {"logistics_context": context.model_dump() if context else None}

    async def get_returns_plan(payload: dict[str, Any]) -> dict[str, Any]:
        tracking_id = payload.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}
        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        if not context:
            return {"error": "shipment not found", "tracking_id": tracking_id}
        plan = await adapters.assistant.build_returns_plan(context)
        return {"returns_plan": plan}

    mcp.add_tool("/logistics/returns/context", get_logistics_context)
    mcp.add_tool("/logistics/returns/plan", get_returns_plan)


def _returns_instructions() -> str:
    return (
        "You are a logistics returns support agent. "
        "Summarize eligibility and next steps for returns. "
        "Highlight policy constraints and risks."
    )
