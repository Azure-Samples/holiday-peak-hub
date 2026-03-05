"""Audit trail routes — immutable audit log for product truth-layer changes."""

from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

router = APIRouter()


class AuditRepository(BaseRepository):
    """Repository for audit events."""

    def __init__(self):
        super().__init__(container_name="audit_events")


audit_repo = AuditRepository()


class AuditEventResponse(BaseModel):
    """Response model for a single audit event."""

    id: str
    entity_id: str
    action: str
    actor: str | None = None
    field_name: str | None = None
    old_value: object = None
    new_value: object = None
    confidence: float | None = None
    source_model: str | None = None
    timestamp: str | None = None
    metadata: dict | None = None


@router.get("/audit/{entity_id}", response_model=list[AuditEventResponse])
async def get_audit_trail(
    entity_id: str,
    action: str | None = Query(None, description="Filter by action type"),
    limit: int = Query(50, le=200, description="Maximum number of events to return"),
):
    """Get the audit trail for a specific product."""
    items = await audit_repo.query(
        query="SELECT * FROM c WHERE c.entity_id = @entity_id",
        parameters=[{"name": "@entity_id", "value": entity_id}],
        partition_key=entity_id,
    )
    if action:
        items = [i for i in items if i.get("action") == action]
    return [AuditEventResponse(**item) for item in items[:limit]]


@router.get("/audit", response_model=list[AuditEventResponse])
async def query_audit_events(
    action: str | None = Query(None, description="Filter by action type (e.g. enrichment)"),
    actor: str | None = Query(None, description="Filter by actor (user or system)"),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    limit: int = Query(50, le=200, description="Maximum number of events to return"),
):
    """Query audit events across all products with optional filters."""
    if entity_id:
        raise HTTPException(
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
            detail="Use /audit/{entity_id} for entity-scoped queries",
            headers={"Location": f"/api/audit/{entity_id}"},
        )
    items = await audit_repo.query(query="SELECT * FROM c")
    if action:
        items = [i for i in items if i.get("action") == action]
    if actor:
        items = [i for i in items if i.get("actor") == actor]
    return [AuditEventResponse(**item) for item in items[:limit]]
