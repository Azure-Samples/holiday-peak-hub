"""Agentic Commerce Protocol (ACP) schemas used across services."""

from pydantic import BaseModel, Field


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
