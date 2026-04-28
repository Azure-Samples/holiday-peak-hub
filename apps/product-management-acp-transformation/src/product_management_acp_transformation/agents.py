"""Product ACP transformation agent implementation and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.memory import (
    CacheConfig,
    inject_session_id,
    resolve_cache_key,
    try_cache_read,
)
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import get_agent_adapters

from .adapters import AcpTransformationAdapters, build_acp_transformation_adapters


class ProductAcpTransformationAgent(BaseRetailAgent):
    """Agent that transforms catalog products into ACP payloads."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_acp_transformation_adapters()

    @property
    def adapters(self) -> AcpTransformationAdapters:
        return self._adapters

    _cache_config = CacheConfig(
        service="product-management-acp-transformation",
        entity_prefix="acp",
        ttl_seconds=300,
        entity_key_field="sku",
    )

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}

        cache_key = resolve_cache_key(request, self._cache_config)
        cached = await try_cache_read(self.hot_memory, cache_key, ttl_seconds=300)
        if cached is not None:
            return cached
        availability = request.get("availability", "in_stock")
        currency = request.get("currency", "usd")

        product = await self.adapters.products.get_product(str(sku))
        if not product:
            return {"error": "sku not found", "sku": sku}

        acp = self.adapters.mapper.to_acp_product(
            product, availability=str(availability), currency=str(currency)
        )

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _acp_instructions()},
                {
                    "role": "user",
                    "content": {
                        "sku": sku,
                        "product": product.model_dump(),
                        "acp_product": acp,
                    },
                },
            ]
            result = await self.invoke_model(
                request=inject_session_id(request, self._cache_config), messages=messages
            )
            self.background_cache_write(cache_key, result, ttl_seconds=300)
            return result

        response = {
            "service": self.service_name,
            "sku": sku,
            "product": product.model_dump(),
            "acp_product": acp,
        }
        self.background_cache_write(cache_key, response, ttl_seconds=300)
        return response


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for ACP transformation workflows."""
    adapters = get_agent_adapters(agent, build_acp_transformation_adapters)

    async def transform_product(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        if not product:
            return {"error": "sku not found", "sku": sku}
        acp = adapters.mapper.to_acp_product(
            product,
            availability=str(payload.get("availability", "in_stock")),
            currency=str(payload.get("currency", "usd")),
        )
        return {"acp_product": acp}

    async def get_product(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        return {"product": product.model_dump() if product else None}

    mcp.add_tool("/product/acp/transform", transform_product)
    mcp.add_tool("/product/acp/product", get_product)


def _acp_instructions() -> str:
    return load_prompt_instructions(__file__, "product-management-acp-transformation")
