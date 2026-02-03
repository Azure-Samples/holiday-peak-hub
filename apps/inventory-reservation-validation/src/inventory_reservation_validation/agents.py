"""Inventory reservation validation agent implementation and MCP tool registration."""
from __future__ import annotations

import os
from typing import Any

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import (
    ReservationValidationAdapters,
    build_reservation_validation_adapters,
    register_external_api_tools,
)


class ReservationValidationAgent(BaseRetailAgent):
    """Agent that validates inventory reservations."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_reservation_validation_adapters()

    @property
    def adapters(self) -> ReservationValidationAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}

        request_qty = int(request.get("request_qty", 1))
        context = await self.adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}

        validation = await self.adapters.validator.validate(
            context, request_qty=request_qty
        )

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _reservation_instructions()},
                {
                    "role": "user",
                    "content": {
                        "sku": sku,
                        "inventory_context": context.model_dump(),
                        "reservation_validation": validation,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "sku": sku,
            "inventory_context": context.model_dump(),
            "reservation_validation": validation,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for reservation validation workflows."""
    adapters = getattr(agent, "adapters", build_reservation_validation_adapters())

    async def get_inventory_context(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        context = await adapters.inventory.build_inventory_context(str(sku))
        return {"inventory_context": context.model_dump() if context else None}

    async def validate_reservation(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        request_qty = int(payload.get("request_qty", 1))
        context = await adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}
        validation = await adapters.validator.validate(context, request_qty=request_qty)
        return {"reservation_validation": validation}

    mcp.add_tool("/inventory/reservations/context", get_inventory_context)
    mcp.add_tool("/inventory/reservations/validate", validate_reservation)
    _register_crud_tools(mcp)
    register_external_api_tools(mcp)


def _register_crud_tools(mcp: FastAPIMCPServer) -> None:
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def _reservation_instructions() -> str:
    return (
        "You are an inventory reservation validation agent. "
        "Validate requested quantities and suggest alternatives when stock is low. "
        "Provide a clear approval decision and backorder details."
    )
