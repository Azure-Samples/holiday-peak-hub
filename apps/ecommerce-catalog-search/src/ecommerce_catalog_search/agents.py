"""Catalog search agent implementation and MCP tool registration (ACP-aware)."""
from __future__ import annotations

import asyncio
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.schemas.product import CatalogProduct

from .adapters import CatalogAdapters, build_catalog_adapters


class CatalogSearchAgent(BaseRetailAgent):
    """Agent that performs ACP-compliant catalog discovery."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_catalog_adapters()

    @property
    def adapters(self) -> CatalogAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        query = request.get("query", "")
        limit = int(request.get("limit", 5))

        products = await _search_products(self.adapters, query=query, limit=limit)
        availability = await _resolve_availability(self.adapters, products)
        acp_products = [
            self.adapters.mapping.to_acp_product(product, availability=availability[idx])
            for idx, product in enumerate(products)
        ]

        if self.slm or self.llm:
            messages = [
                {
                    "role": "system",
                    "content": _catalog_instructions(self.service_name or "catalog"),
                },
                {
                    "role": "user",
                    "content": {
                        "query": query,
                        "results": acp_products,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {"service": self.service_name, "query": query, "results": acp_products}


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for ACP catalog search."""
    adapters = getattr(agent, "adapters", build_catalog_adapters())

    async def search_catalog(payload: dict[str, Any]) -> dict[str, Any]:
        query = payload.get("query", "")
        limit = int(payload.get("limit", 5))
        products = await _search_products(adapters, query=query, limit=limit)
        availability = await _resolve_availability(adapters, products)
        results = [
            adapters.mapping.to_acp_product(product, availability=availability[idx])
            for idx, product in enumerate(products)
        ]
        return {"query": query, "results": results}

    async def get_product_details(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        if product is None:
            return {"error": "not_found", "sku": sku}
        availability = await _availability_for_sku(adapters, product.sku)
        return {
            "product": adapters.mapping.to_acp_product(product, availability=availability),
        }

    mcp.add_tool("/catalog/search", search_catalog)
    mcp.add_tool("/catalog/product", get_product_details)


def _catalog_instructions(service_name: str) -> str:
    return (
        f"You are the {service_name} catalog search agent. "
        "Follow the Agentic Commerce Protocol product feed conventions: "
        "only surface items with required fields populated and accurate availability. "
        "Return ACP-aligned fields (item_id, title, description, url, image_url, price, "
        "availability, eligibility flags, and seller/returns metadata). "
        "If any required field is missing, exclude the item and explain why."
    )


def _coerce_query_to_sku(query: str) -> str:
    if not query:
        return "SKU-1"
    return f"SKU-{abs(hash(query)) % 1000}"


async def _search_products(adapters: CatalogAdapters, *, query: str, limit: int) -> list[CatalogProduct]:
    primary_sku = _coerce_query_to_sku(query)
    primary = await adapters.products.get_product(primary_sku)
    related = await adapters.products.get_related(primary_sku, limit=max(limit - 1, 0))
    products = [p for p in [primary] if p is not None] + related
    return products[:limit]


async def _resolve_availability(
    adapters: CatalogAdapters, products: list[CatalogProduct]
) -> list[str]:
    inventory = await asyncio.gather(
        *[adapters.inventory.get_item(product.sku) for product in products]
    )
    availability: list[str] = []
    for item in inventory:
        if item is None:
            availability.append("unknown")
        elif item.available > 0:
            availability.append("in_stock")
        else:
            availability.append("out_of_stock")
    return availability


async def _availability_for_sku(adapters: CatalogAdapters, sku: str) -> str:
    item = await adapters.inventory.get_item(sku)
    if item is None:
        return "unknown"
    return "in_stock" if item.available > 0 else "out_of_stock"
