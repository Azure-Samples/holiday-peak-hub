"""UCP (Unified Catalog Protocol) product routes."""

from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter()


class TruthProductRepository(BaseRepository):
    """Repository for truth-layer product styles."""

    def __init__(self):
        super().__init__(container_name="truth_products")


truth_product_repo = TruthProductRepository()


class UCPAttribute(BaseModel):
    """A single UCP attribute key-value pair."""

    name: str
    value: object
    confidence: float | None = None


class UCPProductResponse(BaseModel):
    """Product representation in Unified Catalog Protocol (UCP) format."""

    entity_id: str
    sku: str | None = None
    name: str | None = None
    description: str | None = None
    category_id: str | None = None
    brand: str | None = None
    attributes: list[UCPAttribute] = []
    completeness_score: float | None = None
    schema_version: str | None = None
    last_updated: str | None = None


def _to_ucp(product: dict) -> UCPProductResponse:
    """Convert a truth-layer product document to UCP format."""
    raw_attrs = product.get("attributes") or {}
    attributes = [UCPAttribute(name=k, value=v) for k, v in raw_attrs.items()]
    return UCPProductResponse(
        entity_id=product.get("id", ""),
        sku=product.get("sku"),
        name=product.get("name"),
        description=product.get("description"),
        category_id=product.get("category_id"),
        brand=product.get("brand"),
        attributes=attributes,
        completeness_score=product.get("completeness_score"),
        schema_version=product.get("schema_version"),
        last_updated=product.get("updated_at"),
    )


@router.get("/ucp/products", response_model=list[UCPProductResponse])
async def list_ucp_products(
    category: str | None = Query(None, description="Filter by category ID"),
    limit: int = Query(50, le=200, description="Maximum number of results"),
):
    """List products in UCP format with optional category filter."""
    if category:
        items = await truth_product_repo.query(
            query="SELECT * FROM c WHERE c.category_id = @category_id",
            parameters=[{"name": "@category_id", "value": category}],
        )
    else:
        items = await truth_product_repo.query(query="SELECT * FROM c")
    return [_to_ucp(item) for item in items[:limit]]


@router.get("/ucp/products/{entity_id}", response_model=UCPProductResponse)
async def get_ucp_product(entity_id: str):
    """Get a single product in UCP format."""
    item = await truth_product_repo.get_by_id(entity_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product '{entity_id}' not found in truth store",
        )
    return _to_ucp(item)
