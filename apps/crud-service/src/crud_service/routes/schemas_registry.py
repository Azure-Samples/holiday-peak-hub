"""Category schema registry routes."""

from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

router = APIRouter()


class SchemaRepository(BaseRepository):
    """Repository for category schemas."""

    def __init__(self):
        super().__init__(container_name="schemas")


schema_repo = SchemaRepository()


class SchemaField(BaseModel):
    """A single field definition in a category schema."""

    name: str
    type: str
    required: bool = False
    description: str | None = None


class CategorySchemaResponse(BaseModel):
    """Response model for a category schema."""

    id: str
    category_id: str
    category_name: str | None = None
    version: str | None = None
    fields: list[SchemaField] = []
    created_at: str | None = None
    updated_at: str | None = None


class CategorySchemaRequest(BaseModel):
    """Request model for creating or updating a category schema."""

    category_id: str
    category_name: str | None = None
    version: str | None = None
    fields: list[SchemaField] = []


@router.get("/schemas", response_model=list[CategorySchemaResponse])
async def list_schemas():
    """List all category schemas."""
    items = await schema_repo.query(query="SELECT * FROM c")
    return [CategorySchemaResponse(**item) for item in items]


@router.get("/schemas/{category_id}", response_model=CategorySchemaResponse)
async def get_schema(category_id: str):
    """Get the schema for a specific category."""
    items = await schema_repo.query(
        query="SELECT * FROM c WHERE c.category_id = @category_id",
        parameters=[{"name": "@category_id", "value": category_id}],
    )
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Schema for category '{category_id}' not found",
        )
    return CategorySchemaResponse(**items[0])


@router.post("/schemas", response_model=CategorySchemaResponse, status_code=status.HTTP_201_CREATED)
async def upsert_schema(payload: CategorySchemaRequest):
    """Upload or update a category schema."""
    from datetime import datetime, timezone

    existing = await schema_repo.query(
        query="SELECT * FROM c WHERE c.category_id = @category_id",
        parameters=[{"name": "@category_id", "value": payload.category_id}],
    )
    now = datetime.now(timezone.utc).isoformat()

    if existing:
        doc = existing[0]
        doc.update(
            {
                "category_name": payload.category_name,
                "version": payload.version,
                "fields": [f.model_dump() for f in payload.fields],
                "updated_at": now,
            }
        )
        updated = await schema_repo.update(doc)
        return CategorySchemaResponse(**updated)

    doc = {
        "id": payload.category_id,
        "category_id": payload.category_id,
        "category_name": payload.category_name,
        "version": payload.version,
        "fields": [f.model_dump() for f in payload.fields],
        "created_at": now,
        "updated_at": now,
    }
    created = await schema_repo.create(doc)
    return CategorySchemaResponse(**created)
