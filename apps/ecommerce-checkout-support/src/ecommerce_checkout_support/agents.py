"""Checkout support agent implementation and MCP tool registration."""

from __future__ import annotations

import asyncio
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
from holiday_peak_lib.agents.registration_helpers import get_agent_adapters

from .adapters import (
    CheckoutAdapters,
    build_checkout_adapters,
    register_external_api_tools,
)


class CheckoutSupportAgent(BaseRetailAgent):
    """Agent that validates checkout readiness and suggests fixes."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_checkout_adapters()

    @property
    def adapters(self) -> CheckoutAdapters:
        return self._adapters

    _cache_config = CacheConfig(
        service="ecommerce-checkout-support",
        entity_prefix="checkout",
        ttl_seconds=120,
        entity_key_field="user_id",
        fallback_entity_fields=("session_id", "sku"),
    )

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        items = _coerce_items(request.get("items"))

        cache_key = resolve_cache_key(request, self._cache_config)
        cached = await try_cache_read(self.hot_memory, cache_key, ttl_seconds=120)
        if cached is not None:
            return cached

        price_tasks = [self.adapters.pricing.build_price_context(item["sku"]) for item in items]
        inventory_tasks = [
            self.adapters.inventory.build_inventory_context(item["sku"]) for item in items
        ]

        pricing_contexts, inventory_contexts = await asyncio.gather(
            asyncio.gather(*price_tasks),
            asyncio.gather(*inventory_tasks),
        )

        validation = await self.adapters.validator.validate(
            items, pricing=pricing_contexts, inventory=inventory_contexts
        )

        if self.slm or self.llm:
            messages = [
                {
                    "role": "system",
                    "content": _checkout_instructions(self.service_name or "checkout"),
                },
                {
                    "role": "user",
                    "content": {
                        "items": items,
                        "pricing": [ctx.model_dump() for ctx in pricing_contexts],
                        "inventory": [
                            ctx.model_dump() if ctx else None for ctx in inventory_contexts
                        ],
                        "validation": validation,
                    },
                },
            ]
            result = await self.invoke_model(
                request=inject_session_id(request, self._cache_config), messages=messages
            )
            self.background_cache_write(cache_key, result, ttl_seconds=120)
            return result

        acp_checkout = _build_acp_checkout_payload(items)

        result = {
            "service": self.service_name,
            "items": items,
            "pricing": [ctx.model_dump() for ctx in pricing_contexts],
            "inventory": [ctx.model_dump() if ctx else None for ctx in inventory_contexts],
            "validation": validation,
            "acp": {
                "acp_version": "0.1",
                "domain": "checkout",
                "checkout": acp_checkout,
            },
        }
        self.background_cache_write(cache_key, result, ttl_seconds=120)
        return result


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for checkout support workflows."""
    adapters = get_agent_adapters(agent, build_checkout_adapters)

    async def validate_checkout(payload: dict[str, Any]) -> dict[str, Any]:
        items = _coerce_items(payload.get("items"))
        pricing_contexts = await asyncio.gather(
            *[adapters.pricing.build_price_context(item["sku"]) for item in items]
        )
        inventory_contexts = await asyncio.gather(
            *[adapters.inventory.build_inventory_context(item["sku"]) for item in items]
        )
        validation = await adapters.validator.validate(
            items, pricing=pricing_contexts, inventory=inventory_contexts
        )
        return {
            "items": items,
            "validation": validation,
            "acp": {
                "acp_version": "0.1",
                "domain": "checkout",
                "checkout": _build_acp_checkout_payload(items),
            },
        }

    async def get_pricing(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        pricing = await adapters.pricing.build_price_context(str(sku))
        return {
            "pricing": pricing.model_dump(),
            "acp": {
                "acp_version": "0.1",
                "domain": "checkout",
                "checkout": {
                    "items": [
                        {
                            "sku": str(sku),
                            "quantity": 1,
                        }
                    ]
                },
            },
        }

    async def get_inventory(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        inventory = await adapters.inventory.build_inventory_context(str(sku))
        return {
            "inventory": inventory.model_dump() if inventory else None,
            "acp": {
                "acp_version": "0.1",
                "domain": "checkout",
                "checkout": {
                    "items": [
                        {
                            "sku": str(sku),
                            "quantity": 1,
                        }
                    ]
                },
            },
        }

    mcp.add_tool("/checkout/validate", validate_checkout)
    mcp.add_tool("/checkout/pricing", get_pricing)
    mcp.add_tool("/checkout/inventory", get_inventory)
    register_external_api_tools(mcp)


def _coerce_items(raw_items: Any) -> list[dict[str, object]]:
    if not raw_items:
        return []
    items: list[dict[str, object]] = []
    for entry in raw_items:
        if isinstance(entry, dict) and "sku" in entry:
            items.append(
                {
                    "sku": str(entry.get("sku")),
                    "quantity": int(entry.get("quantity", 1)),
                }
            )
    return items


def _build_acp_checkout_payload(items: list[dict[str, object]]) -> dict[str, object]:
    return {
        "items": [
            {
                "sku": str(item.get("sku", "")),
                "quantity": int(item.get("quantity", 1)),
            }
            for item in items
        ]
    }


def _checkout_instructions(service_name: str) -> str:
    return load_prompt_instructions(__file__, service_name)
