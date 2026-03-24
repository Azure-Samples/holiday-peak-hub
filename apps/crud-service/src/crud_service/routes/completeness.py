"""Completeness routes — product completeness scoring reports."""

from collections import defaultdict
from datetime import UTC, datetime, timedelta

from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter()


class CompletenessRepository(BaseRepository):
    """Repository for completeness reports."""

    def __init__(self):
        super().__init__(container_name="completeness_reports")


completeness_repo = CompletenessRepository()
proposed_attr_repo = BaseRepository(container_name="proposed_attributes")
audit_repo = BaseRepository(container_name="audit_events")


class GapDetail(BaseModel):
    """Details of a single missing or incomplete field."""

    field_name: str
    required: bool = True
    reason: str | None = None


class CompletenessReportResponse(BaseModel):
    """Response model for a product completeness report."""

    id: str
    entity_id: str
    score: float
    required_fields: int
    completed_fields: int
    gaps: list[GapDetail] = Field(default_factory=list)
    category_id: str | None = None
    schema_version: str | None = None
    generated_at: str | None = None


class CompletenessSummaryResponse(BaseModel):
    """Aggregate completeness statistics."""

    total_products: int
    average_score: float
    fully_complete: int
    needs_enrichment: int
    critical_gaps: int


class TruthAnalyticsSummaryResponse(BaseModel):
    """Canonical truth analytics summary payload."""

    overall_completeness: float
    total_products: int
    enrichment_jobs_processed: int
    auto_approved: int
    sent_to_hitl: int
    queue_pending: int
    queue_approved: int
    queue_rejected: int
    avg_review_time_minutes: float
    acp_exports: int
    ucp_exports: int


class TruthAnalyticsCompletenessRow(BaseModel):
    """Category-level completeness metrics."""

    category: str
    completeness: float
    product_count: int


class TruthAnalyticsThroughputPoint(BaseModel):
    """Time-window throughput point."""

    timestamp: str
    ingested: int
    enriched: int
    approved: int
    rejected: int


def _to_float(value: object | None) -> float:
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _to_datetime(value: object | None) -> datetime | None:
    if value is None or not isinstance(value, str):
        return None

    candidate = value.strip()
    if not candidate:
        return None

    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _extract_event_time(item: dict, candidates: list[str]) -> datetime | None:
    for key in candidates:
        maybe_dt = _to_datetime(item.get(key))
        if maybe_dt is not None:
            return maybe_dt
    return None


def _matches_any_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in keywords)


def _extract_export_target(item: dict) -> str:
    action = str(item.get("action") or "").lower()
    metadata = item.get("metadata")
    if isinstance(metadata, dict):
        for key in ("target", "destination", "export_type", "format", "channel"):
            raw_value = metadata.get(key)
            if isinstance(raw_value, str) and raw_value.strip():
                return raw_value.lower()
    return action


def _average_review_time_minutes(proposals: list[dict]) -> float:
    durations: list[float] = []
    for item in proposals:
        proposed_at = _extract_event_time(item, ["proposed_at", "created_at", "timestamp"])
        reviewed_at = _extract_event_time(item, ["reviewed_at", "updated_at", "timestamp"])
        if proposed_at is None or reviewed_at is None:
            continue
        if reviewed_at < proposed_at:
            continue
        durations.append((reviewed_at - proposed_at).total_seconds() / 60.0)

    if not durations:
        return 0.0
    return sum(durations) / len(durations)


def _build_bucket_starts(
    *, now: datetime, window_hours: int, interval_minutes: int
) -> list[datetime]:
    total_minutes = max(window_hours * 60, interval_minutes)
    bucket_count = max(1, total_minutes // interval_minutes)

    window_start = now - timedelta(minutes=total_minutes)
    aligned_minute = (window_start.minute // interval_minutes) * interval_minutes
    aligned_start = window_start.replace(minute=aligned_minute, second=0, microsecond=0)

    return [
        aligned_start + timedelta(minutes=index * interval_minutes)
        for index in range(bucket_count + 1)
    ]


def _bucket_for_timestamp(
    event_time: datetime,
    *,
    bucket_starts: list[datetime],
    interval_minutes: int,
) -> datetime | None:
    first_bucket = bucket_starts[0]
    last_bucket_end = bucket_starts[-1] + timedelta(minutes=interval_minutes)
    if event_time < first_bucket or event_time >= last_bucket_end:
        return None

    offset_minutes = int((event_time - first_bucket).total_seconds() // 60)
    bucket_index = offset_minutes // interval_minutes
    if bucket_index < 0:
        return None
    if bucket_index >= len(bucket_starts):
        bucket_index = len(bucket_starts) - 1
    return bucket_starts[bucket_index]


@router.get("/completeness/summary", response_model=CompletenessSummaryResponse)
async def get_completeness_summary():
    """Aggregate completeness statistics across all products."""
    items = await completeness_repo.query(query="SELECT * FROM c")
    if not items:
        return CompletenessSummaryResponse(
            total_products=0,
            average_score=0.0,
            fully_complete=0,
            needs_enrichment=0,
            critical_gaps=0,
        )
    total = len(items)
    scores = [i.get("score", 0.0) for i in items]
    avg_score = sum(scores) / total
    fully_complete = sum(1 for score in scores if score >= 1.0)
    needs_enrichment = sum(1 for score in scores if 0.70 <= score < 1.0)
    critical_gaps = sum(1 for score in scores if score < 0.70)
    return CompletenessSummaryResponse(
        total_products=total,
        average_score=avg_score,
        fully_complete=fully_complete,
        needs_enrichment=needs_enrichment,
        critical_gaps=critical_gaps,
    )


@router.get("/truth/analytics/summary", response_model=TruthAnalyticsSummaryResponse)
async def get_truth_analytics_summary():
    """Return canonical truth analytics summary owned by CRUD service."""
    completeness_items = await completeness_repo.query(query="SELECT * FROM c")
    proposal_items = await proposed_attr_repo.query(query="SELECT * FROM c")
    audit_items = await audit_repo.query(query="SELECT * FROM c")

    scores = [
        _to_float(item.get("score", item.get("completeness_score"))) for item in completeness_items
    ]
    total_products = len(completeness_items)
    overall_completeness = (sum(scores) / total_products) if total_products else 0.0

    queue_pending = sum(
        1 for item in proposal_items if str(item.get("status", "")).lower() == "pending"
    )
    queue_approved = sum(
        1 for item in proposal_items if str(item.get("status", "")).lower() == "approved"
    )
    queue_rejected = sum(
        1 for item in proposal_items if str(item.get("status", "")).lower() == "rejected"
    )
    sent_to_hitl = queue_pending + queue_approved + queue_rejected

    auto_approved = sum(
        1
        for item in proposal_items
        if str(item.get("status", "")).lower() == "approved"
        and str(item.get("reviewed_by", "")).lower() in {"system", "auto", "automation"}
    )
    auto_approved += sum(
        1
        for item in audit_items
        if _matches_any_keyword(str(item.get("action") or ""), ("auto_approve", "auto-approved"))
    )

    enrichment_events = [
        item
        for item in audit_items
        if _matches_any_keyword(
            str(item.get("action") or ""),
            ("enrich", "enrichment", "truth_ingest", "ingest", "completeness"),
        )
    ]
    enrichment_jobs_processed = len(enrichment_events) if enrichment_events else total_products

    acp_exports = 0
    ucp_exports = 0
    for item in audit_items:
        action = str(item.get("action") or "").lower()
        if "export" not in action:
            continue

        target = _extract_export_target(item)
        if "acp" in target:
            acp_exports += 1
        if "ucp" in target:
            ucp_exports += 1

    return TruthAnalyticsSummaryResponse(
        overall_completeness=overall_completeness,
        total_products=total_products,
        enrichment_jobs_processed=enrichment_jobs_processed,
        auto_approved=auto_approved,
        sent_to_hitl=sent_to_hitl,
        queue_pending=queue_pending,
        queue_approved=queue_approved,
        queue_rejected=queue_rejected,
        avg_review_time_minutes=_average_review_time_minutes(proposal_items),
        acp_exports=acp_exports,
        ucp_exports=ucp_exports,
    )


@router.get("/truth/analytics/completeness", response_model=list[TruthAnalyticsCompletenessRow])
async def get_truth_analytics_completeness():
    """Return category-aware completeness data for truth analytics chart."""
    items = await completeness_repo.query(query="SELECT * FROM c")
    by_category: dict[str, list[float]] = defaultdict(list)

    for item in items:
        category = str(item.get("category_id") or item.get("category") or "Uncategorized")
        score = _to_float(item.get("score", item.get("completeness_score")))
        by_category[category].append(score)

    rows = [
        TruthAnalyticsCompletenessRow(
            category=category,
            completeness=(sum(scores) / len(scores)) if scores else 0.0,
            product_count=len(scores),
        )
        for category, scores in by_category.items()
    ]

    return sorted(rows, key=lambda row: row.category.lower())


@router.get("/truth/analytics/throughput", response_model=list[TruthAnalyticsThroughputPoint])
async def get_truth_analytics_throughput(
    window_hours: int = Query(24, ge=1, le=168, description="Rolling window in hours"),
    interval_minutes: int = Query(60, ge=5, le=1440, description="Bucket size in minutes"),
):
    """Return time-window aware throughput series for truth analytics chart."""
    now = datetime.now(UTC)
    completeness_items = await completeness_repo.query(query="SELECT * FROM c")
    proposal_items = await proposed_attr_repo.query(query="SELECT * FROM c")
    audit_items = await audit_repo.query(query="SELECT * FROM c")

    bucket_starts = _build_bucket_starts(
        now=now,
        window_hours=window_hours,
        interval_minutes=interval_minutes,
    )
    buckets: dict[datetime, dict[str, int]] = {
        bucket_start: {"ingested": 0, "enriched": 0, "approved": 0, "rejected": 0}
        for bucket_start in bucket_starts
    }

    for item in completeness_items:
        event_time = _extract_event_time(
            item, ["generated_at", "created_at", "timestamp", "updated_at"]
        )
        if event_time is None:
            continue
        bucket_key = _bucket_for_timestamp(
            event_time,
            bucket_starts=bucket_starts,
            interval_minutes=interval_minutes,
        )
        if bucket_key is not None:
            buckets[bucket_key]["ingested"] += 1

    for item in audit_items:
        action = str(item.get("action") or "")
        if not _matches_any_keyword(action, ("enrich", "enrichment")):
            continue
        event_time = _extract_event_time(item, ["timestamp", "created_at", "updated_at"])
        if event_time is None:
            continue
        bucket_key = _bucket_for_timestamp(
            event_time,
            bucket_starts=bucket_starts,
            interval_minutes=interval_minutes,
        )
        if bucket_key is not None:
            buckets[bucket_key]["enriched"] += 1

    for item in proposal_items:
        status_value = str(item.get("status") or "").lower()
        if status_value not in {"approved", "rejected"}:
            continue

        event_time = _extract_event_time(item, ["reviewed_at", "updated_at", "timestamp"])
        if event_time is None:
            continue

        bucket_key = _bucket_for_timestamp(
            event_time,
            bucket_starts=bucket_starts,
            interval_minutes=interval_minutes,
        )
        if bucket_key is None:
            continue

        buckets[bucket_key][status_value] += 1

    return [
        TruthAnalyticsThroughputPoint(
            timestamp=bucket_start.isoformat(),
            ingested=values["ingested"],
            enriched=values["enriched"],
            approved=values["approved"],
            rejected=values["rejected"],
        )
        for bucket_start, values in sorted(buckets.items(), key=lambda item: item[0])
    ]


@router.get("/completeness/{entity_id}", response_model=CompletenessReportResponse)
async def get_completeness_report(
    entity_id: str,
    limit: int = Query(1, le=10, description="Number of recent reports to return"),
):
    """Get the latest completeness report for a product."""
    items = await completeness_repo.query(
        query="SELECT * FROM c WHERE c.entity_id = @entity_id",
        parameters=[{"name": "@entity_id", "value": entity_id}],
        partition_key=entity_id,
    )
    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No completeness report found for entity '{entity_id}'",
        )
    items = items[-limit:]
    # Return most recent (last inserted)
    return CompletenessReportResponse(**items[-1])
