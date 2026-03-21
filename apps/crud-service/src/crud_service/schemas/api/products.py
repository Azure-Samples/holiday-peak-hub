"""External API DTOs for product routes."""

from pydantic import BaseModel


class ProductResponse(BaseModel):
    """Product response schema."""

    id: str
    name: str
    description: str
    price: float
    category_id: str
    image_url: str | None = None
    in_stock: bool = True
    rating: float | None = None
    review_count: int | None = None
    features: list[str] | None = None
    media: list[dict[str, object]] | None = None
    inventory: dict[str, object] | None = None
    related: list[dict[str, object]] | None = None
