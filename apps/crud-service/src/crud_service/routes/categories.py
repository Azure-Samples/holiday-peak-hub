"""Category routes."""

from fastapi import APIRouter, Query
from pydantic import BaseModel

from crud_service.repositories.base import BaseRepository

router = APIRouter()


class CategoryRepository(BaseRepository):
    """Repository for categories."""

    def __init__(self):
        super().__init__(container_name="categories")


category_repo = CategoryRepository()


class CategoryResponse(BaseModel):
    """Category response."""

    id: str
    name: str
    description: str | None = None
    parent_id: str | None = None
    image_url: str | None = None


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    parent_id: str | None = Query(None, description="Filter by parent category"),
):
    """
    List product categories.
    
    Anonymous access allowed.
    """
    if parent_id:
        categories = await category_repo.query(
            query="SELECT * FROM c WHERE c.parent_id = @parent_id",
            parameters=[{"name": "@parent_id", "value": parent_id}],
        )
    else:
        # Get root categories (no parent)
        categories = await category_repo.query(
            query="SELECT * FROM c WHERE NOT IS_DEFINED(c.parent_id) OR c.parent_id = null",
        )

    return [CategoryResponse(**cat) for cat in categories]


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str):
    """Get category by ID."""
    category = await category_repo.get_by_id(category_id)
    if not category:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse(**category)
