"""Product consistency validation agent implementation and MCP tool registration."""

from __future__ import annotations

import os
from typing import Any

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.prompt_loader import load_prompt_instructions

from .adapters import ProductConsistencyAdapters, build_consistency_adapters
from .completeness_engine import CompletenessEngine


class ProductConsistencyAgent(BaseRetailAgent):
    """Agent that evaluates products with the schema-driven completeness engine."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_consistency_adapters()
        self._engine = CompletenessEngine()

    @property
    def adapters(self) -> ProductConsistencyAdapters:
        return self._adapters

    async def evaluate_completeness(
        self, sku: str, category_id: str | None = None
    ) -> dict[str, Any]:
        product = await self.adapters.products.get_product(str(sku))
        if not product:
            return {"error": "sku not found", "sku": sku}

        resolved_category = category_id or product.category or "default"
        schema = await self.adapters.completeness.get_schema(resolved_category)
        if schema is None:
            return {
                "error": "schema not found",
                "sku": sku,
                "category_id": resolved_category,
            }

        report = self._engine.evaluate(str(sku), product.model_dump(), schema)
        await self.adapters.completeness.store_gap_report(report)

        return {
            "sku": sku,
            "category_id": resolved_category,
            "completeness": report.model_dump(mode="json"),
            "needs_enrichment": bool(report.enrichable_gaps),
        }

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
    completeness_agent = agent if isinstance(agent, ProductConsistencyAgent) else None
    adapters = (
        completeness_agent.adapters
        if completeness_agent is not None
        else build_consistency_adapters()
    )
    engine = CompletenessEngine()

    async def evaluate_product_completeness(payload: dict[str, Any]) -> dict[str, Any]:
        sku = payload.get("sku")
        if not sku:
            return {"error": "sku is required"}
        category_id = payload.get("category_id")
        if completeness_agent is not None:
            return await completeness_agent.evaluate_completeness(
                sku=str(sku), category_id=category_id
            )

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

        report = engine.evaluate(str(sku), product.model_dump(), schema)
        await adapters.completeness.store_gap_report(report)
        return {
            "sku": str(sku),
            "category_id": resolved_category,
            "completeness": report.model_dump(mode="json"),
            "needs_enrichment": bool(report.enrichable_gaps),
        }

    mcp.add_tool("/product/completeness/evaluate", evaluate_product_completeness)
    _register_crud_tools(mcp)


def _register_crud_tools(mcp: FastAPIMCPServer) -> None:
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def _consistency_instructions() -> str:
    return load_prompt_instructions(__file__, "product-management-consistency-validation")
