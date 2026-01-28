"""Cart intelligence agent implementation and MCP tool registration."""
from __future__ import annotations

import asyncio
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import CartAdapters, build_cart_adapters


class CartIntelligenceAgent(BaseRetailAgent):
    """Agent that provides cart intelligence and abandonment prevention insights."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_cart_adapters()

    @property
    def adapters(self) -> CartAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        items = _coerce_cart_items(request.get("items"))
        user_id = request.get("user_id")
        related_limit = int(request.get("related_limit", 3))
        price_limit = int(request.get("price_limit", 5))

        product_tasks = [
            self.adapters.products.build_product_context(item["sku"], related_limit=related_limit)
            for item in items
        ]
        pricing_tasks = [
            self.adapters.pricing.build_price_context(item["sku"], limit=price_limit)
            for item in items
        ]
        inventory_tasks = [
            self.adapters.inventory.build_inventory_context(item["sku"])
            for item in items
        ]

        product_contexts, pricing_contexts, inventory_contexts = await asyncio.gather(
            asyncio.gather(*product_tasks),
            asyncio.gather(*pricing_tasks),
            asyncio.gather(*inventory_tasks),
        )

        risk = await self.adapters.analytics.estimate_abandonment_risk(
            items, inventory=inventory_contexts, pricing=pricing_contexts
        )

        if self.hot_memory and user_id:
            await self.hot_memory.set(
                key=f"cart:{user_id}",
                value={"items": items, "risk": risk},
                ttl_seconds=int(request.get("cart_ttl", 600)),
            )

        if self.slm or self.llm:
            messages = [
                {
                    "role": "system",
                    "content": _cart_instructions(self.service_name or "cart"),
                },
                {
                    "role": "user",
                    "content": {
                        "items": items,
                        "product_contexts": [ctx.model_dump() if ctx else None for ctx in product_contexts],
                        "pricing_contexts": [ctx.model_dump() for ctx in pricing_contexts],
                        "inventory_contexts": [ctx.model_dump() if ctx else None for ctx in inventory_contexts],
                        "abandonment_risk": risk,
                        "user_id": user_id,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "items": items,
            "product_contexts": [ctx.model_dump() if ctx else None for ctx in product_contexts],
            "pricing_contexts": [ctx.model_dump() for ctx in pricing_contexts],
            "inventory_contexts": [ctx.model_dump() if ctx else None for ctx in inventory_contexts],
            "abandonment_risk": risk,
            "insight": "Cart intelligence stub response.",
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for cart intelligence workflows."""
    adapters = getattr(agent, "adapters", build_cart_adapters())

    async def get_cart_context(payload: dict[str, Any]) -> dict[str, Any]:
        items = _coerce_cart_items(payload.get("items"))
        related_limit = int(payload.get("related_limit", 3))
        price_limit = int(payload.get("price_limit", 5))

        product_contexts, pricing_contexts, inventory_contexts = await asyncio.gather(
            asyncio.gather(
                *[
                    adapters.products.build_product_context(item["sku"], related_limit=related_limit)
                    for item in items
                ]
            ),
            asyncio.gather(
                *[
                    adapters.pricing.build_price_context(item["sku"], limit=price_limit)
                    for item in items
                ]
            ),
            asyncio.gather(
                *[adapters.inventory.build_inventory_context(item["sku"]) for item in items]
            ),
        )
        return {
            "items": items,
            "product_contexts": [ctx.model_dump() if ctx else None for ctx in product_contexts],
            "pricing_contexts": [ctx.model_dump() for ctx in pricing_contexts],
            "inventory_contexts": [ctx.model_dump() if ctx else None for ctx in inventory_contexts],
        }

    async def estimate_abandonment_risk(payload: dict[str, Any]) -> dict[str, Any]:
        items = _coerce_cart_items(payload.get("items"))
        pricing_contexts = await asyncio.gather(
            *[adapters.pricing.build_price_context(item["sku"]) for item in items]
        )
        inventory_contexts = await asyncio.gather(
            *[adapters.inventory.build_inventory_context(item["sku"]) for item in items]
        )
        risk = await adapters.analytics.estimate_abandonment_risk(
            items, inventory=inventory_contexts, pricing=pricing_contexts
        )
        return {"items": items, "abandonment_risk": risk}

    async def recommend_actions(payload: dict[str, Any]) -> dict[str, Any]:
        items = _coerce_cart_items(payload.get("items"))
        pricing_contexts = await asyncio.gather(
            *[adapters.pricing.build_price_context(item["sku"]) for item in items]
        )
        inventory_contexts = await asyncio.gather(
            *[adapters.inventory.build_inventory_context(item["sku"]) for item in items]
        )
        risk = await adapters.analytics.estimate_abandonment_risk(
            items, inventory=inventory_contexts, pricing=pricing_contexts
        )
        actions = ["send reminder", "offer limited-time discount", "highlight low stock"]
        return {"items": items, "abandonment_risk": risk, "recommended_actions": actions}

    mcp.add_tool("/cart/context", get_cart_context)
    mcp.add_tool("/cart/abandonment-risk", estimate_abandonment_risk)
    mcp.add_tool("/cart/recommendations", recommend_actions)


def _coerce_cart_items(raw_items: Any) -> list[dict[str, object]]:
    if not raw_items:
        return []
    items: list[dict[str, object]] = []
    for entry in raw_items:
        if isinstance(entry, dict) and "sku" in entry:
            items.append({"sku": str(entry.get("sku")), "quantity": int(entry.get("quantity", 1))})
    return items


def _cart_instructions(service_name: str) -> str:
    return (
        f"You are the {service_name} agent. "
        "Be proactive on every request tied to cart evaluation and abandonment prevention. "
        "Use product, pricing, and inventory context to summarize cart health, "
        "flag risks, and recommend next actions to improve conversion. "
        "Always include a monitoring note: what to track next (e.g., stock levels, "
        "promotion uptake, or segment risk), and any anomalies to watch. "
        "If data is missing, call it out and propose safe assumptions."
    )
