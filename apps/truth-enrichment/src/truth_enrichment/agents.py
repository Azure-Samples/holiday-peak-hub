"""TruthEnrichmentAgent: AI-powered product attribute enrichment."""

from __future__ import annotations

import os
import uuid
from typing import Any

from holiday_peak_lib.adapters import BaseCRUDAdapter
from holiday_peak_lib.agents import BaseRetailAgent
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

from .adapters import EnrichmentAdapters, build_enrichment_adapters
from .enrichment_engine import EnrichmentEngine


class TruthEnrichmentAgent(BaseRetailAgent):
    """Agent that enriches product attributes using Azure AI Foundry."""

    def __init__(self, config, *args: Any, **kwargs: Any) -> None:
        super().__init__(config, *args, **kwargs)
        self._engine = EnrichmentEngine()
        self._adapters = build_enrichment_adapters()
        self._adapters.image_analysis.set_vision_invoker(self.invoke_model)
        self._adapters.image_analysis.set_vision_prompt_builder(self._engine.build_vision_prompt)

    @property
    def adapters(self) -> EnrichmentAdapters:
        return self._adapters

    @property
    def engine(self) -> EnrichmentEngine:
        return self._engine

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        """Enrich a product's missing fields on demand."""
        entity_id = request.get("entity_id") or request.get("product_id")
        if not entity_id:
            return {"error": "entity_id is required"}

        product = await self.adapters.products.get_product(str(entity_id))
        if product is None:
            return {"error": "product not found", "entity_id": entity_id}

        category = product.get("category", "")
        schema = await self.adapters.products.get_schema(category)
        gaps = _detect_gaps(product, schema)

        if not gaps:
            return {
                "service": self.service_name,
                "entity_id": entity_id,
                "message": "no enrichable gaps found",
                "proposed": [],
            }

        proposed_list = await self._enrich_gaps(entity_id, product, gaps, schema)
        return {
            "service": self.service_name,
            "entity_id": entity_id,
            "proposed": proposed_list,
        }

    async def enrich_field(
        self,
        entity_id: str,
        field_name: str,
        product: dict[str, Any],
        field_definition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Enrich a single field for a product and persist the result."""
        job_id = str(uuid.uuid4())
        messages = self.engine.build_prompt(product, field_name, field_definition)

        image_raw = await self.adapters.image_analysis.analyze_attribute_from_images(
            entity_id=entity_id,
            field_name=field_name,
            product=product,
            field_definition=field_definition,
        )
        image_parsed = self.engine.parse_ai_response(image_raw)

        text_parsed: dict[str, Any] | None = None
        if self.slm or self.llm:
            text_raw = await self.invoke_model(
                request={"entity_id": entity_id, "field_name": field_name},
                messages=messages,
            )
            text_parsed = self.engine.parse_ai_response(text_raw)

        parsed = self.engine.merge_enrichment_candidates(
            field_name=field_name,
            original_data={field_name: product.get(field_name)},
            image_parsed=image_parsed,
            text_parsed=text_parsed,
        )
        proposed = self.engine.build_proposed_attribute(
            entity_id=entity_id,
            field_name=field_name,
            parsed=parsed,
            model_id=_model_id(self),
            job_id=job_id,
        )

        await self.adapters.proposed.upsert(proposed)

        if not self.engine.needs_hitl(proposed):
            await self.adapters.truth.upsert({**proposed, "status": "approved"})

        audit = self.engine.build_audit_event(
            "enrichment_proposed", entity_id, field_name, proposed
        )
        await self.adapters.audit.append(audit)

        if self.engine.needs_hitl(proposed):
            await self.adapters.hitl_publisher.publish(
                {"entity_id": entity_id, "field_name": field_name, "proposed_id": proposed["id"]}
            )

        return proposed

    async def _enrich_gaps(
        self,
        entity_id: str,
        product: dict[str, Any],
        gaps: list[str],
        schema: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        results = []
        field_defs = (schema or {}).get("fields", {})
        for field_name in gaps:
            field_def = field_defs.get(field_name) if field_defs else None
            proposed = await self.enrich_field(entity_id, field_name, product, field_def)
            results.append(proposed)
        return results


def register_mcp_tools(mcp: FastAPIMCPServer, agent: BaseRetailAgent) -> None:
    """Expose MCP tools for truth enrichment workflows."""

    async def ingest_product(payload: dict[str, Any]) -> dict[str, Any]:
        return await agent.handle(payload)

    async def get_enrichment_status(payload: dict[str, Any]) -> dict[str, Any]:
        attribute_id = payload.get("attribute_id")
        if not attribute_id:
            return {"error": "attribute_id is required"}
        adapters: EnrichmentAdapters = getattr(agent, "adapters", build_enrichment_adapters())
        result = await adapters.proposed.get(str(attribute_id))
        return {"attribute": result}

    mcp.add_tool("/enrich/product", ingest_product)
    mcp.add_tool("/enrich/status", get_enrichment_status)
    _register_crud_tools(mcp)


def _register_crud_tools(mcp: FastAPIMCPServer) -> None:
    crud_url = os.getenv("CRUD_SERVICE_URL")
    if not crud_url:
        return
    BaseCRUDAdapter(crud_url).register_mcp_tools(mcp)


def _detect_gaps(product: dict[str, Any], schema: dict[str, Any] | None) -> list[str]:
    """Return field names that are required by the schema but missing from the product."""
    if schema is None:
        return []

    required_fields: list[str] = []
    seen: set[str] = set()

    for field_name in schema.get("required_fields", []):
        if isinstance(field_name, str) and field_name not in seen:
            required_fields.append(field_name)
            seen.add(field_name)

    fields = schema.get("fields", {})
    if isinstance(fields, list):
        for field in fields:
            if not isinstance(field, dict) or not field.get("required"):
                continue
            field_name = field.get("name")
            if isinstance(field_name, str) and field_name not in seen:
                required_fields.append(field_name)
                seen.add(field_name)
    elif isinstance(fields, dict):
        for field_name, definition in fields.items():
            if (
                isinstance(field_name, str)
                and isinstance(definition, dict)
                and definition.get("required")
                and field_name not in seen
            ):
                required_fields.append(field_name)
                seen.add(field_name)

    return [field_name for field_name in required_fields if _is_missing(product.get(field_name))]


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, (list, dict, tuple, set)):
        return len(value) == 0
    return False


def _model_id(agent: BaseRetailAgent) -> str:
    if agent.llm:
        deployment_name = getattr(agent.llm, "deployment_name", None)
        return deployment_name or "llm"
    if agent.slm:
        deployment_name = getattr(agent.slm, "deployment_name", None)
        return deployment_name or "slm"
    return "unknown"
