"""ACP product feed routes."""

from crud_service.auth import User, get_current_user_optional
from crud_service.routes.products import _fetch_products, product_repo
from fastapi import APIRouter, Depends, HTTPException, Query, status
from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.schemas.acp import AcpProduct
from holiday_peak_lib.schemas.product import CatalogProduct

router = APIRouter()
acp_mapper = AcpCatalogMapper()


def _to_catalog_product(product: dict) -> CatalogProduct:
    return CatalogProduct(
        sku=str(product.get("id", "")),
        name=str(product.get("name", "")),
        description=product.get("description"),
        brand=product.get("brand") or "",
        category=product.get("category") or product.get("category_id"),
        price=product.get("price"),
        currency=product.get("currency"),
        image_url=product.get("image_url"),
        rating=product.get("rating"),
        tags=product.get("tags") or [],
        attributes=product.get("attributes") or {},
        variants=product.get("variants") or [],
    )


def _to_acp_product(product: dict) -> AcpProduct:
    availability = "in_stock" if product.get("in_stock", True) else "out_of_stock"
    currency = str(product.get("currency", "usd"))
    return AcpProduct(
        **acp_mapper.to_acp_product(
            _to_catalog_product(product),
            availability=availability,
            currency=currency,
        )
    )


@router.get("/products", response_model=list[AcpProduct])
async def list_products_acp(
    search: str | None = Query(None, description="Search term"),
    category: str | None = Query(None, description="Category filter"),
    limit: int = Query(20, le=100),
    current_user: User | None = Depends(get_current_user_optional),
):
    """List products in ACP Product Feed format."""
    products = await _fetch_products(
        search=search,
        category=category,
        limit=limit,
        current_user=current_user,
    )
    return [_to_acp_product(product) for product in products]


@router.get("/products/{product_id}", response_model=AcpProduct)
async def get_product_acp(product_id: str):
    """Get product details by ID in ACP Product Feed format."""
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _to_acp_product(product)
