"""Category routes."""

from collections.abc import Iterable
import logging

from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ValidationError

router = APIRouter()
logger = logging.getLogger(__name__)


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
    try:
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
    except Exception as exc:
        logger.warning("Category list fetch failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Categories are temporarily unavailable",
        ) from exc

    if (
        categories is None
        or isinstance(categories, (str, bytes))
        or not isinstance(categories, Iterable)
    ):
        logger.warning("Category list returned invalid result type: %s", type(categories).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Categories are temporarily unavailable",
        )

    # No GoF pattern applies - straightforward record validation and filtering.
    validated_categories: list[CategoryResponse] = []
    for category in categories:
        try:
            validated_categories.append(CategoryResponse.model_validate(category))
        except ValidationError as exc:
            logger.warning("Skipping malformed category record: %s", exc)

    return validated_categories


@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(category_id: str):
    """Get category by ID."""
    category = await category_repo.get_by_id(category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return CategoryResponse(**category)
