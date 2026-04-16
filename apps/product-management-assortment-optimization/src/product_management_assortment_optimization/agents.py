"""Assortment optimization agent implementation and MCP tool registration."""

from __future__ import annotations

import asyncio
from typing import Any

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import (
    get_agent_adapters,
    register_crud_tools,
)

from .adapters import AssortmentAdapters, build_assortment_adapters

_ACP_MAPPER = AcpCatalogMapper()


class AssortmentOptimizationAgent(BaseRetailAgent):
    """Agent that ranks products for assortment decisions."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
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

        fetched = await asyncio.gather(*(self.adapters.products.get_product(sku) for sku in skus))
        products = [p for p in fetched if p]

        if not products:
            return {"error": "no products found", "skus": skus}

        recommendations = await self.adapters.optimizer.recommend_assortment(
            products, target_size=target_size
        )
        acp_products = [
            _ACP_MAPPER.to_acp_product(product, availability="unknown") for product in products
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
    adapters = get_agent_adapters(agent, build_assortment_adapters)

    async def score_products(payload: dict[str, Any]) -> dict[str, Any]:
        skus = [str(sku) for sku in payload.get("skus", [])]
        if not skus:
            return {"error": "skus is required"}
        fetched = await asyncio.gather(*(adapters.products.get_product(sku) for sku in skus))
        products = [p for p in fetched if p]
        scored = await adapters.optimizer.score_products(products)
        acp_products = [
            _ACP_MAPPER.to_acp_product(product, availability="unknown") for product in products
        ]
        return {"scores": scored, "acp_products": acp_products}

    async def recommend_assortment(payload: dict[str, Any]) -> dict[str, Any]:
        skus = [str(sku) for sku in payload.get("skus", [])]
        if not skus:
            return {"error": "skus is required"}
        fetched = await asyncio.gather(*(adapters.products.get_product(sku) for sku in skus))
        products = [p for p in fetched if p]
        target_size = int(payload.get("target_size", 5))
        recommendations = await adapters.optimizer.recommend_assortment(
            products, target_size=target_size
        )
        acp_products = [
            _ACP_MAPPER.to_acp_product(product, availability="unknown") for product in products
        ]
        return {"assortment": recommendations, "acp_products": acp_products}

    mcp.add_tool("/assortment/score", score_products)
    mcp.add_tool("/assortment/recommendations", recommend_assortment)
    register_crud_tools(mcp)


def _assortment_instructions() -> str:
    return load_prompt_instructions(__file__, "product-management-assortment-optimization")
