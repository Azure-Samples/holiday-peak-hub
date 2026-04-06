"""Product routes."""

import asyncio
import logging
from datetime import UTC, datetime

import httpx
from circuitbreaker import CircuitBreakerError
from crud_service.auth import User, get_current_user_optional
from crud_service.config.settings import get_settings
from crud_service.integrations import get_agent_client, get_event_publisher
from crud_service.repositories import ProductRepository
from crud_service.schemas.api.products import (
    ProductEnrichmentTriggerRequest,
    ProductEnrichmentTriggerResponse,
    ProductResponse,
)
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
event_publisher = get_event_publisher()
logger = logging.getLogger(__name__)
settings = get_settings()
AGENT_FALLBACK_EXCEPTIONS = (httpx.HTTPError, CircuitBreakerError)


def _to_canonical_product(product: dict) -> dict | None:
    return to_canonical_product_service(product)


def _log_products_fetch_failure(
    *,
    message: str,
    search: str | None,
    category: str | None,
    limit: int,
    exc: BaseException,
) -> None:
    logger.warning(
        message,
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


async def _fetch_products(
    *,
    search: str | None,
    category: str | None,
    limit: int,
    current_user: User | None,
) -> list[dict]:
    try:
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
    except asyncio.TimeoutError as exc:
        _log_products_fetch_failure(
            message="Product list fetch timed out; returning empty fallback list",
            search=search,
            category=category,
            limit=limit,
            exc=exc,
        )
        # No GoF pattern applies - this endpoint uses a fail-open fallback for read availability.
        return []
    except Exception as exc:  # pylint: disable=broad-exception-caught
        _log_products_fetch_failure(
            message="Product list fetch failed; returning empty fallback list",
            search=search,
            category=category,
            limit=limit,
            exc=exc,
        )
        return []


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
    products = await _fetch_products(
        search=search,
        category=category,
        limit=limit,
        current_user=current_user,
    )

    try:
        return validate_product_responses(products, logger=logger)
    except TypeError:
        logger.warning(
            "Product list returned invalid result type: %s; returning empty fallback list",
            type(products).__name__,
        )
        return []


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


@router.post(
    "/products/{product_id}/trigger-enrichment",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=ProductEnrichmentTriggerResponse,
)
async def trigger_product_enrichment(
    product_id: str,
    request: ProductEnrichmentTriggerRequest | None = None,
):
    """Queue a ProductUpdated event to trigger asynchronous product enrichment."""
    product = await product_repo.get_by_id(product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    queued_at = datetime.now(UTC).isoformat()
    event_payload = dict(product)
    event_payload["timestamp"] = queued_at

    if request and request.trace_id is not None:
        event_payload["trace_id"] = request.trace_id
    if request and request.trigger_source is not None:
        event_payload["trigger_source"] = request.trigger_source
    if request and request.reason is not None:
        event_payload["reason"] = request.reason

    await event_publisher.publish_product_updated(event_payload)

    return ProductEnrichmentTriggerResponse(
        status="queued",
        product_id=product_id,
        event_type="ProductUpdated",
        queued_at=queued_at,
        trace_id=request.trace_id if request else None,
        trigger_source=request.trigger_source if request else None,
        reason=request.reason if request else None,
    )
