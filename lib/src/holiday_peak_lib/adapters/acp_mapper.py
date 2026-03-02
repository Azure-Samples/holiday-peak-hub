"""Shared ACP mapping utilities."""

from typing import Any

from holiday_peak_lib.schemas.acp import AcpProduct
from holiday_peak_lib.schemas.product import CatalogProduct


class AcpCatalogMapper:
    """Map catalog products to ACP Product Feed fields."""

    def to_acp_product(
        self,
        product: CatalogProduct,
        *,
        availability: str,
        currency: str = "usd",
    ) -> dict[str, Any]:
        sku = product.sku
        price = product.price if product.price is not None else 0.0
        image_url = product.image_url or "https://example.com/images/placeholder.png"
        product_url = f"https://example.com/products/{sku}"
        return AcpProduct(
            item_id=sku,
            title=product.name,
            description=product.description or "",
            url=product_url,
            image_url=image_url,
            brand=product.brand or "",
            price=f"{price:.2f} {currency}",
            availability=availability,
        ).model_dump()
