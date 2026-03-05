"""Truth attributes routes — approved (official) product attributes."""

from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter()


class TruthAttributeRepository(BaseRepository):
    """Repository for truth (approved) attributes."""

    def __init__(self):
        super().__init__(container_name="truth_attributes")


truth_attr_repo = TruthAttributeRepository()


class TruthAttributeResponse(BaseModel):
    """Response model for an approved truth attribute."""

    id: str
    entity_id: str
    field_name: str
    value: object
    source_model: str | None = None
    confidence: float | None = None
    approved_at: str | None = None
    approved_by: str | None = None


@router.get(
    "/truth/attributes/{entity_id}",
    response_model=list[TruthAttributeResponse],
)
async def get_truth_attributes(entity_id: str):
    """Get all official (approved) attributes for a product."""
    items = await truth_attr_repo.query(
        query="SELECT * FROM c WHERE c.entity_id = @entity_id",
        parameters=[{"name": "@entity_id", "value": entity_id}],
        partition_key=entity_id,
    )
    return [TruthAttributeResponse(**item) for item in items]


@router.get(
    "/truth/attributes/{entity_id}/{field_name}",
    response_model=TruthAttributeResponse,
)
async def get_truth_attribute(entity_id: str, field_name: str):
    """Get a single official attribute for a product by field name."""
    items = await truth_attr_repo.query(
        query=("SELECT * FROM c WHERE c.entity_id = @entity_id" " AND c.field_name = @field_name"),
        parameters=[
            {"name": "@entity_id", "value": entity_id},
            {"name": "@field_name", "value": field_name},
        ],
        partition_key=entity_id,
    )
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Attribute '{field_name}' not found for entity '{entity_id}'",
        )
    return TruthAttributeResponse(**items[0])
