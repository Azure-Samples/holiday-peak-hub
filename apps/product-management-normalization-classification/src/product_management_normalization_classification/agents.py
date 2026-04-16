"""Product normalization and classification agent implementation and MCP tool registration."""

from __future__ import annotations

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

from .adapters import ProductNormalizationAdapters, build_normalization_adapters

_ACP_MAPPER = AcpCatalogMapper()


class ProductNormalizationAgent(BaseRetailAgent):
    """Agent that normalizes and classifies product data."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
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
        acp_product = _ACP_MAPPER.to_acp_product(product, availability="unknown")

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
    adapters = get_agent_adapters(agent, build_normalization_adapters)

    async def normalize_product(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        if not product:
            return {"error": "sku not found", "sku": sku}
        normalized = await adapters.normalizer.normalize(product)
        acp_product = _ACP_MAPPER.to_acp_product(product, availability="unknown")
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
    register_crud_tools(mcp)


def _normalization_instructions() -> str:
    return load_prompt_instructions(__file__, "product-management-normalization-classification")
