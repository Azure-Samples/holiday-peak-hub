"""Canonical product catalog schemas.

Provides agent-ready product representations for search, discovery, and
cross-sell flows described in the business summary. Doctests demonstrate how
payloads are validated and structured.
"""

from typing import Any, Optional
from pydantic import BaseModel, Field


class CatalogProduct(BaseModel):
    """Standardized product representation for catalog and search.

    >>> CatalogProduct(sku="SKU-1", name="Widget", price=9.99).sku
    'SKU-1'
    >>> CatalogProduct(sku="SKU-2", name="Gadget", attributes={"color": "red"}).attributes["color"]
    'red'
    """

    sku: str
    name: str
    description: Optional[str] = None
    brand: Optional[str] = None
    category: Optional[str] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    image_url: Optional[str] = None
    rating: Optional[float] = None
    tags: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    variants: list[dict[str, Any]] = Field(default_factory=list)


class ProductContext(BaseModel):
    """Product context exposed to agents (primary + related).

    >>> main = CatalogProduct(sku="SKU-1", name="Widget")
    >>> related = [CatalogProduct(sku="SKU-2", name="Widget Plus")]
    >>> ProductContext(product=main, related=related).related[0].sku
    'SKU-2'
    """

    product: CatalogProduct
    related: list[CatalogProduct] = Field(default_factory=list)
