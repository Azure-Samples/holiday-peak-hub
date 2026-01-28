"""Assortment optimization agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

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

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _assortment_instructions()},
                {
                    "role": "user",
                    "content": {
                        "skus": skus,
                        "products": [p.model_dump() for p in products],
                        "assortment": recommendations,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "skus": skus,
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
        scored = await adapters.optimizer.score_products(products)
        return {"scores": scored}

    async def recommend_assortment(payload: dict[str, Any]) -> dict[str, Any]:
        skus = [str(sku) for sku in payload.get("skus", [])]
        if not skus:
            return {"error": "skus is required"}
        products = [p for p in [await adapters.products.get_product(sku) for sku in skus] if p]
        target_size = int(payload.get("target_size", 5))
        recommendations = await adapters.optimizer.recommend_assortment(
            products, target_size=target_size
        )
        return {"assortment": recommendations}

    mcp.add_tool("/assortment/score", score_products)
    mcp.add_tool("/assortment/recommendations", recommend_assortment)


def _assortment_instructions() -> str:
    return (
        "You are an assortment optimization agent. "
        "Rank products by performance indicators and recommend the ideal set. "
        "Explain trade-offs and highlight missing signals."
    )
