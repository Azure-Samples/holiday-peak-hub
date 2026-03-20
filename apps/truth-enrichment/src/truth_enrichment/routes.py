"""REST route handlers for the Truth Enrichment service."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from .agents import _detect_gaps, _field_definition_for_name

router = APIRouter(prefix="/enrich", tags=["enrichment"])


class EnrichProductRequest(BaseModel):
    """Request body for on-demand product enrichment."""

    entity_id: str


class EnrichFieldRequest(BaseModel):
    """Request body for enriching a specific field."""

    entity_id: str
    field_name: str
    field_definition: dict[str, Any] | None = None


@router.post("/product/{entity_id}")
async def enrich_product(entity_id: str, request: Request) -> dict[str, Any]:
    """Trigger on-demand enrichment for all gaps in a product."""
    agent = request.app.state.agent
    product = await agent.adapters.products.get_product(entity_id)
    if product is None:
        return {"error": "product not found", "entity_id": entity_id}

    category = product.get("category", "")
    schema = await agent.adapters.products.get_schema(category)
    gaps = _detect_gaps(product, schema)
    if not gaps:
        return {"entity_id": entity_id, "message": "no enrichable gaps found", "proposed": []}

    proposed_list = []
    for field_name in gaps:
        field_def = _field_definition_for_name(schema, field_name)
        proposed = await agent.enrich_field(entity_id, field_name, product, field_def)
        proposed_list.append(proposed)

    return {"entity_id": entity_id, "proposed": proposed_list}


@router.post("/field")
async def enrich_field(body: EnrichFieldRequest, request: Request) -> dict[str, Any]:
    """Enrich a specific field for a product."""
    agent = request.app.state.agent
    product = await agent.adapters.products.get_product(body.entity_id)
    if product is None:
        return {"error": "product not found", "entity_id": body.entity_id}

    proposed = await agent.enrich_field(
        body.entity_id, body.field_name, product, body.field_definition
    )
    return {"entity_id": body.entity_id, "proposed": proposed}


@router.get("/status/{job_id}")
async def get_status(job_id: str, request: Request) -> dict[str, Any]:
    """Check the status of an enrichment job."""
    agent = request.app.state.agent
    result = await agent.adapters.proposed.get(job_id)
    if result is None:
        return {"job_id": job_id, "status": "not_found"}
    return {"job_id": job_id, "status": result.get("status"), "attribute": result}
