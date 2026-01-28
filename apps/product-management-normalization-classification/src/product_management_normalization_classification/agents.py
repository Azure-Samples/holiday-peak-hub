"""Product normalization and classification agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import ProductNormalizationAdapters, build_normalization_adapters


class ProductNormalizationAgent(BaseRetailAgent):
    """Agent that normalizes and classifies product data."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_normalization_adapters()

    @property
    def adapters(self) -> ProductNormalizationAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await self.adapters.products.get_product(str(sku))
        if not product:
            return {"error": "sku not found", "sku": sku}

        normalized = await self.adapters.normalizer.normalize(product)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _normalization_instructions()},
                {
                    "role": "user",
                    "content": {
                        "sku": sku,
                        "product": product.model_dump(),
                        "normalized": normalized,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "sku": sku,
            "product": product.model_dump(),
            "normalized": normalized,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for normalization/classification workflows."""
    adapters = getattr(agent, "adapters", build_normalization_adapters())

    async def normalize_product(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        if not product:
            return {"error": "sku not found", "sku": sku}
        normalized = await adapters.normalizer.normalize(product)
        return {"normalized": normalized}

    async def classify_product(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        if not product:
            return {"error": "sku not found", "sku": sku}
        normalized = await adapters.normalizer.normalize(product)
        return {"classification": normalized.get("classification")}

    mcp.add_tool("/product/normalize", normalize_product)
    mcp.add_tool("/product/classify", classify_product)


def _normalization_instructions() -> str:
    return (
        "You are a product normalization agent. "
        "Normalize names, categories, and tags, and assign a classification. "
        "Highlight any missing attributes needed for accurate categorization."
    )
