"""Inventory alerts agent implementation and MCP tool registration."""

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

from .adapters import InventoryAlertsAdapters, build_inventory_alerts_adapters


class InventoryAlertsAgent(BaseRetailAgent):
    """Agent that detects inventory alerts and trigger conditions."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_inventory_alerts_adapters()

    @property
    def adapters(self) -> InventoryAlertsAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}
        threshold = int(request.get("threshold", 5))

        context = await self.adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}

        alerts = await self.adapters.analytics.build_alerts(context, threshold=threshold)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _alerts_instructions()},
                {
                    "role": "user",
                    "content": {
                        "sku": sku,
                        "inventory_context": context.model_dump(),
                        "alerts": alerts,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "sku": sku,
            "inventory_context": context.model_dump(),
            "alerts": alerts,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for inventory alert workflows."""
    adapters = get_agent_adapters(agent, build_inventory_alerts_adapters)

    get_inventory_context = mcp_context_tool(
        adapters.inventory.build_inventory_context,
        id_param="sku",
        result_key="inventory_context",
    )

    async def get_alerts(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        context = await adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}
        threshold = int(payload.get("threshold", 5))
        alerts = await adapters.analytics.build_alerts(context, threshold=threshold)
        return {"alerts": alerts}

    mcp.add_tool("/inventory/alerts/context", get_inventory_context)
    mcp.add_tool("/inventory/alerts", get_alerts)
    register_crud_tools(mcp)


def _alerts_instructions() -> str:
    return load_prompt_instructions(__file__, "inventory-alerts-triggers")
