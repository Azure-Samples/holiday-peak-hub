"""Canonical product catalog schemas.

Provides agent-ready product representations for search, discovery, and
cross-sell flows described in the business summary. Doctests demonstrate how
payloads are validated and structured.
"""

from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


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


class CanonicalProduct(BaseModel):
    """Cross-surface canonical product contract with compatibility aliases.

    Supports CRUD fields (`id`, `name`, `category_id`) and ACP/search fields
    (`item_id`, `title`).
    """

    id: str
    sku: str
    name: str
    description: str = ""
    price: float = 0.0
    currency: str | None = None
    category_id: str = "uncategorized"
    category: str | None = None
    image_url: str | None = None

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        payload = dict(value)
        payload.setdefault(
            "sku", payload.get("item_id") or payload.get("id") or payload.get("product_id")
        )
        payload.setdefault(
            "id", payload.get("sku") or payload.get("item_id") or payload.get("product_id")
        )
        payload.setdefault("name", payload.get("title"))
        payload.setdefault(
            "category_id", payload.get("category") or payload.get("category_id") or "uncategorized"
        )

        raw_price = payload.get("price")
        is_acp_shape = bool(
            payload.get("item_id") or payload.get("title") or payload.get("protocol_version")
        )
        if isinstance(raw_price, str) and is_acp_shape:
            numeric = raw_price.split()[0].strip()
            payload["price"] = float(numeric)
        elif raw_price is None:
            payload["price"] = 0.0

        if payload.get("name") is None:
            payload["name"] = payload.get("sku") or payload.get("id") or "unknown-product"
        if payload.get("description") is None:
            payload["description"] = ""

        return payload

    def to_catalog_product(self) -> CatalogProduct:
        """Convert canonical product into catalog schema used by agents."""
        return CatalogProduct(
            sku=self.sku,
            name=self.name,
            description=self.description,
            category=self.category or self.category_id,
            price=self.price,
            currency=self.currency,
            image_url=self.image_url,
        )

    def to_crud_record(self) -> dict[str, Any]:
        """Convert canonical product into CRUD-compatible response shape."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "category_id": self.category_id,
            "image_url": self.image_url,
        }


class ProductContext(BaseModel):
    """Product context exposed to agents (primary + related).

    >>> main = CatalogProduct(sku="SKU-1", name="Widget")
    >>> related = [CatalogProduct(sku="SKU-2", name="Widget Plus")]
    >>> ProductContext(product=main, related=related).related[0].sku
    'SKU-2'
    """

    product: CatalogProduct
    related: list[CatalogProduct] = Field(default_factory=list)
