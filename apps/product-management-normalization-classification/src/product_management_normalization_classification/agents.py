"""Product normalization and classification agent implementation and MCP tool registration."""

from __future__ import annotations

import os
from typing import Any

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
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
        acp_product = AcpCatalogMapper().to_acp_product(product, availability="unknown")

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _normalization_instructions()},
                {
                    "role": "user",
                    "content": {
                        "sku": sku,
                        "product": product.model_dump(),
                        "acp_product": acp_product,
                        "normalized": normalized,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "sku": sku,
            "product": product.model_dump(),
            "acp_product": acp_product,
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
        acp_product = AcpCatalogMapper().to_acp_product(product, availability="unknown")
        return {"normalized": normalized, "acp_product": acp_product}

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
    _register_crud_tools(mcp)


def _register_crud_tools(mcp: FastAPIMCPServer) -> None:
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def _normalization_instructions() -> str:
    return (
        "You are a product normalization agent. "
        "Normalize names, categories, and tags, and assign a classification. "
        "Highlight any missing attributes needed for accurate categorization."
    )
