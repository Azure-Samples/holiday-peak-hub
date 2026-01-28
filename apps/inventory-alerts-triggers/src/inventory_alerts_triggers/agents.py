"""Inventory alerts agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import InventoryAlertsAdapters, build_inventory_alerts_adapters


class InventoryAlertsAgent(BaseRetailAgent):
    """Agent that detects inventory alerts and trigger conditions."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
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
    adapters = getattr(agent, "adapters", build_inventory_alerts_adapters())

    async def get_inventory_context(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        context = await adapters.inventory.build_inventory_context(str(sku))
        return {"inventory_context": context.model_dump() if context else None}

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


def _alerts_instructions() -> str:
    return (
        "You are an inventory alerts agent. "
        "Identify low stock, reservation pressure, and trigger conditions. "
        "Recommend immediate actions (expedite, reallocate, or notify)."
    )
