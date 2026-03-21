"""Agentic Commerce Protocol (ACP) schemas used across services."""

from typing import Any

from pydantic import BaseModel, Field


class AcpPartnerProfile(BaseModel):
    """Partner-specific profile used for field filtering in ACP exports."""

    partner_id: str
    share_policy: list[str] = Field(default_factory=list)
    restricted_fields: list[str] = Field(default_factory=list)


class AcpProduct(BaseModel):
    """ACP product feed item."""

    item_id: str
    title: str
    description: str
    url: str
    image_url: str
    brand: str
    price: str
    availability: str
    is_eligible_search: bool = True
    is_eligible_checkout: bool = True
    store_name: str = "Example Store"
    seller_url: str = "https://example.com/store"
    seller_privacy_policy: str = "https://example.com/privacy"
    seller_tos: str = "https://example.com/terms"
    return_policy: str = "https://example.com/returns"
    return_window: int = 30
    target_countries: list[str] = Field(default_factory=lambda: ["US"])
    store_country: str = "US"
    protocol_version: str = "1.0"
    partner_profile: AcpPartnerProfile | None = None
    extended_attributes: dict[str, Any] = Field(default_factory=dict)
