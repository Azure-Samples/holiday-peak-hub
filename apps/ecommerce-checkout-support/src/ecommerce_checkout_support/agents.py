"""Checkout support agent implementation and MCP tool registration."""
from __future__ import annotations

import asyncio
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import CheckoutAdapters, build_checkout_adapters


class CheckoutSupportAgent(BaseRetailAgent):
    """Agent that validates checkout readiness and suggests fixes."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_checkout_adapters()

    @property
    def adapters(self) -> CheckoutAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        items = _coerce_items(request.get("items"))
        price_tasks = [self.adapters.pricing.build_price_context(item["sku"]) for item in items]
        inventory_tasks = [self.adapters.inventory.build_inventory_context(item["sku"]) for item in items]

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
                        "inventory": [ctx.model_dump() if ctx else None for ctx in inventory_contexts],
                        "validation": validation,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "items": items,
            "pricing": [ctx.model_dump() for ctx in pricing_contexts],
            "inventory": [ctx.model_dump() if ctx else None for ctx in inventory_contexts],
            "validation": validation,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for checkout support workflows."""
    adapters = getattr(agent, "adapters", build_checkout_adapters())

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
        return {"items": items, "validation": validation}

    async def get_pricing(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        pricing = await adapters.pricing.build_price_context(str(sku))
        return {"pricing": pricing.model_dump()}

    async def get_inventory(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        inventory = await adapters.inventory.build_inventory_context(str(sku))
        return {"inventory": inventory.model_dump() if inventory else None}

    mcp.add_tool("/checkout/validate", validate_checkout)
    mcp.add_tool("/checkout/pricing", get_pricing)
    mcp.add_tool("/checkout/inventory", get_inventory)


def _coerce_items(raw_items: Any) -> list[dict[str, object]]:
    if not raw_items:
        return []
    items: list[dict[str, object]] = []
    for entry in raw_items:
        if isinstance(entry, dict) and "sku" in entry:
            items.append({"sku": str(entry.get("sku")), "quantity": int(entry.get("quantity", 1))})
    return items


def _checkout_instructions(service_name: str) -> str:
    return (
        f"You are the {service_name} agent. "
        "Be proactive about checkout readiness. "
        "Validate pricing and availability, summarize blockers, and propose fixes. "
        "Always include a monitoring note: what to track next (e.g., price changes, "
        "stock volatility, or failed validations) and any anomalies to watch."
    )
