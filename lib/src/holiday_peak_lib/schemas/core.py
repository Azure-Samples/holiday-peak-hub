"""Core schemas."""
from typing import List, Optional

from pydantic import BaseModel, Field


class UserContext(BaseModel):
    user_id: str
    segment: Optional[str] = None
    preferences: Optional[dict] = None


class Product(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    price: Optional[float] = None
    attributes: dict = Field(default_factory=dict)


class RecommendationRequest(BaseModel):
    query: str
    user: Optional[UserContext] = None
    limit: int = 5


class RecommendationResponse(BaseModel):
    items: List[Product]
    latency_ms: float
