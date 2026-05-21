"""Inventory health check agent implementation and MCP tool registration."""

from __future__ import annotations

import re
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.memory import (
    CacheConfig,
    inject_session_id,
    resolve_cache_key,
    try_cache_read,
)
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import (
    get_agent_adapters,
    mcp_context_tool,
)

from .adapters import InventoryHealthAdapters, build_inventory_health_adapters

# Pattern: capture SKU identifiers from natural-language Responses protocol
# inputs (e.g. "check health of SKU-123", "is sku ABC-9 healthy?"). Two
# alternations: (a) explicit "SKU-XYZ" tokens, (b) "sku <id>" prefixed forms.
_SKU_PATTERN_TEXT = (
    r"\b(?:SKU[-_]?)([A-Z0-9][A-Z0-9_-]{1,63})\b" + r"|\bsku\s+([A-Z0-9][A-Z0-9_-]{1,63})\b"
)
_SKU_PATTERN = re.compile(_SKU_PATTERN_TEXT, re.IGNORECASE)


class InventoryHealthAgent(BaseRetailAgent):
    """Agent that checks inventory health and anomalies."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_inventory_health_adapters()

    @property
    def adapters(self) -> InventoryHealthAdapters:
        return self._adapters

    _cache_config = CacheConfig(
        service="inventory-health-check",
        entity_prefix="health",
        ttl_seconds=120,
        entity_key_field="sku",
    )

    async def responses_request_from_text(self, text: str) -> dict[str, Any]:
        """Translate Responses-API free-form input into a ``handle()``
        request dict.

        ``handle()`` requires a ``sku`` field. We try to extract one from
        natural-language inputs ("check health for SKU-123", "is sku ABC9
        healthy?"). When no SKU can be found we still fan the call out to
        ``handle()`` with an explanatory error so the caller (and the
        Responses-API surface) sees a structured reply rather than a 500.
        """
        match = _SKU_PATTERN.search(text or "")
        if match:
            sku = (match.group(1) or match.group(2) or "").upper()
            return {"sku": sku, "_responses_input_text": text}
        # No SKU found — surface a structured prompt back to the caller.
        return {
            "_no_sku": True,
            "_responses_input_text": text,
            "sku": None,
        }

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        if request.get("_no_sku"):
            return {
                "error": "sku is required",
                "hint": ("Provide a SKU id in the prompt, e.g. " "'check health for SKU-1234'."),
                "input": request.get("_responses_input_text"),
            }

        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}

        cache_key = resolve_cache_key(request, self._cache_config)
        cached = await try_cache_read(self.hot_memory, cache_key, ttl_seconds=120)
        if cached is not None:
            return cached

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
            result = await self.invoke_model(
                request=inject_session_id(request, self._cache_config), messages=messages
            )
            self.background_cache_write(cache_key, result, ttl_seconds=120)
            return result

        response = {
            "service": self.service_name,
            "sku": sku,
            "inventory_context": context.model_dump(),
            "health": health,
        }
        self.background_cache_write(cache_key, response, ttl_seconds=120)
        return response


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for inventory health workflows."""
    adapters = get_agent_adapters(agent, build_inventory_health_adapters)

    get_inventory_context = mcp_context_tool(
        adapters.inventory.build_inventory_context,
        id_param="sku",
        result_key="inventory_context",
    )

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


def _health_instructions() -> str:
    return load_prompt_instructions(__file__, "inventory-health-check")
