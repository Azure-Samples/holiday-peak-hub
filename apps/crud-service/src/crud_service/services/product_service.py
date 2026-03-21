"""Business logic for product retrieval and normalization."""

from collections.abc import Iterable
from typing import Any

from crud_service.schemas.api.products import ProductResponse
from crud_service.schemas.domain.products import ProductQuery
from holiday_peak_lib.schemas import CanonicalProduct
from pydantic import ValidationError


def to_canonical_product(product: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize product records to canonical CRUD schema when possible."""
    if not isinstance(product, dict):
        return None
    try:
        return CanonicalProduct.model_validate(product).to_crud_record()
    except ValidationError:
        return None


async def fetch_products(
    query: ProductQuery,
    *,
    product_repo: Any,
    agent_client: Any,
    logger: Any,
    agent_fallback_exceptions: tuple[type[BaseException], ...],
) -> list[dict[str, Any]]:
    """Fetch product records using search/category/default paths and personalization."""
    products: list[dict[str, Any]] = []

    if query.search:
        try:
            agent_results = await agent_client.semantic_search(query.search, limit=query.limit)
            if isinstance(agent_results, list):
                canonical_results: list[dict[str, Any]] = []
                for product in agent_results:
                    normalized = to_canonical_product(product)
                    if normalized is not None:
                        canonical_results.append(normalized)
                if canonical_results:
                    products = canonical_results
        except agent_fallback_exceptions as exc:
            logger.warning(
                "Semantic search unavailable; falling back to keyword search for search=%s",
                query.search,
                extra={"error_type": type(exc).__name__},
                exc_info=True,
            )
        if not products:
            products = await product_repo.search_by_name(query.search, limit=query.limit)
    elif query.category:
        products = await product_repo.get_by_category(query.category, limit=query.limit)
    else:
        products = await product_repo.query(
            query="SELECT * FROM c OFFSET 0 LIMIT @limit",
            parameters=[{"name": "@limit", "value": query.limit}],
        )

    if query.current_user:
        try:
            recommendations = await agent_client.get_user_recommendations(
                user_id=query.current_user.user_id
            )
            if isinstance(recommendations, dict):
                boosted_skus = recommendations.get("boosted_skus") or []
                if boosted_skus:
                    sku_set = set(boosted_skus)
                    boosted = [p for p in products if p.get("id") in sku_set]
                    rest = [p for p in products if p.get("id") not in sku_set]
                    products = boosted + rest
        except agent_fallback_exceptions as exc:
            logger.warning(
                "Personalized product ordering unavailable for user_id=%s",
                query.current_user.user_id,
                extra={"error_type": type(exc).__name__},
                exc_info=True,
            )

    return products


def validate_product_responses(
    products: Any,
    *,
    logger: Any,
) -> list[ProductResponse]:
    """Validate and normalize product records into API DTOs."""
    if products is None or isinstance(products, (str, bytes)) or not isinstance(products, Iterable):
        raise TypeError(f"invalid products response type: {type(products).__name__}")

    validated_products: list[ProductResponse] = []
    for product in products:
        normalized = to_canonical_product(product)
        if normalized is not None:
            product = normalized
        try:
            validated_products.append(ProductResponse.model_validate(product))
        except ValidationError as exc:
            logger.warning("Skipping malformed product record: %s", exc)
    return validated_products
