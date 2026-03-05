"""Canonical protocol data models for enterprise connectors.

These models provide a vendor-neutral representation of common retail domain
entities. Each connector implementation maps vendor-specific API responses to
one of these canonical types so agents can consume data uniformly.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class InventoryData(BaseModel):
    """Canonical inventory record returned by SCM/WMS connectors.

    >>> InventoryData(item_number="ITEM-1", organization_code="M1", on_hand_quantity=100).on_hand_quantity
    100
    >>> InventoryData(item_number="ITEM-1", organization_code="M1", on_hand_quantity=0).reserved_quantity
    0
    """

    item_number: str
    organization_code: str
    organization_id: Optional[int] = None
    description: Optional[str] = None
    on_hand_quantity: float = 0.0
    reserved_quantity: float = 0.0
    available_quantity: Optional[float] = None
    unit_of_measure: Optional[str] = None
    subinventory_code: Optional[str] = None
    locator: Optional[str] = None
    lot_number: Optional[str] = None
    expiration_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    attributes: dict = Field(default_factory=dict)

    @property
    def effective_available(self) -> float:
        """Return available_quantity if set, else on_hand - reserved."""
        if self.available_quantity is not None:
            return self.available_quantity
        return max(0.0, self.on_hand_quantity - self.reserved_quantity)


class ProductData(BaseModel):
    """Canonical product record returned by PIM connectors.

    >>> ProductData(product_id="P1", name="Widget").name
    'Widget'
    """

    product_id: str
    name: str
    description: Optional[str] = None
    sku: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    images: list[str] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)
    last_updated: Optional[datetime] = None


class AssetData(BaseModel):
    """Canonical digital asset record returned by DAM connectors.

    >>> AssetData(asset_id="A1", name="hero.jpg", url="https://cdn.example.com/hero.jpg").url
    'https://cdn.example.com/hero.jpg'
    """

    asset_id: str
    name: str
    url: str
    media_type: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)
    last_updated: Optional[datetime] = None


class CustomerData(BaseModel):
    """Canonical customer record returned by CRM/CDP connectors.

    >>> CustomerData(customer_id="C1", email="a@b.com").email
    'a@b.com'
    """

    customer_id: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    segments: list[str] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)
    last_updated: Optional[datetime] = None


class OrderData(BaseModel):
    """Canonical order record returned by Commerce/OMS connectors.

    >>> OrderData(order_id="O1", status="open").status
    'open'
    """

    order_id: str
    status: str
    customer_id: Optional[str] = None
    total_amount: Optional[float] = None
    currency: Optional[str] = None
    line_items: list[dict] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None


class SegmentData(BaseModel):
    """Canonical analytics segment record.

    >>> SegmentData(segment_id="S1", name="High Value").name
    'High Value'
    """

    segment_id: str
    name: str
    description: Optional[str] = None
    size: Optional[int] = None
    attributes: dict = Field(default_factory=dict)
    last_updated: Optional[datetime] = None
