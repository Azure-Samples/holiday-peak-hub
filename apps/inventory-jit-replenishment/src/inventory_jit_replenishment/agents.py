"""Inventory JIT replenishment agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import InventoryReplenishmentAdapters, build_replenishment_adapters


class InventoryReplenishmentAgent(BaseRetailAgent):
    """Agent that recommends just-in-time replenishment actions."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
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
    adapters = getattr(agent, "adapters", build_replenishment_adapters())

    async def get_inventory_context(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        context = await adapters.inventory.build_inventory_context(str(sku))
        return {"inventory_context": context.model_dump() if context else None}

    async def get_replenishment_plan(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        target_stock = int(payload.get("target_stock", 20))
        context = await adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}
        plan = await adapters.planner.build_replenishment_plan(
            context, target_stock=target_stock
        )
        return {"replenishment_plan": plan}

    mcp.add_tool("/inventory/replenishment/context", get_inventory_context)
    mcp.add_tool("/inventory/replenishment/plan", get_replenishment_plan)


def _replenishment_instructions() -> str:
    return (
        "You are an inventory replenishment agent. "
        "Recommend reorder quantities and timing based on availability and demand. "
        "Call out risks to service levels and supplier lead times."
    )
