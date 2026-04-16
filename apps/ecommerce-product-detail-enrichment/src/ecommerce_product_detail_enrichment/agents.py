"""Product detail enrichment agent implementation and MCP tool registration."""

from __future__ import annotations

import asyncio
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.guardrails import EnrichmentGuardrail
from holiday_peak_lib.agents.memory import (
    build_canonical_memory_key,
    read_hot_with_compatibility,
    resolve_namespace_context,
)
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import (
    get_agent_adapters,
    register_crud_tools,
)

from .adapters import (
    EnrichmentAdapters,
    build_enrichment_adapters,
    merge_product_enrichment,
)


class ProductDetailEnrichmentAgent(BaseRetailAgent):
    """Agent that enriches product detail pages."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_enrichment_adapters()
        self._guardrail = EnrichmentGuardrail()

    @property
    def adapters(self) -> EnrichmentAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        related_limit = int(request.get("related_limit", 4))
        if not sku:
            return {"error": "sku is required"}
        cache_ttl_seconds = int(request.get("cache_ttl", 300))

        namespace_context = resolve_namespace_context(
            request,
            self.service_name or "product-detail-enrichment",
            session_fallback=str(request.get("user_id")) if request.get("user_id") else None,
        )
        canonical_cache_key = build_canonical_memory_key(
            namespace_context,
            f"pdp:{sku}",
        )
        if self.hot_memory:
            await read_hot_with_compatibility(
                self.hot_memory,
                canonical_cache_key,
                [f"pdp:{sku}"],
                ttl_seconds=cache_ttl_seconds,
            )

        enriched = await self._fetch_and_enrich(str(sku), related_limit)
        if "error" in enriched:
            return enriched

        if self.hot_memory:
            await self.hot_memory.set(
                key=canonical_cache_key,
                value=enriched,
                ttl_seconds=cache_ttl_seconds,
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

    async def _fetch_and_enrich(self, sku: str, related_limit: int) -> dict[str, Any]:
        """Fetch product data in parallel, validate via guardrails, and merge enrichment."""
        product, related, inventory, acp_content, review_summary = await asyncio.gather(
            self.adapters.products.get_product(sku),
            self.adapters.products.get_related(sku, limit=related_limit),
            self.adapters.inventory.build_inventory_context(sku),
            self.adapters.acp.get_content(sku),
            self.adapters.reviews.get_summary(sku),
        )

        validation = self._guardrail.validate_sources(product=product, acp_content=acp_content)
        if not validation.is_valid:
            self._guardrail.log_audit(sku, [], rejection_reason=validation.rejection_reason)
            return {"error": "enrichment not available", "reason": validation.rejection_reason}

        self._guardrail.log_audit(sku, validation.source_ids)

        enriched = merge_product_enrichment(product, acp_content, review_summary)
        enriched["inventory"] = inventory.model_dump() if inventory else None
        enriched["related"] = [item.model_dump() for item in related]
        availability = "unknown"
        if inventory and inventory.item.available > 0:
            availability = "in_stock"
        elif inventory:
            availability = "out_of_stock"
        if product:
            enriched["acp_product"] = self.adapters.acp_mapper.to_acp_product(
                product,
                availability=availability,
            )

        return self._guardrail.tag_content(enriched, validation.source_ids)


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for product detail enrichment workflows."""
    adapters = get_agent_adapters(agent, build_enrichment_adapters)

    async def get_product_details(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        related = await adapters.products.get_related(
            str(sku), limit=int(payload.get("related_limit", 4))
        )
        inventory = await adapters.inventory.build_inventory_context(str(sku))
        acp_content = await adapters.acp.get_content(str(sku))
        review_summary = await adapters.reviews.get_summary(str(sku))
        enriched = merge_product_enrichment(product, acp_content, review_summary)
        enriched["inventory"] = inventory.model_dump() if inventory else None
        enriched["related"] = [item.model_dump() for item in related]
        availability = "unknown"
        if inventory and inventory.item.available > 0:
            availability = "in_stock"
        elif inventory:
            availability = "out_of_stock"
        if product:
            enriched["acp_product"] = adapters.acp_mapper.to_acp_product(
                product,
                availability=availability,
            )
        return {"enriched_product": enriched}

    async def get_similar_products(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        related = await adapters.products.get_related(str(sku), limit=int(payload.get("limit", 4)))
        return {"sku": sku, "related": [item.model_dump() for item in related]}

    mcp.add_tool("/product/detail", get_product_details)
    mcp.add_tool("/product/similar", get_similar_products)
    register_crud_tools(mcp)


def _enrichment_instructions(service_name: str) -> str:
    return load_prompt_instructions(__file__, service_name)
