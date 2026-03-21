"""Core schemas."""

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: str
    segment: str | None = None
    preferences: dict | None = None


class Product(BaseModel):
    sku: str
    name: str
    description: str | None = None
    price: float | None = None
    attributes: dict = Field(default_factory=dict)


class RecommendationRequest(BaseModel):
    query: str
    user: UserContext | None = None
    limit: int = 5


class RecommendationResponse(BaseModel):
    items: list[Product]
    latency_ms: float
