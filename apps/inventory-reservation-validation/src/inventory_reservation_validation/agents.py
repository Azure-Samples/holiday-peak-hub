"""Inventory reservation validation agent implementation and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.memory import (
    CacheConfig,
    cache_write,
    inject_session_id,
    resolve_cache_key,
    try_cache_read,
)
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import (
    get_agent_adapters,
    mcp_context_tool,
)

from .adapters import (
    ReservationValidationAdapters,
    build_reservation_validation_adapters,
    register_external_api_tools,
)


class ReservationValidationAgent(BaseRetailAgent):
    """Agent that validates inventory reservations."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_reservation_validation_adapters()

    @property
    def adapters(self) -> ReservationValidationAdapters:
        return self._adapters

    _cache_config = CacheConfig(
        service="inventory-reservation-validation",
        entity_prefix="reservation",
        ttl_seconds=120,
        entity_key_field="sku",
        fallback_entity_fields=("reservation_id",),
    )

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}

        cache_key = resolve_cache_key(request, self._cache_config)
        cached = await try_cache_read(self.hot_memory, cache_key, ttl_seconds=120)
        if cached is not None:
            return cached

        request_qty = int(request.get("request_qty", 1))
        context = await self.adapters.inventory.build_inventory_context(str(sku))
        if not context:
            return {"error": "sku not found", "sku": sku}

        validation = await self.adapters.validator.validate(context, request_qty=request_qty)

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
            result = await self.invoke_model(
                request=inject_session_id(request, self._cache_config), messages=messages
            )
            await cache_write(self.hot_memory, cache_key, result, ttl_seconds=120)
            return result

        response = {
            "service": self.service_name,
            "sku": sku,
            "inventory_context": context.model_dump(),
            "reservation_validation": validation,
        }
        await cache_write(self.hot_memory, cache_key, response, ttl_seconds=120)
        return response


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for reservation validation workflows."""
    adapters = get_agent_adapters(agent, build_reservation_validation_adapters)

    get_inventory_context = mcp_context_tool(
        adapters.inventory.build_inventory_context,
        id_param="sku",
        result_key="inventory_context",
    )

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
    register_external_api_tools(mcp)


def _reservation_instructions() -> str:
    return load_prompt_instructions(__file__, "inventory-reservation-validation")
