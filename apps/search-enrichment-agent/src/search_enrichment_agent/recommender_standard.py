"""Local recommender contracts and baseline strategies for recommendation-agent."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

RecommendationEvidenceSource = Literal[
    "explicit",
    "product_correlation",
    "complement",
    "substitute",
    "bundle",
    "policy",
    "fallback",
]
FeedbackEventType = Literal[
    "impression",
    "click",
    "dismissal",
    "add_to_cart",
    "purchase",
    "explanation_view",
]
RecommendationModelKind = Literal[
    "deterministic_baseline",
    "classical_ml",
    "hybrid",
    "external",
]
RecommendationModelStage = Literal[
    "Development",
    "Staging",
    "Production",
    "Archived",
    "Baseline",
]


class RecommendationEvidence(BaseModel):
    """Evidence item supporting a recommendation decision."""

    model_config = ConfigDict(extra="forbid")

    source: RecommendationEvidenceSource
    reason: str = Field(min_length=1)
    weight: float = Field(default=0.0, ge=-1.0, le=1.0)
    source_sku: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)


class RecommendationCandidate(BaseModel):
    """Candidate row shared by candidate, rank, and compose flows."""

    model_config = ConfigDict(extra="forbid")

    sku: str = Field(min_length=1)
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    reason_codes: list[str] = Field(default_factory=list)
    evidence: list[RecommendationEvidence] = Field(default_factory=list)


class RankedRecommendation(BaseModel):
    """Ranked recommendation row emitted by a recommender engine."""

    model_config = ConfigDict(extra="forbid")
    sku: str
    rank: int = Field(ge=1)
    score: float = Field(ge=0.0, le=1.0)
    reason_codes: list[str]
    evidence: list[RecommendationEvidence]


class RecommendationDisplay(BaseModel):
    """Renderable product display payload for one recommendation card."""

    model_config = ConfigDict(extra="forbid")
    title: str
    image_url: str | None = None
    url: str
    category: str
    price: float | None = None
    availability: Literal["available", "unavailable", "unknown"] = "unknown"


class RecommendationCard(BaseModel):
    """UI-ready recommendation card."""

    model_config = ConfigDict(extra="forbid")
    sku: str
    display: RecommendationDisplay
    score: float = Field(ge=0.0, le=1.0)
    reason_codes: list[str]
    evidence: list[RecommendationEvidence]


class RecommendationModelMetadata(BaseModel):
    """Model lifecycle metadata aligned with MLET tracking guidance."""

    model_config = ConfigDict(extra="forbid")
    model_version: str
    model_type: RecommendationModelKind
    feature_version: str
    policy_version: str
    experiment_id: str
    stage: RecommendationModelStage = "Baseline"
    registry_uri: str | None = None
    training_run_id: str | None = None
    dataset_version: str | None = None
    model_card_uri: str | None = None


@dataclass(frozen=True, slots=True)
class RecommendationScoringContext:
    """Typed context used by ranking strategies."""

    tenant_id: str
    subject_ref: str
    intent_tokens: frozenset[str]
    category: str | None
    cart_skus: frozenset[str]


@dataclass(frozen=True, slots=True)
class RecommendationScoreResult:
    """Internal ranking result before response shaping."""

    sku: str
    score: float
    reason_codes: tuple[str, ...]
    evidence: tuple[RecommendationEvidence, ...]


# Strategy pattern: PEP 544 structural protocol for swappable rankers.
class RankingStrategy(Protocol):
    """Strategy interface for provider-agnostic recommendation scoring."""

    def score(
        self,
        candidate: RecommendationCandidate,
        context: RecommendationScoringContext,
    ) -> RecommendationScoreResult:
        """Return a score for a candidate within the current context."""
        raise NotImplementedError


class RecommendationEngineProtocol(Protocol):
    """Common surface that synchronous recommendation-agent rankers implement."""

    def rank(
        self,
        *,
        candidates: Sequence[RecommendationCandidate],
        context: RecommendationScoringContext,
        max_items: int,
    ) -> list[RankedRecommendation]:
        """Rank candidates for a context."""
        raise NotImplementedError

    def explain(
        self,
        *,
        sku: str,
        reason_codes: Sequence[str],
        evidence: Sequence[RecommendationEvidence],
    ) -> str:
        """Explain a recommendation from deterministic evidence."""
        raise NotImplementedError


class DeterministicBaselineRankingStrategy:
    """Classical deterministic baseline for hot-path recommendation ranking."""

    def score(
        self,
        candidate: RecommendationCandidate,
        context: RecommendationScoringContext,
    ) -> RecommendationScoreResult:
        reasons = dedupe_strings(candidate.reason_codes or ["input_score"])
        score = candidate.score
        candidate_words = _candidate_text(candidate)

        for evidence_item in candidate.evidence:
            score += evidence_item.weight
            if evidence_item.source == "complement":
                reasons.append("complementary_product")
            elif evidence_item.source == "substitute":
                reasons.append("substitute_product")
            elif evidence_item.source == "bundle":
                reasons.append("bundle_product")
            elif evidence_item.source == "product_correlation":
                reasons.append("product_correlation")

            if evidence_item.attributes.get("in_stock") is False:
                score -= 0.25
                reasons.append("low_availability")

        overlap = context.intent_tokens.intersection(candidate_words)
        if overlap:
            score += min(0.2, 0.04 * len(overlap))
            reasons.append("intent_overlap")

        if context.category and context.category.lower() in candidate_words:
            score += 0.06
            reasons.append("category_context")

        if candidate.sku in context.cart_skus:
            score -= 0.4
            reasons.append("already_in_cart")

        return RecommendationScoreResult(
            sku=candidate.sku,
            score=_bounded_score(score),
            reason_codes=tuple(dedupe_strings(reasons)),
            evidence=tuple(candidate.evidence),
        )


class StandardRecommendationEngine:
    """Rank/explain engine shared inside the recommendation-agent boundary."""

    def __init__(self, ranking_strategy: RankingStrategy | None = None) -> None:
        self._ranking_strategy = ranking_strategy or DeterministicBaselineRankingStrategy()

    def rank(
        self,
        *,
        candidates: Sequence[RecommendationCandidate],
        context: RecommendationScoringContext,
        max_items: int,
    ) -> list[RankedRecommendation]:
        scored = [self._ranking_strategy.score(candidate, context) for candidate in candidates]
        scored.sort(key=lambda item: (-item.score, item.sku))

        return [
            RankedRecommendation(
                sku=result.sku,
                rank=index,
                score=result.score,
                reason_codes=list(result.reason_codes),
                evidence=list(result.evidence),
            )
            for index, result in enumerate(scored[:max_items], start=1)
        ]

    def explain(
        self,
        *,
        sku: str,
        reason_codes: Sequence[str],
        evidence: Sequence[RecommendationEvidence],
    ) -> str:
        reason_text = ", ".join(dedupe_strings(reason_codes))
        if not reason_text:
            reason_text = "baseline relevance and available product correlation signals"

        evidence_text = "; ".join(
            f"{evidence_item.source}: {evidence_item.reason}" for evidence_item in evidence[:3]
        )
        if evidence_text:
            return f"{sku} was recommended because of {reason_text}. Evidence: {evidence_text}."
        return f"{sku} was recommended because of {reason_text}."


def merge_recommendation_candidate(
    candidates_by_sku: dict[str, RecommendationCandidate],
    incoming: RecommendationCandidate,
) -> None:
    """Merge a candidate into a SKU-keyed candidate map."""
    existing = candidates_by_sku.get(incoming.sku)
    if existing is None:
        candidates_by_sku[incoming.sku] = incoming
        return

    candidates_by_sku[incoming.sku] = RecommendationCandidate(
        sku=incoming.sku,
        score=max(existing.score, incoming.score),
        reason_codes=dedupe_strings([*existing.reason_codes, *incoming.reason_codes]),
        evidence=[*existing.evidence, *incoming.evidence],
    )


def subject_ref(customer_ref: str | None, session_id: str | None) -> str:
    """Resolve a pseudonymous recommendation subject reference."""
    return customer_ref or session_id or "anonymous"


def intent_tokens(intent: str | None, query: str | None) -> frozenset[str]:
    """Build normalized intent tokens from request intent and query text."""
    tokens = set(_tokenize(intent or ""))
    tokens.update(_tokenize(query or ""))
    return frozenset(tokens)


def normalize_string_list(value: object) -> list[str]:
    """Normalize optional scalar/list-like values into stripped strings."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if isinstance(value, Iterable):
        values: list[str] = []
        for item in value:
            text = str(item).strip()
            if text:
                values.append(text)
        return values
    text = str(value).strip()
    return [text] if text else []


def dedupe_strings(values: Iterable[str]) -> list[str]:
    """Return non-empty strings while preserving first-seen order."""
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def first_media_url(value: object) -> str | None:
    """Return the first normalized media URL from a scalar or list-like value."""
    media_values = normalize_string_list(value)
    return media_values[0] if media_values else None


def optional_float(value: object) -> float | None:
    """Return a float only for numeric values."""
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _candidate_text(candidate: RecommendationCandidate) -> frozenset[str]:
    parts: list[str] = [candidate.sku, *candidate.reason_codes]
    for evidence_item in candidate.evidence:
        parts.extend([evidence_item.source, evidence_item.reason])
        parts.extend(str(value) for value in evidence_item.attributes.values())
    return frozenset(_tokenize(" ".join(parts)))


def _tokenize(text: str) -> list[str]:
    stopwords = {"the", "and", "for", "with", "from", "that", "this", "into", "your"}
    cleaned = text.replace("/", " ").replace("-", " ").replace("_", " ")
    return [token for token in cleaned.lower().split() if len(token) > 2 and token not in stopwords]


def _bounded_score(score: float) -> float:
    return max(0.0, min(1.0, round(score, 4)))
