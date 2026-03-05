"""Unified Commerce Product (UCP) schemas.

UCP models provide a flat, external-facing product representation suitable for
commerce integrations and downstream protocol consumers.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UcpImage(BaseModel):
    """Image payload for UCP exports."""

    model_config = ConfigDict(extra="forbid")

    url: str
    role: str = "primary"
    alt_text: str | None = None


class UcpPricing(BaseModel):
    """Pricing payload for UCP exports."""

    model_config = ConfigDict(extra="forbid")

    list_price: float | None = None
    sale_price: float | None = None
    currency: str = "USD"


class UcpCompliance(BaseModel):
    """Compliance metadata included in UCP exports."""

    model_config = ConfigDict(extra="forbid")

    completeness_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_validated: datetime | None = None


class UcpMetadata(BaseModel):
    """Export metadata for UCP payloads."""

    model_config = ConfigDict(extra="forbid")

    version: str = "1.0"
    protocol: str = "ucp"
    exported_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UcpProduct(BaseModel):
    """UCP product model for external commerce consumers."""

    model_config = ConfigDict(extra="forbid")

    entity_id: str
    sku: str
    title: str
    brand: str | None = None

    category_id: str | None = None
    category_label: str | None = None

    enriched_description: str | None = None
    short_description: str | None = None

    images: list[UcpImage] = Field(default_factory=list)
    pricing: UcpPricing = Field(default_factory=UcpPricing)

    attributes: dict[str, Any] = Field(default_factory=dict)

    compliance: UcpCompliance = Field(default_factory=UcpCompliance)
    metadata: UcpMetadata = Field(default_factory=UcpMetadata)
