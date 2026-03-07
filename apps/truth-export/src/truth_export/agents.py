"""Truth Export agent implementation and MCP tool registration."""

from __future__ import annotations

import uuid
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import TruthExportAdapters, build_truth_export_adapters
from .export_engine import ExportEngine


class TruthExportAgent(BaseRetailAgent):
    """Agent that exports approved product truth data in protocol-specific formats."""

    def __init__(self, config: Any, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._adapters: TruthExportAdapters = build_truth_export_adapters()
        self._engine = ExportEngine()

    @property
    def adapters(self) -> TruthExportAdapters:
        return self._adapters

    @property
    def engine(self) -> ExportEngine:
        return self._engine

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        entity_id = request.get("entity_id")
        protocol = request.get("protocol", "ucp")

        if not entity_id:
            return {"error": "entity_id is required"}

        product = await self._adapters.truth_store.get_product_style(str(entity_id))
        if product is None:
            return {"error": "product not found", "entity_id": entity_id}

        attributes = await self._adapters.truth_store.get_truth_attributes(str(entity_id))
        mapping = await self._adapters.truth_store.get_protocol_mapping(str(protocol))

        job_id = self._adapters.job_tracker.create(
            str(entity_id),
            str(protocol),
            request.get("partner_id"),
        )
        result = self._engine.export(
            job_id=job_id,
            product=product,
            attributes=attributes,
            protocol=str(protocol),
            mapping=mapping,
            partner_id=request.get("partner_id"),
        )

        await self._adapters.truth_store.save_export_result(result.model_dump())

        audit = self._engine.build_audit_event(job_id, product, str(protocol))
        await self._adapters.truth_store.save_audit_event(audit.model_dump())

        self._adapters.job_tracker.update(job_id, result.status)

        return result.model_dump()


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for truth-export workflows."""
    adapters = getattr(agent, "adapters", build_truth_export_adapters())
    engine = getattr(agent, "engine", ExportEngine())

    async def export_product(payload: dict[str, Any]) -> dict[str, Any]:
        entity_id = payload.get("entity_id")
        protocol = payload.get("protocol", "ucp")
        if not entity_id:
            return {"error": "entity_id is required"}

        product = await adapters.truth_store.get_product_style(str(entity_id))
        if product is None:
            return {"error": "product not found", "entity_id": entity_id}

        attributes = await adapters.truth_store.get_truth_attributes(str(entity_id))
        mapping = await adapters.truth_store.get_protocol_mapping(str(protocol))

        result = engine.export(
            job_id=str(uuid.uuid4()),
            product=product,
            attributes=attributes,
            protocol=str(protocol),
            mapping=mapping,
        )
        return result.model_dump()

    async def get_export_status(payload: dict[str, Any]) -> dict[str, Any]:
        job_id = payload.get("job_id")
        if not job_id:
            return {"error": "job_id is required"}
        job = adapters.job_tracker.get(str(job_id))
        return job or {"error": "job not found", "job_id": job_id}

    async def list_sources(_payload: dict[str, Any]) -> dict[str, Any]:
        return {"protocols": engine.supported_protocols()}

    mcp.add_tool("/export/product", export_product)
    mcp.add_tool("/export/status", get_export_status)
    mcp.add_tool("/export/protocols", list_sources)
