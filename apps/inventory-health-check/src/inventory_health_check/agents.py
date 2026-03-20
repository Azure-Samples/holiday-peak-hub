"""Inventory health check agent implementation and MCP tool registration."""

from __future__ import annotations

import os
from typing import Any

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions

from .adapters import InventoryHealthAdapters, build_inventory_health_adapters


class InventoryHealthAgent(BaseRetailAgent):
    """Agent that checks inventory health and anomalies."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_inventory_health_adapters()

    @property
    def adapters(self) -> InventoryHealthAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}

        context = await self.adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}

        health = await self.adapters.analytics.evaluate_health(context)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _health_instructions()},
                {
                    "role": "user",
                    "content": {
                        "sku": sku,
                        "inventory_context": context.model_dump(),
                        "health": health,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "sku": sku,
            "inventory_context": context.model_dump(),
            "health": health,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for inventory health workflows."""
    adapters = getattr(agent, "adapters", build_inventory_health_adapters())

    async def get_inventory_context(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        context = await adapters.inventory.build_inventory_context(str(sku))
        return {"inventory_context": context.model_dump() if context else None}

    async def get_health(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        context = await adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}
        health = await adapters.analytics.evaluate_health(context)
        return {"health": health}

    mcp.add_tool("/inventory/health/context", get_inventory_context)
    mcp.add_tool("/inventory/health", get_health)
    _register_crud_tools(mcp)


def _register_crud_tools(mcp: FastAPIMCPServer) -> None:
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def _health_instructions() -> str:
    return load_prompt_instructions(__file__, "inventory-health-check")
