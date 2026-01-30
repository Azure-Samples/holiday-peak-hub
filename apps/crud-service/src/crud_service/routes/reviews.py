"""Review routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from crud_service.auth import User, get_current_user
from crud_service.repositories.base import BaseRepository

router = APIRouter()


class ReviewRepository(BaseRepository):
    """Repository for reviews."""

    def __init__(self):
        super().__init__(container_name="reviews")

    async def get_by_product(self, product_id: str, limit: int = 20) -> list[dict]:
        """Get reviews for a product."""
        return await self.query(
            query="SELECT * FROM c WHERE c.product_id = @product_id ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit",
            parameters=[
                {"name": "@product_id", "value": product_id},
                {"name": "@limit", "value": limit},
            ],
        )


review_repo = ReviewRepository()


class CreateReviewRequest(BaseModel):
    """Create review request."""

    product_id: str
    rating: int = Field(ge=1, le=5, description="Rating 1-5 stars")
    title: str
    comment: str


class ReviewResponse(BaseModel):
    """Review response."""

    id: str
    product_id: str
    user_id: str
    rating: int
    title: str
    comment: str
    created_at: str


@router.get("/reviews", response_model=list[ReviewResponse])
async def list_reviews(product_id: str):
    """
    List reviews for a product.
    
    Anonymous access allowed.
    """
    reviews = await review_repo.get_by_product(product_id, limit=20)
    return [ReviewResponse(**review) for review in reviews]


@router.post("/reviews", response_model=ReviewResponse)
async def create_review(
    request: CreateReviewRequest,
    current_user: User = Depends(get_current_user),
):
    """Create a product review."""
    review_id = str(uuid.uuid4())

    review = {
        "id": review_id,
        "product_id": request.product_id,
        "user_id": current_user.user_id,
        "rating": request.rating,
        "title": request.title,
        "comment": request.comment,
        "created_at": datetime.utcnow().isoformat(),
    }

    await review_repo.create(review)

    return ReviewResponse(**review)


@router.delete("/reviews/{review_id}")
async def delete_review(review_id: str, current_user: User = Depends(get_current_user)):
    """Delete a review (only by author or admin)."""
    review = await review_repo.get_by_id(review_id)
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    if review["user_id"] != current_user.user_id and "admin" not in current_user.roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    await review_repo.delete(review_id)

    return {"message": "Review deleted"}
