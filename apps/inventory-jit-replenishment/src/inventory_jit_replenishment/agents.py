"""Inventory JIT replenishment agent implementation and MCP tool registration."""

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

from .adapters import InventoryReplenishmentAdapters, build_replenishment_adapters


class InventoryReplenishmentAgent(BaseRetailAgent):
    """Agent that recommends just-in-time replenishment actions."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_replenishment_adapters()

    @property
    def adapters(self) -> InventoryReplenishmentAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}

        target_stock = int(request.get("target_stock", 20))
        context = await self.adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}

        plan = await self.adapters.planner.build_replenishment_plan(
            context, target_stock=target_stock
        )

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _replenishment_instructions()},
                {
                    "role": "user",
                    "content": {
                        "sku": sku,
                        "inventory_context": context.model_dump(),
                        "replenishment_plan": plan,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "sku": sku,
            "inventory_context": context.model_dump(),
            "replenishment_plan": plan,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for JIT replenishment workflows."""
    adapters = get_agent_adapters(agent, build_replenishment_adapters)

    get_inventory_context = mcp_context_tool(
        adapters.inventory.build_inventory_context,
        id_param="sku",
        result_key="inventory_context",
    )

    async def get_replenishment_plan(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        target_stock = int(payload.get("target_stock", 20))
        context = await adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}
        plan = await adapters.planner.build_replenishment_plan(context, target_stock=target_stock)
        return {"replenishment_plan": plan}

    mcp.add_tool("/inventory/replenishment/context", get_inventory_context)
    mcp.add_tool("/inventory/replenishment/plan", get_replenishment_plan)
    register_crud_tools(mcp)


def _replenishment_instructions() -> str:
    return load_prompt_instructions(__file__, "inventory-jit-replenishment")
