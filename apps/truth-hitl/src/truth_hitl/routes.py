"""REST routes for the Truth HITL review queue."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from truth_hitl.adapters import HITLAdapters
from truth_hitl.review_manager import ReviewDecision, ReviewItem

router = APIRouter(prefix="/review", tags=["hitl-review"])


def build_review_router(adapters: HITLAdapters) -> APIRouter:
    """Return an APIRouter wired to the provided adapters."""

    @router.get("/queue")
    async def list_queue(
        entity_id: str | None = None,
        field_name: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> dict:
        """List pending review items (paginated, filterable)."""
        items = adapters.review_manager.list_pending(
            entity_id=entity_id,
            field_name=field_name,
            skip=skip,
            limit=limit,
        )
        return {"items": [i.model_dump() for i in items], "count": len(items)}

    @router.get("/stats")
    async def queue_stats() -> dict:
        """Return review queue statistics."""
        return adapters.review_manager.stats()

    @router.get("/{entity_id}")
    async def get_entity_proposals(entity_id: str) -> dict:
        """Get all pending proposals for a product."""
        items = adapters.review_manager.get_by_entity(entity_id)
        return {"entity_id": entity_id, "items": [i.model_dump() for i in items]}

    @router.post("/{entity_id}/approve")
    async def approve(entity_id: str, decision: ReviewDecision) -> dict:
        """Approve proposed attribute(s) for an entity."""
        approved = adapters.review_manager.approve(entity_id, decision)
        if not approved:
            raise HTTPException(status_code=404, detail="No pending proposals found")
        return {
            "entity_id": entity_id,
            "approved": len(approved),
            "items": [i.model_dump() for i in approved],
        }

    @router.post("/{entity_id}/reject")
    async def reject(entity_id: str, decision: ReviewDecision) -> dict:
        """Reject proposed attribute(s) with an optional reason."""
        rejected = adapters.review_manager.reject(entity_id, decision)
        if not rejected:
            raise HTTPException(status_code=404, detail="No pending proposals found")
        return {
            "entity_id": entity_id,
            "rejected": len(rejected),
            "items": [i.model_dump() for i in rejected],
        }

    @router.post("/{entity_id}/edit")
    async def edit_and_approve(entity_id: str, decision: ReviewDecision) -> dict:
        """Edit a proposed value and approve it (source becomes 'human')."""
        edited = adapters.review_manager.edit_and_approve(entity_id, decision)
        if not edited:
            raise HTTPException(status_code=404, detail="No pending proposals found")
        return {
            "entity_id": entity_id,
            "edited": len(edited),
            "items": [i.model_dump() for i in edited],
        }

    return router
