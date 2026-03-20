"""Brand-shopping contract routes for notebook/UI parity."""

import logging
from typing import Any, Literal

import asyncpg
import httpx
from circuitbreaker import CircuitBreakerError
from crud_service.auth import User, get_current_user
from crud_service.integrations import get_agent_client
from crud_service.repositories import ProductRepository, UserRepository
from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()
product_repo = ProductRepository()
user_repo = UserRepository()
agent_client = get_agent_client()
logger = logging.getLogger(__name__)
IDENTIFIER_PATTERN = r"^[A-Za-z0-9._-]+$"
DATA_ACCESS_EXCEPTIONS = (RuntimeError, asyncpg.PostgresError)
AGENT_FALLBACK_EXCEPTIONS = (httpx.HTTPError, CircuitBreakerError)


def _round_money(value: float) -> float:
    """Round monetary values to two decimals."""
    return round(float(value), 2)


def _to_positive_price(value: Any) -> float | None:
    """Normalize a numeric price value."""
    if not isinstance(value, (int, float)):
        return None
    price = _round_money(value)
    if price <= 0:
        return None
    return price


async def _resolve_user_profile(customer_id: str) -> dict[str, Any] | None:
    """Resolve a customer profile by user id first, then Entra id."""
    user = await user_repo.get_by_id(customer_id)
    if user:
        return user
    return await user_repo.get_by_entra_id(customer_id)


def _to_non_empty_string(value: Any) -> str | None:
    """Normalize to non-empty string or None."""
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_tier(value: Any) -> str:
    """Normalize customer tier with deterministic fallback."""
    tier = _to_non_empty_string(value)
    return tier.lower() if tier else "standard"


def _is_staff_or_admin(current_user: User) -> bool:
    """Return whether the current user has elevated access."""
    return bool({"staff", "admin"}.intersection(set(current_user.roles or [])))


def _ensure_customer_scope_access(customer_id: str, current_user: User) -> None:
    """Enforce ownership for customers while allowing staff/admin access."""
    if _is_staff_or_admin(current_user):
        return

    if "customer" in set(current_user.roles or []) and customer_id == current_user.user_id:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden",
    )


def _dedupe_candidates(
    candidates: list["RecommendationCandidate"],
) -> list["RecommendationCandidate"]:
    """Deduplicate recommendation candidates by SKU using max score."""
    max_scores_by_sku: dict[str, float] = {}
    for candidate in candidates:
        previous = max_scores_by_sku.get(candidate.sku)
        if previous is None or candidate.score > previous:
            max_scores_by_sku[candidate.sku] = candidate.score

    return [
        RecommendationCandidate(sku=sku, score=score) for sku, score in max_scores_by_sku.items()
    ]


class CatalogProductResponse(BaseModel):
    """Canonical catalog product contract."""

    model_config = ConfigDict(extra="forbid")

    sku: str
    name: str
    description: str
    category_id: str
    price: float
    currency: Literal["usd"] = "usd"
    in_stock: bool


class CustomerProfileResponse(BaseModel):
    """Canonical customer profile contract."""

    model_config = ConfigDict(extra="forbid")

    customer_id: str
    email: str | None = None
    name: str | None = None
    phone: str | None = None
    tier: str = "standard"
    crm_profile: dict[str, Any] | None = None
    personalization: dict[str, Any] | None = None


class PricingOffersRequest(BaseModel):
    """Offer generation request."""

    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(min_length=1, pattern=IDENTIFIER_PATTERN)
    sku: str = Field(min_length=1, pattern=IDENTIFIER_PATTERN)
    quantity: int = Field(ge=1, le=100)
    currency: Literal["usd"] = "usd"


class PricingOffer(BaseModel):
    """Single offer row."""

    model_config = ConfigDict(extra="forbid")

    code: str
    title: str
    amount: float
    offer_type: Literal["bulk", "loyalty", "dynamic"]
    source: Literal["rule", "agent"]


class PricingOffersResponse(BaseModel):
    """Offer generation response."""

    model_config = ConfigDict(extra="forbid")

    customer_id: str
    sku: str
    quantity: int
    currency: Literal["usd"] = "usd"
    base_price: float
    offers: list[PricingOffer]
    final_price: float


class RecommendationCandidate(BaseModel):
    """Recommendation candidate input row."""

    model_config = ConfigDict(extra="forbid")

    sku: str = Field(min_length=1, pattern=IDENTIFIER_PATTERN)
    score: float = Field(default=0.5, ge=0.0, le=1.0)


class RankRecommendationsRequest(BaseModel):
    """Recommendation ranking request."""

    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(min_length=1, pattern=IDENTIFIER_PATTERN)
    candidates: list[RecommendationCandidate] = Field(min_length=1, max_length=50)


class RankedRecommendation(BaseModel):
    """Recommendation ranking output row."""

    model_config = ConfigDict(extra="forbid")

    sku: str
    score: float
    reason_codes: list[str]


class RankRecommendationsResponse(BaseModel):
    """Recommendation ranking response."""

    model_config = ConfigDict(extra="forbid")

    customer_id: str
    ranked: list[RankedRecommendation]


class ComposeRecommendationsRequest(BaseModel):
    """Recommendation composition request."""

    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(min_length=1, pattern=IDENTIFIER_PATTERN)
    ranked_items: list[RecommendationCandidate] = Field(min_length=1, max_length=50)
    max_items: int = Field(default=3, ge=1, le=10)


class ComposedRecommendation(BaseModel):
    """Recommendation composition output row."""

    model_config = ConfigDict(extra="forbid")

    sku: str
    title: str
    score: float
    message: str


class ComposeRecommendationsResponse(BaseModel):
    """Recommendation composition response."""

    model_config = ConfigDict(extra="forbid")

    customer_id: str
    headline: str
    recommendations: list[ComposedRecommendation]


@router.get("/catalog/products/{sku}", response_model=CatalogProductResponse)
async def get_catalog_product(sku: str = Path(min_length=1, pattern=IDENTIFIER_PATTERN)):
    """Get canonical product contract by SKU."""
    try:
        product = await product_repo.get_by_id(sku)
    except DATA_ACCESS_EXCEPTIONS as exc:
        logger.warning("Catalog product lookup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalog service is temporarily unavailable",
        ) from exc

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    price = _to_positive_price(product.get("price"))
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalog product pricing is unavailable",
        )

    resolved_sku = _to_non_empty_string(product.get("id")) or sku
    name = _to_non_empty_string(product.get("name"))
    description = _to_non_empty_string(product.get("description"))
    category_id = _to_non_empty_string(product.get("category_id"))

    if not name or not description or not category_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Catalog product contract is incomplete",
        )

    return CatalogProductResponse(
        sku=resolved_sku,
        name=name,
        description=description,
        category_id=category_id,
        price=price,
        in_stock=bool(product.get("in_stock", True)),
    )


@router.get("/customers/{customer_id}/profile", response_model=CustomerProfileResponse)
async def get_customer_profile(
    customer_id: str = Path(min_length=1, pattern=IDENTIFIER_PATTERN),
    current_user: User = Depends(get_current_user),
):
    """Get canonical customer profile contract by customer id."""
    is_staff_or_admin = _is_staff_or_admin(current_user)

    try:
        user = await _resolve_user_profile(customer_id)
    except DATA_ACCESS_EXCEPTIONS as exc:
        logger.warning("Customer profile lookup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Customer profile service is temporarily unavailable",
        ) from exc

    if not user:
        if not is_staff_or_admin and customer_id != current_user.user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    if not is_staff_or_admin:
        owner_ids = {
            str(user.get("id") or ""),
            str(user.get("user_id") or ""),
            str(user.get("entra_id") or ""),
            customer_id,
        }
        if current_user.user_id not in owner_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )

    crm_profile = None
    personalization = None
    try:
        crm_profile = await agent_client.get_customer_profile(customer_id)
    except AGENT_FALLBACK_EXCEPTIONS:
        logger.warning(
            "CRM profile enrichment unavailable for customer_id=%s",
            customer_id,
            exc_info=True,
        )
        crm_profile = None
    try:
        personalization = await agent_client.get_personalization(customer_id)
    except AGENT_FALLBACK_EXCEPTIONS:
        logger.warning(
            "Personalization enrichment unavailable for customer_id=%s",
            customer_id,
            exc_info=True,
        )
        personalization = None

    tier = _normalize_tier(
        (crm_profile or {}).get("tier") if isinstance(crm_profile, dict) else None
    )
    if tier == "standard":
        tier = _normalize_tier(user.get("tier"))

    return CustomerProfileResponse(
        customer_id=customer_id,
        email=_to_non_empty_string(user.get("email")),
        name=_to_non_empty_string(user.get("name")),
        phone=_to_non_empty_string(user.get("phone")),
        tier=tier,
        crm_profile=crm_profile if isinstance(crm_profile, dict) else None,
        personalization=personalization if isinstance(personalization, dict) else None,
    )


@router.post("/pricing/offers", response_model=PricingOffersResponse)
async def get_pricing_offers(
    request: PricingOffersRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate deterministic pricing offers for a customer and SKU."""
    _ensure_customer_scope_access(request.customer_id, current_user)

    try:
        product = await product_repo.get_by_id(request.sku)
        user = await _resolve_user_profile(request.customer_id)
    except DATA_ACCESS_EXCEPTIONS as exc:
        logger.warning("Pricing offer lookup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pricing service is temporarily unavailable",
        ) from exc

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    base_unit_price = _to_positive_price(product.get("price"))
    if base_unit_price is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Product pricing is unavailable",
        )

    base_price = _round_money(base_unit_price * request.quantity)
    offers: list[PricingOffer] = []

    if request.quantity >= 5:
        amount = _round_money(base_price * 0.10)
        offers.append(
            PricingOffer(
                code="bulk-10",
                title="Bulk quantity discount",
                amount=amount,
                offer_type="bulk",
                source="rule",
            )
        )
    elif request.quantity >= 3:
        amount = _round_money(base_price * 0.05)
        offers.append(
            PricingOffer(
                code="bulk-5",
                title="Bulk quantity discount",
                amount=amount,
                offer_type="bulk",
                source="rule",
            )
        )

    loyalty_multiplier = 0.0
    try:
        crm_profile = await agent_client.get_customer_profile(request.customer_id)
    except AGENT_FALLBACK_EXCEPTIONS:
        logger.warning(
            "Loyalty profile enrichment unavailable for customer_id=%s",
            request.customer_id,
            exc_info=True,
        )
        crm_profile = None
    tier = str((crm_profile or {}).get("tier") or user.get("tier") or "standard").lower()
    if tier == "gold":
        loyalty_multiplier = 0.10
    elif tier == "silver":
        loyalty_multiplier = 0.05
    if loyalty_multiplier > 0:
        loyalty_amount = _round_money(base_price * loyalty_multiplier)
        offers.append(
            PricingOffer(
                code=f"loyalty-{tier}",
                title=f"{tier.title()} loyalty discount",
                amount=loyalty_amount,
                offer_type="loyalty",
                source="rule",
            )
        )

    try:
        dynamic_unit_price = await agent_client.calculate_dynamic_pricing(request.sku)
    except AGENT_FALLBACK_EXCEPTIONS:
        logger.warning(
            "Dynamic pricing unavailable for sku=%s",
            request.sku,
            exc_info=True,
        )
        dynamic_unit_price = None
    if isinstance(dynamic_unit_price, (int, float)):
        dynamic_unit_price = _round_money(dynamic_unit_price)
        if 0 < dynamic_unit_price < base_unit_price:
            dynamic_amount = _round_money((base_unit_price - dynamic_unit_price) * request.quantity)
            offers.append(
                PricingOffer(
                    code="dynamic-price",
                    title="Dynamic price optimization",
                    amount=dynamic_amount,
                    offer_type="dynamic",
                    source="agent",
                )
            )

    total_discount = _round_money(sum(offer.amount for offer in offers))
    final_price = _round_money(max(base_price - total_discount, 0.0))

    return PricingOffersResponse(
        customer_id=request.customer_id,
        sku=request.sku,
        quantity=request.quantity,
        currency=request.currency,
        base_price=base_price,
        offers=offers,
        final_price=final_price,
    )


@router.post("/recommendations/rank", response_model=RankRecommendationsResponse)
async def rank_recommendations(
    request: RankRecommendationsRequest,
    current_user: User = Depends(get_current_user),
):
    """Rank recommendation candidates with deterministic tie-breaking."""
    _ensure_customer_scope_access(request.customer_id, current_user)

    try:
        user = await _resolve_user_profile(request.customer_id)
    except DATA_ACCESS_EXCEPTIONS as exc:
        logger.warning("Recommendation rank lookup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is temporarily unavailable",
        ) from exc

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    preferred_categories: set[str] = set()
    try:
        personalization = await agent_client.get_personalization(request.customer_id)
        if isinstance(personalization, dict):
            categories = personalization.get("preferred_categories")
            if isinstance(categories, list):
                preferred_categories = {
                    str(category).strip().lower()
                    for category in categories
                    if str(category).strip()
                }
    except AGENT_FALLBACK_EXCEPTIONS:
        logger.warning(
            "Recommendation personalization unavailable for customer_id=%s",
            request.customer_id,
            exc_info=True,
        )
        preferred_categories = set()

    unique_candidates = _dedupe_candidates(request.candidates)

    ranked_rows: list[RankedRecommendation] = []
    for candidate in unique_candidates:
        reason_codes = ["input_score"]
        final_score = candidate.score
        product: dict[str, Any] | None = None

        try:
            product = await product_repo.get_by_id(candidate.sku)
        except DATA_ACCESS_EXCEPTIONS:
            logger.warning(
                "Recommendation product lookup failed for sku=%s; continuing without product context",
                candidate.sku,
                exc_info=True,
            )
            product = None

        if isinstance(product, dict):
            category = str(product.get("category_id") or "").strip().lower()
            if category and category in preferred_categories:
                final_score += 0.15
                reason_codes.append("category_preference")
            if product.get("in_stock") is False:
                final_score -= 0.25
                reason_codes.append("low_availability")

        bounded_score = max(0.0, min(1.0, _round_money(final_score)))
        ranked_rows.append(
            RankedRecommendation(
                sku=candidate.sku,
                score=bounded_score,
                reason_codes=reason_codes,
            )
        )

    ranked_rows.sort(key=lambda item: (-item.score, item.sku))

    return RankRecommendationsResponse(customer_id=request.customer_id, ranked=ranked_rows)


@router.post("/recommendations/compose", response_model=ComposeRecommendationsResponse)
async def compose_recommendations(
    request: ComposeRecommendationsRequest,
    current_user: User = Depends(get_current_user),
):
    """Compose recommendation cards from ranked recommendation items."""
    _ensure_customer_scope_access(request.customer_id, current_user)

    try:
        user = await _resolve_user_profile(request.customer_id)
    except DATA_ACCESS_EXCEPTIONS as exc:
        logger.warning("Recommendation compose lookup failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation service is temporarily unavailable",
        ) from exc

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    sorted_candidates = sorted(
        _dedupe_candidates(request.ranked_items),
        key=lambda item: (-item.score, item.sku),
    )

    recommendations: list[ComposedRecommendation] = []
    for candidate in sorted_candidates[: request.max_items]:
        title = candidate.sku
        try:
            product = await product_repo.get_by_id(candidate.sku)
        except DATA_ACCESS_EXCEPTIONS:
            logger.warning(
                "Recommendation composition product lookup failed for sku=%s; using SKU as title",
                candidate.sku,
                exc_info=True,
            )
            product = None
        if isinstance(product, dict) and product.get("name"):
            title = str(product["name"])

        recommendations.append(
            ComposedRecommendation(
                sku=candidate.sku,
                title=title,
                score=_round_money(candidate.score),
                message=f"Recommended for {request.customer_id} based on shopping intent",
            )
        )

    return ComposeRecommendationsResponse(
        customer_id=request.customer_id,
        headline=f"Top picks for {request.customer_id}",
        recommendations=recommendations,
    )
