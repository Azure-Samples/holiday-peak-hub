"""Product routes."""

from collections.abc import Iterable
import logging

from crud_service.auth import User, get_current_user_optional
from crud_service.integrations import get_agent_client
from crud_service.repositories import ProductRepository
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from pydantic import ValidationError

router = APIRouter()
product_repo = ProductRepository()
agent_client = get_agent_client()
logger = logging.getLogger(__name__)


class ProductResponse(BaseModel):
    """Product response schema."""

    id: str
    name: str
    description: str
    price: float
    category_id: str
    image_url: str | None = None
    in_stock: bool = True
    rating: float | None = None
    review_count: int | None = None
    features: list[str] | None = None
    media: list[dict[str, object]] | None = None
    inventory: dict[str, object] | None = None
    related: list[dict[str, object]] | None = None


async def _fetch_products(
    *,
    search: str | None,
    category: str | None,
    limit: int,
    current_user: User | None,
) -> list[dict]:
    products: list[dict] = []

    if search:
        try:
            agent_results = await agent_client.semantic_search(search, limit=limit)
            if agent_results:
                products = agent_results
        except Exception:
            pass
        if not products:
            products = await product_repo.search_by_name(search, limit=limit)
    elif category:
        products = await product_repo.get_by_category(category, limit=limit)
    else:
        products = await product_repo.query(
            query="SELECT * FROM c OFFSET 0 LIMIT @limit",
            parameters=[{"name": "@limit", "value": limit}],
        )

    if current_user:
        try:
            recommendations = await agent_client.get_user_recommendations(
                user_id=current_user.user_id
            )
            if isinstance(recommendations, dict):
                boosted_skus = recommendations.get("boosted_skus") or []
                if boosted_skus:
                    sku_set = set(boosted_skus)
                    boosted = [p for p in products if p.get("id") in sku_set]
                    rest = [p for p in products if p.get("id") not in sku_set]
                    products = boosted + rest
        except Exception:
            pass

    return products


@router.get("/products", response_model=list[ProductResponse])
async def list_products(
    search: str | None = Query(None, description="Search term"),
    category: str | None = Query(None, description="Category filter"),
    limit: int = Query(20, le=100),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    List products with optional search and filters.

    Anonymous users can browse products.
    Semantic search is attempted first when a search term is provided;
    the CRUD keyword search is used as fallback.
    Authenticated users may get personalized ordering (via agent).
    """
    try:
        products = await _fetch_products(
            search=search,
            category=category,
            limit=limit,
            current_user=current_user,
        )
    except Exception as exc:
        logger.warning("Product list fetch failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product catalog is temporarily unavailable",
        ) from exc

    if products is None or isinstance(products, (str, bytes)) or not isinstance(products, Iterable):
        logger.warning("Product list returned invalid result type: %s", type(products).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product catalog is temporarily unavailable",
        )

    # No GoF pattern applies - straightforward record validation and filtering.
    validated_products: list[ProductResponse] = []
    for product in products:
        try:
            validated_products.append(ProductResponse.model_validate(product))
        except ValidationError as exc:
            logger.warning("Skipping malformed product record: %s", exc)

    return validated_products


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(product_id: str):
    """Get product details by ID."""
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Optionally enrich product details
    try:
        enrichment = await agent_client.get_product_enrichment(product_id)
        if isinstance(enrichment, dict):
            product["description"] = enrichment.get("description", product.get("description"))
            product["rating"] = enrichment.get("rating")
            product["review_count"] = enrichment.get("review_count")
            product["features"] = enrichment.get("features")
            product["media"] = enrichment.get("media")
            product["inventory"] = enrichment.get("inventory")
            product["related"] = enrichment.get("related")
    except Exception:
        pass  # Use base product data

    # Optionally get dynamic pricing
    try:
        dynamic_price = await agent_client.calculate_dynamic_pricing(product_id)
        if dynamic_price:
            product["price"] = dynamic_price
    except Exception:
        pass  # Use base price

    return ProductResponse(**product)
