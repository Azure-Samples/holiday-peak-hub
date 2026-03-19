"""Logistics ETA computation agent implementation and MCP tool registration."""

from __future__ import annotations

import os
from typing import Any

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions

from .adapters import (
    EtaComputationAdapters,
    build_eta_adapters,
    register_external_api_tools,
)


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
    _register_crud_tools(mcp)
    register_external_api_tools(mcp)


def _register_crud_tools(mcp: FastAPIMCPServer) -> None:
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def _eta_instructions() -> str:
    return load_prompt_instructions(__file__, "logistics-eta-computation")
