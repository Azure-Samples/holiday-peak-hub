"""Product routes."""

import asyncio
import logging

import httpx
from circuitbreaker import CircuitBreakerError
from crud_service.auth import User, get_current_user_optional
from crud_service.config.settings import get_settings
from crud_service.integrations import get_agent_client
from crud_service.repositories import ProductRepository
from crud_service.schemas.api.products import ProductResponse
from crud_service.schemas.domain.products import ProductQuery
from crud_service.services.product_service import fetch_products as fetch_products_service
from crud_service.services.product_service import (
    to_canonical_product as to_canonical_product_service,
)
from crud_service.services.product_service import (
    validate_product_responses,
)
from fastapi import APIRouter, Depends, HTTPException, Query, status

router = APIRouter()
product_repo = ProductRepository()
agent_client = get_agent_client()
logger = logging.getLogger(__name__)
settings = get_settings()
AGENT_FALLBACK_EXCEPTIONS = (httpx.HTTPError, CircuitBreakerError)


def _to_canonical_product(product: dict) -> dict | None:
    return to_canonical_product_service(product)


async def _fetch_products(
    *,
    search: str | None,
    category: str | None,
    limit: int,
    current_user: User | None,
) -> list[dict]:
    return await fetch_products_service(
        ProductQuery(
            search=search,
            category=category,
            limit=limit,
            current_user=current_user,
        ),
        product_repo=product_repo,
        agent_client=agent_client,
        logger=logger,
        agent_fallback_exceptions=AGENT_FALLBACK_EXCEPTIONS,
    )


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
    except asyncio.TimeoutError as exc:
        logger.warning(
            "Product list fetch timed out",
            extra={
                "app_role": settings.service_name,
                "endpoint": "/api/products",
                "search_present": bool(search),
                "category_present": bool(category),
                "limit": limit,
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product catalog is temporarily unavailable",
        ) from exc
    except Exception as exc:
        logger.warning(
            "Product list fetch failed: %s",
            exc,
            extra={
                "app_role": settings.service_name,
                "endpoint": "/api/products",
                "search_present": bool(search),
                "category_present": bool(category),
                "limit": limit,
                "error_type": type(exc).__name__,
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product catalog is temporarily unavailable",
        ) from exc

    try:
        return validate_product_responses(products, logger=logger)
    except TypeError:
        logger.warning("Product list returned invalid result type: %s", type(products).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product catalog is temporarily unavailable",
        ) from None


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
    except AGENT_FALLBACK_EXCEPTIONS as exc:
        logger.warning(
            "Product enrichment unavailable for product_id=%s; using base product data",
            product_id,
            extra={"error_type": type(exc).__name__},
            exc_info=True,
        )

    # Optionally get dynamic pricing
    try:
        dynamic_price = await agent_client.calculate_dynamic_pricing(product_id)
        if dynamic_price:
            product["price"] = dynamic_price
    except AGENT_FALLBACK_EXCEPTIONS as exc:
        logger.warning(
            "Dynamic pricing unavailable for product_id=%s; using base price",
            product_id,
            extra={"error_type": type(exc).__name__},
            exc_info=True,
        )

    return ProductResponse(**product)
