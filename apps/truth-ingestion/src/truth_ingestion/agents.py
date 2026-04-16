"""Truth Ingestion agent and MCP tool registration."""

from __future__ import annotations

from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.base_agent import AgentDependencies
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from holiday_peak_lib.agents.registration_helpers import get_agent_adapters

from .adapters import (
    IngestionAdapters,
    build_ingestion_adapters,
    ingest_bulk_products,
    ingest_single_product,
)


class TruthIngestionAgent(BaseRetailAgent):
    """Agent that orchestrates product ingestion from PIM/DAM into the truth store."""

    def __init__(self, config: AgentDependencies, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters = build_ingestion_adapters()

    @property
    def adapters(self) -> IngestionAdapters:
        return self._adapters

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle an agent invocation for product ingestion.

        Supports ``action`` values: ``ingest_single``, ``ingest_bulk``, ``get_status``.
        """
        action = request.get("action", "ingest_single")

        if action == "ingest_bulk":
            products = request.get("products", [])
            if not products:
                return {"error": "products list is required for bulk ingestion"}
            concurrency = int(request.get("concurrency", 5))
            results = await ingest_bulk_products(products, self._adapters, concurrency=concurrency)
            return {"action": action, "results": results, "count": len(results)}

        if action == "get_status":
            entity_id = request.get("entity_id")
            if not entity_id:
                return {"error": "entity_id is required"}
            record = await self._adapters.truth_store.get_product_style(str(entity_id))
            return {
                "entity_id": entity_id,
                "found": record is not None,
                "record": record,
            }

        # Default: ingest_single
        product = request.get("product")
        if not product:
            return {"error": "product payload is required"}
        result = await ingest_single_product(product, self._adapters)
        return {"action": "ingest_single", "result": result}


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for truth ingestion workflows."""
    adapters: IngestionAdapters = get_agent_adapters(agent, build_ingestion_adapters)

    async def ingest_product(payload: dict[str, Any]) -> dict[str, Any]:
        """MCP tool: ingest a single product from a PIM payload."""
        product = payload.get("product")
        if not product:
            return {"error": "product payload is required"}
        return await ingest_single_product(product, adapters)

    async def get_ingestion_status(payload: dict[str, Any]) -> dict[str, Any]:
        """MCP tool: check whether a product has been ingested."""
        entity_id = payload.get("entity_id")
        if not entity_id:
            return {"error": "entity_id is required"}
        record = await adapters.truth_store.get_product_style(str(entity_id))
        return {
            "entity_id": entity_id,
            "found": record is not None,
            "record": record,
        }

    async def list_sources(payload: dict[str, Any]) -> dict[str, Any]:
        """MCP tool: list configured PIM/DAM source connectivity."""
        return {
            "pim_configured": bool(adapters.pim._base_url),
            "dam_configured": bool(adapters.dam._base_url),
            "events_configured": bool(adapters.events._connection_string),
            "truth_store_configured": bool(adapters.truth_store._cosmos_uri),
        }

    mcp.add_tool("/ingest/product", ingest_product)
    mcp.add_tool("/ingest/status", get_ingestion_status)
    mcp.add_tool("/ingest/sources", list_sources)
