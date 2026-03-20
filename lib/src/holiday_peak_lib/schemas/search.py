"""Search and query-intelligence schemas.

Pydantic v2 models used by intelligent search and product enrichment flows.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class SearchEnrichedProduct(BaseModel):
    """Enriched product document optimized for intelligent search."""

    model_config = ConfigDict(populate_by_name=True)

    id: str
    entity_id: str = Field(alias="entityId")
    sku: str
    name: str
    brand: str
    category: str
    description: Optional[str] = None
    price: Optional[float] = None
    use_cases: list[str] = Field(default_factory=list, alias="useCases")
    complementary_products: list[str] = Field(
        default_factory=list,
        alias="complementaryProducts",
    )
    substitute_products: list[str] = Field(default_factory=list, alias="substituteProducts")
    search_keywords: list[str] = Field(default_factory=list, alias="searchKeywords")
    enriched_description: Optional[str] = Field(None, alias="enrichedDescription")
    enriched_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="enrichedAt",
    )
    enrichment_model: Optional[str] = Field(None, alias="enrichmentModel")
    source_approval_version: int = Field(alias="sourceApprovalVersion")


class IntentClassification(BaseModel):
    """Structured query interpretation output for intelligent search."""

    model_config = ConfigDict(populate_by_name=True)

    query_type: Literal["simple", "complex"] = Field(alias="queryType")
    category: Optional[str] = None
    attributes: list[str] = Field(default_factory=list)
    use_case: Optional[str] = Field(None, alias="useCase")
    brand: Optional[str] = None
    price_range: tuple[float | None, float | None] = Field(
        default=(None, None),
        alias="priceRange",
    )
    filters: dict[str, Any] = Field(default_factory=dict)
    sub_queries: list[str] = Field(default_factory=list, alias="subQueries")
    confidence: float = Field(..., ge=0.0, le=1.0)
