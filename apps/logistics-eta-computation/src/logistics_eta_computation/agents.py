"""Logistics ETA computation agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import EtaComputationAdapters, build_eta_adapters


class EtaComputationAgent(BaseRetailAgent):
    """Agent that computes updated ETA for shipments."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_eta_adapters()

    @property
    def adapters(self) -> EtaComputationAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        tracking_id = request.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}

        context = await self.adapters.logistics.build_logistics_context(str(tracking_id))
        if not context:
            return {"error": "shipment not found", "tracking_id": tracking_id}

        eta = await self.adapters.estimator.compute_eta(context)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _eta_instructions()},
                {
                    "role": "user",
                    "content": {
                        "tracking_id": tracking_id,
                        "logistics_context": context.model_dump(),
                        "eta": eta,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "tracking_id": tracking_id,
            "logistics_context": context.model_dump(),
            "eta": eta,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for ETA computation workflows."""
    adapters = getattr(agent, "adapters", build_eta_adapters())

    async def get_logistics_context(payload: dict[str, Any]) -> dict[str, Any]:
        tracking_id = payload.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}
        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        return {"logistics_context": context.model_dump() if context else None}

    async def get_eta(payload: dict[str, Any]) -> dict[str, Any]:
        tracking_id = payload.get("tracking_id")
        if not tracking_id:
            return {"error": "tracking_id is required"}
        context = await adapters.logistics.build_logistics_context(str(tracking_id))
        if not context:
            return {"error": "shipment not found", "tracking_id": tracking_id}
        eta = await adapters.estimator.compute_eta(context)
        return {"eta": eta}

    mcp.add_tool("/logistics/eta/context", get_logistics_context)
    mcp.add_tool("/logistics/eta", get_eta)


def _eta_instructions() -> str:
    return (
        "You are a logistics ETA computation agent. "
        "Provide the most accurate ETA and explain confidence level. "
        "Highlight delays and risk factors."
    )
