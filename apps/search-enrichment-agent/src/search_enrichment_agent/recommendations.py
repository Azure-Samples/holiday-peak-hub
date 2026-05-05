"""Recommendation-agent service schemas, orchestration, and REST routes."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, Literal, Protocol, cast
from uuid import uuid4

from fastapi import APIRouter, FastAPI, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from .adapters import SearchEnrichmentAdapters
from .enrichment_engine import SearchEnrichmentEngine
from .recommender_standard import (
    FeedbackEventType,
    RankedRecommendation,
    RankingStrategy,
    RecommendationCandidate,
    RecommendationCard,
    RecommendationDisplay,
    RecommendationEvidence,
    RecommendationEvidenceSource,
    RecommendationScoringContext,
    StandardRecommendationEngine,
    dedupe_strings,
    first_media_url,
    intent_tokens,
    merge_recommendation_candidate,
    normalize_string_list,
    optional_float,
    subject_ref,
)

_MODEL_VERSION = "deterministic-baseline-v1"
_FEATURE_VERSION = "recommenderiq-projection-v0"
_POLICY_VERSION = "recommendation-policy-v1"
_EXPERIMENT_ID = "baseline-control"


class RecommendationCandidatesRequest(BaseModel):
    """Request to generate explicit and product-correlated candidates."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="default", min_length=1)
    customer_ref: str | None = None
    session_id: str | None = None
    intent: str | None = None
    query: str | None = None
    page_type: str | None = None
    category: str | None = None
    seed_skus: list[str] = Field(default_factory=list, max_length=20)
    candidate_skus: list[str] = Field(default_factory=list, max_length=50)
    candidates: list[RecommendationCandidate] = Field(default_factory=list, max_length=50)
    cart_skus: list[str] = Field(default_factory=list, max_length=50)
    max_candidates: int = Field(default=10, ge=1, le=50)
    context: dict[str, Any] = Field(default_factory=dict)


class RecommendationCandidatesResponse(BaseModel):
    """Candidate-generation response with evidence and version metadata."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ready", "empty"]
    recommendation_set_id: str
    tenant_id: str
    customer_ref: str | None = None
    session_id: str | None = None
    candidates: list[RecommendationCandidate]
    model_version: str
    feature_version: str
    policy_version: str
    experiment_id: str
    projection_watermark: str
    fallback_reason: str | None = None


class RankRecommendationsRequest(BaseModel):
    """Request to rank recommendation candidates for a customer or session."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(default="default", min_length=1)
    customer_ref: str | None = None
    session_id: str | None = None
    intent: str | None = None
    query: str | None = None
    category: str | None = None
    cart_skus: list[str] = Field(default_factory=list, max_length=50)
    candidates: list[RecommendationCandidate] = Field(min_length=1, max_length=50)
    max_items: int = Field(default=10, ge=1, le=50)
    context: dict[str, Any] = Field(default_factory=dict)


class RankRecommendationsResponse(BaseModel):
    """Ranking response with model and feature versions."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["ranked", "empty"]
    recommendation_set_id: str
    tenant_id: str
    customer_ref: str | None = None
    session_id: str | None = None
    ranked: list[RankedRecommendation]
    model_version: str
    feature_version: str
    policy_version: str
    experiment_id: str
    projection_watermark: str
    fallback_reason: str | None = None


class ComposeRecommendationsRequest(BaseModel):
    """Request to compose recommendation cards from ranked items."""

    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(default="default", min_length=1)
    customer_ref: str | None = None
    session_id: str | None = None
    ranked_items: list[RecommendationCandidate] = Field(min_length=1, max_length=50)
    max_items: int = Field(default=3, ge=1, le=10)
    context: dict[str, Any] = Field(default_factory=dict)


class ComposeRecommendationsResponse(BaseModel):
    """UI readiness contract for composed recommendations."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["ready", "fallback"]
    ready_for_ui: bool
    recommendation_set_id: str
    tenant_id: str
    customer_ref: str | None = None
    session_id: str | None = None
    cards: list[RecommendationCard]
    model_version: str
    feature_version: str
    policy_version: str
    experiment_id: str
    projection_watermark: str
    fallback_reason: str | None = None


class RecommendationFeedbackRequest(BaseModel):
    """Feedback event tied to a recommendation set or card."""

    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(default="default", min_length=1)
    recommendation_set_id: str = Field(min_length=1)
    event_type: FeedbackEventType
    sku: str | None = None
    customer_ref: str | None = None
    session_id: str | None = None
    value: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendationFeedbackResponse(BaseModel):
    """Acknowledgement for accepted recommendation feedback."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["accepted"]
    feedback_id: str
    recommendation_set_id: str
    tenant_id: str
    recorded_at: str


class ExplainRecommendationRequest(BaseModel):
    """Request deterministic or model-assisted explanation for a recommendation."""

    model_config = ConfigDict(extra="forbid")
    tenant_id: str = Field(default="default", min_length=1)
    sku: str = Field(min_length=1)
    customer_ref: str | None = None
    session_id: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    evidence: list[RecommendationEvidence] = Field(default_factory=list)
    natural_language: bool = False
    context: dict[str, Any] = Field(default_factory=dict)


class ExplainRecommendationResponse(BaseModel):
    """Recommendation explanation response."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["explained"]
    tenant_id: str
    sku: str
    explanation: str
    reason_codes: list[str]
    evidence: list[RecommendationEvidence]
    model_version: str
    policy_version: str


class ModelStatusResponse(BaseModel):
    """Active recommendation model and governance status."""

    model_config = ConfigDict(extra="forbid")
    status: Literal["ready"]
    service: Literal["recommendation-agent"]
    hosted_by: Literal["search-enrichment-agent"]
    active_model: str
    model_type: Literal["deterministic_baseline"]
    feature_version: str
    policy_version: str
    experiment_id: str
    calibration_status: Literal["baseline"]
    drift_status: Literal["not_evaluated"]
    request_path_training: Literal["disabled"]
    updated_at: str


class RecommendationEngine:
    """Provider-agnostic recommendation engine façade with a baseline ranker."""

    def __init__(
        self,
        search_engine: SearchEnrichmentEngine | None = None,
        ranking_strategy: RankingStrategy | None = None,
    ) -> None:
        self._search_engine = search_engine or SearchEnrichmentEngine()
        self._standard_engine = StandardRecommendationEngine(ranking_strategy=ranking_strategy)

    def build_correlated_candidates(
        self,
        *,
        request: RecommendationCandidatesRequest,
        seed_products: dict[str, dict[str, Any]],
    ) -> list[RecommendationCandidate]:
        candidates_by_sku: dict[str, RecommendationCandidate] = {}
        for candidate in request.candidates:
            merge_recommendation_candidate(candidates_by_sku, candidate)
        for candidate_sku in request.candidate_skus:
            merge_recommendation_candidate(
                candidates_by_sku,
                RecommendationCandidate(
                    sku=candidate_sku,
                    score=0.55,
                    reason_codes=["explicit_candidate"],
                    evidence=[
                        RecommendationEvidence(
                            source="explicit",
                            reason="Candidate supplied by caller",
                            weight=0.0,
                        )
                    ],
                ),
            )

        for seed_sku, approved_truth in seed_products.items():
            for candidate in self._candidates_from_seed(seed_sku, approved_truth):
                merge_recommendation_candidate(candidates_by_sku, candidate)

        ranked_candidates = sorted(
            candidates_by_sku.values(),
            key=lambda item: (-item.score, item.sku),
        )
        return ranked_candidates[: request.max_candidates]

    def rank(
        self,
        request: RankRecommendationsRequest,
    ) -> list[RankedRecommendation]:
        context = RecommendationScoringContext(
            tenant_id=request.tenant_id,
            subject_ref=subject_ref(request.customer_ref, request.session_id),
            intent_tokens=intent_tokens(request.intent, request.query),
            category=request.category,
            cart_skus=frozenset(request.cart_skus),
        )
        return self._standard_engine.rank(
            candidates=request.candidates,
            context=context,
            max_items=request.max_items,
        )

    def explain(self, request: ExplainRecommendationRequest) -> str:
        return self._standard_engine.explain(
            sku=request.sku,
            reason_codes=request.reason_codes,
            evidence=request.evidence,
        )

    def _candidates_from_seed(
        self,
        seed_sku: str,
        approved_truth: dict[str, Any],
    ) -> list[RecommendationCandidate]:
        enriched = self._search_engine.build_simple_fields(approved_truth)
        seed_name = str(
            approved_truth.get("name")
            or approved_truth.get("title")
            or approved_truth.get("product_name")
            or seed_sku
        )
        field_specs: tuple[tuple[str, RecommendationEvidenceSource, str, float, float], ...] = (
            ("complementary_products", "complement", "complementary_product", 0.7, 0.12),
            ("substitute_products", "substitute", "substitute_product", 0.62, 0.08),
            ("bundles", "bundle", "bundle_product", 0.68, 0.1),
            ("bundle_products", "bundle", "bundle_product", 0.68, 0.1),
            ("frequently_bought_together", "bundle", "frequently_bought_together", 0.68, 0.1),
            ("related_products", "product_correlation", "product_correlation", 0.64, 0.09),
        )

        candidates: list[RecommendationCandidate] = []
        for field_name, source, reason_code, base_score, weight in field_specs:
            values = normalize_string_list(
                approved_truth.get(field_name) or enriched.get(field_name)
            )
            for candidate_sku in values:
                if candidate_sku == seed_sku:
                    continue
                candidates.append(
                    RecommendationCandidate(
                        sku=candidate_sku,
                        score=base_score,
                        reason_codes=[reason_code],
                        evidence=[
                            RecommendationEvidence(
                                source=source,
                                reason=f"Correlated with {seed_name}",
                                weight=weight,
                                source_sku=seed_sku,
                                attributes={
                                    "seed_sku": seed_sku,
                                    "seed_name": seed_name,
                                    "source_field": field_name,
                                    "category": approved_truth.get("category"),
                                },
                            )
                        ],
                    )
                )
        return candidates


class RecommendationOrchestrator:
    """Agent-owned orchestration for RecommenderIQ REST and MCP surfaces."""

    def __init__(self, adapters: SearchEnrichmentAdapters, engine: RecommendationEngine) -> None:
        self._adapters = adapters
        self._engine = engine

    async def candidates(
        self,
        request: RecommendationCandidatesRequest,
    ) -> RecommendationCandidatesResponse:
        seed_products = await self._fetch_seed_products(request.seed_skus)
        candidates = self._engine.build_correlated_candidates(
            request=request,
            seed_products=seed_products,
        )
        fallback_reason = None if candidates else "no_candidate_signals"
        return RecommendationCandidatesResponse(
            status="ready" if candidates else "empty",
            recommendation_set_id=_new_recommendation_set_id(),
            tenant_id=request.tenant_id,
            customer_ref=request.customer_ref,
            session_id=request.session_id,
            candidates=candidates,
            model_version=_MODEL_VERSION,
            feature_version=_FEATURE_VERSION,
            policy_version=_POLICY_VERSION,
            experiment_id=_EXPERIMENT_ID,
            projection_watermark=_utc_now(),
            fallback_reason=fallback_reason,
        )

    async def rank(self, request: RankRecommendationsRequest) -> RankRecommendationsResponse:
        ranked = self._engine.rank(request)
        return RankRecommendationsResponse(
            status="ranked" if ranked else "empty",
            recommendation_set_id=_new_recommendation_set_id(),
            tenant_id=request.tenant_id,
            customer_ref=request.customer_ref,
            session_id=request.session_id,
            ranked=ranked,
            model_version=_MODEL_VERSION,
            feature_version=_FEATURE_VERSION,
            policy_version=_POLICY_VERSION,
            experiment_id=_EXPERIMENT_ID,
            projection_watermark=_utc_now(),
            fallback_reason=None if ranked else "no_rankable_candidates",
        )

    async def compose(
        self,
        request: ComposeRecommendationsRequest,
    ) -> ComposeRecommendationsResponse:
        sorted_items = sorted(
            request.ranked_items,
            key=lambda item: (-item.score, item.sku),
        )[: request.max_items]
        product_contexts = await self._fetch_seed_products([item.sku for item in sorted_items])
        cards = [self._build_card(item, product_contexts.get(item.sku)) for item in sorted_items]
        return ComposeRecommendationsResponse(
            status="ready" if cards else "fallback",
            ready_for_ui=bool(cards),
            recommendation_set_id=_new_recommendation_set_id(),
            tenant_id=request.tenant_id,
            customer_ref=request.customer_ref,
            session_id=request.session_id,
            cards=cards,
            model_version=_MODEL_VERSION,
            feature_version=_FEATURE_VERSION,
            policy_version=_POLICY_VERSION,
            experiment_id=_EXPERIMENT_ID,
            projection_watermark=_utc_now(),
            fallback_reason=None if cards else "no_cards_composed",
        )

    async def feedback(
        self,
        request: RecommendationFeedbackRequest,
    ) -> RecommendationFeedbackResponse:
        feedback_id = f"feedback-{uuid4()}"
        recorded_at = _utc_now()
        await self._adapters.recommendation_feedback.record(
            {
                "feedback_id": feedback_id,
                "tenant_id": request.tenant_id,
                "recommendation_set_id": request.recommendation_set_id,
                "event_type": request.event_type,
                "sku": request.sku,
                "customer_ref": request.customer_ref,
                "session_id": request.session_id,
                "value": request.value,
                "metadata": request.metadata,
                "recorded_at": recorded_at,
            }
        )
        return RecommendationFeedbackResponse(
            status="accepted",
            feedback_id=feedback_id,
            recommendation_set_id=request.recommendation_set_id,
            tenant_id=request.tenant_id,
            recorded_at=recorded_at,
        )

    async def explain(
        self,
        request: ExplainRecommendationRequest,
    ) -> ExplainRecommendationResponse:
        return ExplainRecommendationResponse(
            status="explained",
            tenant_id=request.tenant_id,
            sku=request.sku,
            explanation=self._engine.explain(request),
            reason_codes=dedupe_strings(request.reason_codes),
            evidence=request.evidence,
            model_version=_MODEL_VERSION,
            policy_version=_POLICY_VERSION,
        )

    async def model_status(self) -> ModelStatusResponse:
        return ModelStatusResponse(
            status="ready",
            service="recommendation-agent",
            hosted_by="search-enrichment-agent",
            active_model=_MODEL_VERSION,
            model_type="deterministic_baseline",
            feature_version=_FEATURE_VERSION,
            policy_version=_POLICY_VERSION,
            experiment_id=_EXPERIMENT_ID,
            calibration_status="baseline",
            drift_status="not_evaluated",
            request_path_training="disabled",
            updated_at=_utc_now(),
        )

    async def _fetch_seed_products(self, skus: Sequence[str]) -> dict[str, dict[str, Any]]:
        async def fetch_product(sku: str) -> tuple[str, dict[str, Any] | None]:
            try:
                return sku, await self._adapters.approved_truth.get_approved_data(sku)
            except (RuntimeError, ValueError, TypeError):
                return sku, None

        tasks: dict[str, asyncio.Task[tuple[str, dict[str, Any] | None]]] = {}
        async with asyncio.TaskGroup() as task_group:
            for sku in dedupe_strings(skus):
                tasks[sku] = task_group.create_task(fetch_product(sku))

        products: dict[str, dict[str, Any]] = {}
        for task in tasks.values():
            sku, product = task.result()
            if product is not None:
                products[sku] = product
        return products

    def _build_card(
        self,
        item: RecommendationCandidate,
        product: dict[str, Any] | None,
    ) -> RecommendationCard:
        product_data = product or {}
        title = str(
            product_data.get("name")
            or product_data.get("title")
            or product_data.get("product_name")
            or item.sku
        )
        category = str(product_data.get("category") or product_data.get("category_id") or "product")
        image_url = first_media_url(product_data.get("images") or product_data.get("media"))
        price = optional_float(product_data.get("price"))
        availability = "unknown"
        if product_data.get("in_stock") is True:
            availability = "available"
        elif product_data.get("in_stock") is False:
            availability = "unavailable"

        return RecommendationCard(
            sku=item.sku,
            display=RecommendationDisplay(
                title=title,
                image_url=image_url,
                url=str(
                    product_data.get("url")
                    or product_data.get("product_url")
                    or f"/products/{item.sku}"
                ),
                category=category,
                price=price,
                availability=availability,
            ),
            score=item.score,
            reason_codes=dedupe_strings(item.reason_codes),
            evidence=item.evidence,
        )


class RecommendationAgentProtocol(Protocol):
    """Protocol surface implemented by the evolved recommendation agent."""

    async def recommendation_candidates(
        self,
        request: RecommendationCandidatesRequest,
    ) -> RecommendationCandidatesResponse:
        """Generate recommendation candidates."""

    async def recommendation_rank(
        self,
        request: RankRecommendationsRequest,
    ) -> RankRecommendationsResponse:
        """Rank recommendation candidates."""

    async def recommendation_compose(
        self,
        request: ComposeRecommendationsRequest,
    ) -> ComposeRecommendationsResponse:
        """Compose recommendation cards."""

    async def recommendation_feedback(
        self,
        request: RecommendationFeedbackRequest,
    ) -> RecommendationFeedbackResponse:
        """Record recommendation feedback."""

    async def recommendation_explain(
        self,
        request: ExplainRecommendationRequest,
    ) -> ExplainRecommendationResponse:
        """Explain a recommendation."""

    async def recommendation_model_status(self) -> ModelStatusResponse:
        """Return model status."""


def register_recommendation_routes(app: FastAPI) -> None:
    """Register recommendation-agent REST endpoints on a standard app."""
    router = APIRouter(tags=["Recommendations"])

    @router.post(
        "/recommendations/candidates",
        response_model=RecommendationCandidatesResponse,
    )
    async def candidates(
        payload: RecommendationCandidatesRequest,
        request: Request,
    ) -> RecommendationCandidatesResponse:
        return await _agent(request).recommendation_candidates(payload)

    @router.post("/recommendations/rank", response_model=RankRecommendationsResponse)
    async def rank(
        payload: RankRecommendationsRequest,
        request: Request,
    ) -> RankRecommendationsResponse:
        return await _agent(request).recommendation_rank(payload)

    @router.post("/recommendations/compose", response_model=ComposeRecommendationsResponse)
    async def compose(
        payload: ComposeRecommendationsRequest,
        request: Request,
    ) -> ComposeRecommendationsResponse:
        return await _agent(request).recommendation_compose(payload)

    @router.post("/recommendations/feedback", response_model=RecommendationFeedbackResponse)
    async def feedback(
        payload: RecommendationFeedbackRequest,
        request: Request,
    ) -> RecommendationFeedbackResponse:
        return await _agent(request).recommendation_feedback(payload)

    @router.post("/recommendations/explain", response_model=ExplainRecommendationResponse)
    async def explain(
        payload: ExplainRecommendationRequest,
        request: Request,
    ) -> ExplainRecommendationResponse:
        return await _agent(request).recommendation_explain(payload)

    @router.get("/models/status", response_model=ModelStatusResponse)
    async def model_status(request: Request) -> ModelStatusResponse:
        return await _agent(request).recommendation_model_status()

    app.include_router(router)


def _agent(request: Request) -> RecommendationAgentProtocol:
    agent = getattr(request.app.state, "agent", None)
    required_methods = (
        "recommendation_candidates",
        "recommendation_rank",
        "recommendation_compose",
        "recommendation_feedback",
        "recommendation_explain",
        "recommendation_model_status",
    )
    if agent is None or not all(
        callable(getattr(agent, method_name, None)) for method_name in required_methods
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Recommendation capability is unavailable",
        )
    return cast(RecommendationAgentProtocol, agent)


def _response_payload(response: BaseModel) -> dict[str, Any]:
    return response.model_dump(mode="json")


def model_to_payload(response: BaseModel) -> dict[str, Any]:
    """Expose consistent Pydantic JSON dumping for MCP tool wrappers."""
    return _response_payload(response)


def _new_recommendation_set_id() -> str:
    return f"recset-{uuid4()}"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
