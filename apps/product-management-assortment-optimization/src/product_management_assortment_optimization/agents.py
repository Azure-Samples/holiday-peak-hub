"""Assortment optimization agent implementation and MCP tool registration."""

from __future__ import annotations

import os
from typing import Any

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import AssortmentAdapters, build_assortment_adapters


class AssortmentOptimizationAgent(BaseRetailAgent):
    """Agent that ranks products for assortment decisions."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_assortment_adapters()

    @property
    def adapters(self) -> AssortmentAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        skus = [str(sku) for sku in request.get("skus", [])]
        target_size = int(request.get("target_size", 5))
        if not skus:
            return {"error": "skus is required"}

        products = []
        for sku in skus:
            product = await self.adapters.products.get_product(sku)
            if product:
                products.append(product)

        if not products:
            return {"error": "no products found", "skus": skus}

        recommendations = await self.adapters.optimizer.recommend_assortment(
            products, target_size=target_size
        )
        mapper = AcpCatalogMapper()
        acp_products = [
            mapper.to_acp_product(product, availability="unknown") for product in products
        ]

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _assortment_instructions()},
                {
                    "role": "user",
                    "content": {
                        "skus": skus,
                        "products": [p.model_dump() for p in products],
                        "acp_products": acp_products,
                        "assortment": recommendations,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "skus": skus,
            "acp_products": acp_products,
            "assortment": recommendations,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for assortment optimization workflows."""
    adapters = getattr(agent, "adapters", build_assortment_adapters())

    async def score_products(payload: dict[str, Any]) -> dict[str, Any]:
        skus = [str(sku) for sku in payload.get("skus", [])]
        if not skus:
            return {"error": "skus is required"}
        products = [p for p in [await adapters.products.get_product(sku) for sku in skus] if p]
        mapper = AcpCatalogMapper()
        scored = await adapters.optimizer.score_products(products)
        acp_products = [
            mapper.to_acp_product(product, availability="unknown") for product in products
        ]
        return {"scores": scored, "acp_products": acp_products}

    async def recommend_assortment(payload: dict[str, Any]) -> dict[str, Any]:
        skus = [str(sku) for sku in payload.get("skus", [])]
        if not skus:
            return {"error": "skus is required"}
        products = [p for p in [await adapters.products.get_product(sku) for sku in skus] if p]
        target_size = int(payload.get("target_size", 5))
        mapper = AcpCatalogMapper()
        recommendations = await adapters.optimizer.recommend_assortment(
            products, target_size=target_size
        )
        acp_products = [
            mapper.to_acp_product(product, availability="unknown") for product in products
        ]
        return {"assortment": recommendations, "acp_products": acp_products}

    mcp.add_tool("/assortment/score", score_products)
    mcp.add_tool("/assortment/recommendations", recommend_assortment)
    _register_crud_tools(mcp)


def _register_crud_tools(mcp: FastAPIMCPServer) -> None:
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def _assortment_instructions() -> str:
    return (
        "You are an assortment optimization agent. "
        "Rank products by performance indicators and recommend the ideal set. "
        "Explain trade-offs and highlight missing signals."
    )
