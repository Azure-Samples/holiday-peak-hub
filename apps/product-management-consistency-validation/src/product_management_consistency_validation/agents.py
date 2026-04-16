"""Product consistency validation agent implementation and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions
from holiday_peak_lib.agents.registration_helpers import (
    get_agent_adapters,
    register_crud_tools,
)

from .adapters import ProductConsistencyAdapters, build_consistency_adapters
from .completeness_engine import CompletenessEngine

_ENGINE = CompletenessEngine()


async def _evaluate_completeness(
    sku: str,
    adapters: ProductConsistencyAdapters,
    category_id: str | None = None,
) -> dict[str, Any]:
    """Shared evaluation logic used by agent and MCP tool."""
    product = await adapters.products.get_product(str(sku))
    if not product:
        return {"error": "sku not found", "sku": sku}

    resolved_category = category_id or product.category or "default"
    schema = await adapters.completeness.get_schema(resolved_category)
    if schema is None:
        return {
            "error": "schema not found",
            "sku": sku,
            "category_id": resolved_category,
        }

    report = _ENGINE.evaluate(str(sku), product.model_dump(), schema)
    await adapters.completeness.store_gap_report(report)

    return {
        "sku": sku,
        "category_id": resolved_category,
        "completeness": report.model_dump(mode="json"),
        "needs_enrichment": bool(report.enrichable_gaps),
    }


class ProductConsistencyAgent(BaseRetailAgent):
    """Agent that evaluates products with the schema-driven completeness engine."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_consistency_adapters()

    @property
    def adapters(self) -> ProductConsistencyAdapters:
        return self._adapters

    async def evaluate_completeness(
        self, sku: str, category_id: str | None = None
    ) -> dict[str, Any]:
        return await _evaluate_completeness(sku, self.adapters, category_id)

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        sku = request.get("sku")
        if not sku:
            return {"error": "sku is required"}

        result = await self.evaluate_completeness(
            sku=str(sku), category_id=request.get("category_id")
        )

        if "error" in result:
            return result

        if self.slm or self.llm:
            messages = [
                {"role": "system", "content": _consistency_instructions()},
                {
                    "role": "user",
                    "content": result,
                },
            ]
            return await self.invoke_model(request=request, messages=messages)

        return {"service": self.service_name, **result}


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for schema-driven completeness workflows."""
    adapters = get_agent_adapters(agent, build_consistency_adapters)

    async def evaluate_product_completeness(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        return await _evaluate_completeness(
            sku=str(sku),
            adapters=adapters,
            category_id=payload.get("category_id"),
        )

    mcp.add_tool("/product/completeness/evaluate", evaluate_product_completeness)
    register_crud_tools(mcp)


def _consistency_instructions() -> str:
    return load_prompt_instructions(__file__, "product-management-consistency-validation")
