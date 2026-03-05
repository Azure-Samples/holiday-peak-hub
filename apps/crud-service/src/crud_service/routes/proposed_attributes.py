"""Proposed attributes routes — AI-proposed (pending review) product attributes."""

from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter()


class ProposedAttributeRepository(BaseRepository):
    """Repository for proposed attributes."""

    def __init__(self):
        super().__init__(container_name="proposed_attributes")


proposed_attr_repo = ProposedAttributeRepository()


class ProposedAttributeResponse(BaseModel):
    """Response model for a proposed attribute."""

    id: str
    entity_id: str
    field_name: str
    proposed_value: object
    status: str = "pending"
    confidence: float | None = None
    source_model: str | None = None
    evidence: list[str] | None = None
    proposed_at: str | None = None
    reviewed_at: str | None = None
    reviewed_by: str | None = None
    rejection_reason: str | None = None


@router.get(
    "/proposed/attributes/{entity_id}",
    response_model=list[ProposedAttributeResponse],
)
async def get_proposed_attributes(
    entity_id: str,
    status_filter: str | None = Query(
        None, alias="status", description="Filter by status (pending/approved/rejected)"
    ),
    limit: int = Query(50, le=200, description="Maximum number of results"),
):
    """Get all proposed attributes for a product, with optional status filter."""
    items = await proposed_attr_repo.query(
        query="SELECT * FROM c WHERE c.entity_id = @entity_id",
        parameters=[{"name": "@entity_id", "value": entity_id}],
        partition_key=entity_id,
    )
    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    return [ProposedAttributeResponse(**item) for item in items[:limit]]


@router.get(
    "/proposed/attributes/{entity_id}/{attribute_id}",
    response_model=ProposedAttributeResponse,
)
async def get_proposed_attribute(entity_id: str, attribute_id: str):
    """Get a single proposed attribute by ID."""
    item = await proposed_attr_repo.get_by_id(attribute_id, partition_key=entity_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposed attribute '{attribute_id}' not found for entity '{entity_id}'",
        )
    return ProposedAttributeResponse(**item)
