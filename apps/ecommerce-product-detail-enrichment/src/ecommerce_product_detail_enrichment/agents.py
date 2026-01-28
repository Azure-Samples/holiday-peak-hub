"""Product detail enrichment agent implementation and MCP tool registration."""
from __future__ import annotations

import asyncio
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import EnrichmentAdapters, build_enrichment_adapters, merge_product_enrichment


class ProductDetailEnrichmentAgent(BaseRetailAgent):
    """Agent that enriches product detail pages."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_enrichment_adapters()

    @property
    def adapters(self) -> EnrichmentAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        related_limit = int(request.get("related_limit", 4))
        if not sku:
            return {"error": "sku is required"}

        product_task = self.adapters.products.get_product(str(sku))
        related_task = self.adapters.products.get_related(str(sku), limit=related_limit)
        inventory_task = self.adapters.inventory.build_inventory_context(str(sku))
        acp_task = self.adapters.acp.get_content(str(sku))
        review_task = self.adapters.reviews.get_summary(str(sku))

        product, related, inventory, acp_content, review_summary = await asyncio.gather(
            product_task,
            related_task,
            inventory_task,
            acp_task,
            review_task,
        )

        enriched = merge_product_enrichment(product, acp_content, review_summary)
        enriched["inventory"] = inventory.model_dump() if inventory else None
        enriched["related"] = [item.model_dump() for item in related]

        if self.hot_memory:
            await self.hot_memory.set(
                key=f"pdp:{sku}",
                value=enriched,
                ttl_seconds=int(request.get("cache_ttl", 300)),
            )

        if self.slm or self.llm:
            messages = [
                {
                    "role": "system",
                    "content": _enrichment_instructions(self.service_name or "product detail"),
                },
                {
                    "role": "user",
                    "content": {
                        "sku": sku,
                        "enriched": enriched,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return enriched


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for product detail enrichment workflows."""
    adapters = getattr(agent, "adapters", build_enrichment_adapters())

    async def get_product_details(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        related = await adapters.products.get_related(str(sku), limit=int(payload.get("related_limit", 4)))
        inventory = await adapters.inventory.build_inventory_context(str(sku))
        acp_content = await adapters.acp.get_content(str(sku))
        review_summary = await adapters.reviews.get_summary(str(sku))
        enriched = merge_product_enrichment(product, acp_content, review_summary)
        enriched["inventory"] = inventory.model_dump() if inventory else None
        enriched["related"] = [item.model_dump() for item in related]
        return {"enriched_product": enriched}

    async def get_similar_products(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        related = await adapters.products.get_related(str(sku), limit=int(payload.get("limit", 4)))
        return {"sku": sku, "related": [item.model_dump() for item in related]}

    mcp.add_tool("/product/detail", get_product_details)
    mcp.add_tool("/product/similar", get_similar_products)


def _enrichment_instructions(service_name: str) -> str:
    return (
        f"You are the {service_name} agent. "
        "Be proactive when enriching product details. "
        "Combine catalog, ACP content, reviews, and inventory into a concise summary. "
        "Highlight anything that could impact conversion (low stock, missing media, low ratings). "
        "Always include a monitoring note: which signals to track next (e.g., stock, ratings, "
        "content completeness) and any anomalies to watch."
    )
