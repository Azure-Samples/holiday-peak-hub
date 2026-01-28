"""Product consistency validation agent implementation and MCP tool registration."""
from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import ProductConsistencyAdapters, build_consistency_adapters


class ProductConsistencyAgent(BaseRetailAgent):
    """Agent that validates catalog product consistency."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_consistency_adapters()

    @property
    def adapters(self) -> ProductConsistencyAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await self.adapters.products.get_product(str(sku))
        if not product:
            return {"error": "sku not found", "sku": sku}

        validation = await self.adapters.validator.validate(product)

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _consistency_instructions()},
                {
                    "role": "user",
                    "content": {
                        "sku": sku,
                        "product": product.model_dump(),
                        "validation": validation,
                    },
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {
            "service": self.service_name,
            "sku": sku,
            "product": product.model_dump(),
            "validation": validation,
        }


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for product consistency validation workflows."""
    adapters = getattr(agent, "adapters", build_consistency_adapters())

    async def validate_product(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        if not product:
            return {"error": "sku not found", "sku": sku}
        validation = await adapters.validator.validate(product)
        return {"validation": validation}

    async def get_product(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        product = await adapters.products.get_product(str(sku))
        return {"product": product.model_dump() if product else None}

    mcp.add_tool("/product/consistency/check", validate_product)
    mcp.add_tool("/product/consistency/product", get_product)


def _consistency_instructions() -> str:
    return (
        "You are a product consistency validation agent. "
        "Check catalog completeness and highlight missing fields. "
        "Provide remediation steps for invalid items."
    )
