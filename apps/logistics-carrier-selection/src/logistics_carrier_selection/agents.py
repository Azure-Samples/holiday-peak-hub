"""Logistics carrier selection agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import CarrierSelectionAdapters, build_carrier_selection_adapters


class CarrierSelectionAgent(BaseRetailAgent):
    """Agent that recommends a carrier for a shipment."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_carrier_selection_adapters()

    @property
    def adapters(self) -> CarrierSelectionAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        tracking_id = request.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}

        context = await self.adapters.logistics.build_logistics_context(str(tracking_id))
        if not context:
            return {"error": "shipment not found", "tracking_id": tracking_id}

        recommendation = await self.adapters.selector.select(context)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _carrier_instructions()},
                {
                    "role": "user",
                    "content": {
                        "tracking_id": tracking_id,
                        "shipment": context.model_dump(),
                        "recommendation": recommendation,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "tracking_id": tracking_id,
            "shipment": context.model_dump(),
            "recommendation": recommendation,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for carrier selection workflows."""
    adapters = getattr(agent, "adapters", build_carrier_selection_adapters())

    async def get_logistics_context(payload: dict[str, Any]) -> dict[str, Any]:
        tracking_id = payload.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}
        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        return {"logistics_context": context.model_dump() if context else None}

    async def get_carrier_recommendation(payload: dict[str, Any]) -> dict[str, Any]:
        tracking_id = payload.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}
        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        if not context:
            return {"error": "shipment not found", "tracking_id": tracking_id}
        recommendation = await adapters.selector.select(context)
        return {"recommendation": recommendation}

    mcp.add_tool("/logistics/carrier/context", get_logistics_context)
    mcp.add_tool("/logistics/carrier/recommendation", get_carrier_recommendation)


def _carrier_instructions() -> str:
    return (
        "You are a logistics carrier selection agent. "
        "Recommend the best carrier based on service level and constraints. "
        "Explain trade-offs and risks."
    )
