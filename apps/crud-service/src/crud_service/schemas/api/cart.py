"""External API DTOs for cart routes."""

from pydantic import BaseModel


class AddToCartRequest(BaseModel):
    """Add to cart request."""

    product_id: str
    quantity: int = 1


class CartItem(BaseModel):
    """Cart item."""

    product_id: str
    quantity: int
    price: float


class CartResponse(BaseModel):
    """Cart response."""

    user_id: str
    items: list[CartItem]
    total: float


class CartRecommendationsResponse(BaseModel):
    """Cart recommendations response."""

    user_id: str
    recommendations: dict | None
