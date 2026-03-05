"""Completeness routes — product completeness scoring reports."""

from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter()


class CompletenessRepository(BaseRepository):
    """Repository for completeness reports."""

    def __init__(self):
        super().__init__(container_name="completeness_reports")


completeness_repo = CompletenessRepository()


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
    gaps: list[GapDetail] = []
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
    fully_complete = sum(1 for s in scores if s >= 1.0)
    needs_enrichment = sum(1 for s in scores if 0.70 <= s < 1.0)
    critical_gaps = sum(1 for s in scores if s < 0.70)
    return CompletenessSummaryResponse(
        total_products=total,
        average_score=avg_score,
        fully_complete=fully_complete,
        needs_enrichment=needs_enrichment,
        critical_gaps=critical_gaps,
    )


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
    # Return most recent (last inserted)
    return CompletenessReportResponse(**items[-1])
