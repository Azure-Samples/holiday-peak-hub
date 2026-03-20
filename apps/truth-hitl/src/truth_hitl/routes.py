"""REST routes for the Truth HITL review queue."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from truth_hitl.adapters import HITLAdapters, build_hitl_approval_event
from truth_hitl.review_manager import ReviewDecision, ReviewItem


class BatchReviewItemDecision(BaseModel):
    """Single batch decision entry for an entity."""

    entity_id: str
    attr_ids: list[str] | None = None
    reason: str | None = None
    reviewed_by: str | None = None


class BatchReviewDecisionRequest(BaseModel):
    """Batch request for approve/reject over multiple entities."""

    decisions: list[BatchReviewItemDecision]


def build_review_router(adapters: HITLAdapters) -> APIRouter:
    """Return an APIRouter wired to the provided adapters."""
    router = APIRouter(prefix="/review", tags=["hitl-review"])

    async def publish_approval_event(
        *,
        entity_id: str,
        approved_items: list[ReviewItem],
        reviewed_by: str | None,
    ) -> None:
        if not approved_items:
            return

        approved_fields = [item.field_name for item in approved_items if item.field_name]
        decision_timestamp = datetime.now(timezone.utc)
        payload = build_hitl_approval_event(
            entity_id=entity_id,
            approved_fields=approved_fields,
            reviewer_id=reviewed_by,
            decision_timestamp=decision_timestamp,
        )
        await adapters.export_publisher.publish(payload)

    def execute_review_action(
        entity_id: str, decision: ReviewDecision, action: str
    ) -> list[ReviewItem]:
        """Execute a review action and keep single-action response semantics."""
        action_map = {
            "approve": adapters.review_manager.approve,
            "reject": adapters.review_manager.reject,
            "edit": adapters.review_manager.edit_and_approve,
        }
        items = action_map[action](entity_id, decision)
        if not items:
            raise HTTPException(status_code=404, detail="No pending proposals found")
        return items

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
        approved = execute_review_action(entity_id, decision, "approve")
        await publish_approval_event(
            entity_id=entity_id,
            approved_items=approved,
            reviewed_by=decision.reviewed_by,
        )
        return {
            "entity_id": entity_id,
            "approved": len(approved),
            "items": [i.model_dump() for i in approved],
        }

    @router.post("/{entity_id}/reject")
    async def reject(entity_id: str, decision: ReviewDecision) -> dict:
        """Reject proposed attribute(s) with an optional reason."""
        rejected = execute_review_action(entity_id, decision, "reject")
        return {
            "entity_id": entity_id,
            "rejected": len(rejected),
            "items": [i.model_dump() for i in rejected],
        }

    @router.post("/{entity_id}/edit")
    async def edit_and_approve(entity_id: str, decision: ReviewDecision) -> dict:
        """Edit a proposed value and approve it (source becomes 'human')."""
        edited = execute_review_action(entity_id, decision, "edit")
        await publish_approval_event(
            entity_id=entity_id,
            approved_items=edited,
            reviewed_by=decision.reviewed_by,
        )
        return {
            "entity_id": entity_id,
            "edited": len(edited),
            "items": [i.model_dump() for i in edited],
        }

    @router.post("/approve/batch")
    async def batch_approve(request: BatchReviewDecisionRequest) -> dict:
        """Approve proposals for multiple entities in one request."""
        results: list[dict] = []
        for entry in request.decisions:
            decision = ReviewDecision(
                attr_ids=entry.attr_ids,
                reason=entry.reason,
                reviewed_by=entry.reviewed_by,
            )
            approved = adapters.review_manager.approve(entry.entity_id, decision)
            if not approved:
                continue
            await publish_approval_event(
                entity_id=entry.entity_id,
                approved_items=approved,
                reviewed_by=entry.reviewed_by,
            )
            results.append(
                {
                    "entity_id": entry.entity_id,
                    "approved": len(approved),
                    "items": [i.model_dump() for i in approved],
                }
            )
        return {
            "processed": len(results),
            "requested": len(request.decisions),
            "results": results,
        }

    @router.post("/reject/batch")
    async def batch_reject(request: BatchReviewDecisionRequest) -> dict:
        """Reject proposals for multiple entities in one request."""
        results: list[dict] = []
        for entry in request.decisions:
            decision = ReviewDecision(
                attr_ids=entry.attr_ids,
                reason=entry.reason,
                reviewed_by=entry.reviewed_by,
            )
            rejected = adapters.review_manager.reject(entry.entity_id, decision)
            if not rejected:
                continue
            results.append(
                {
                    "entity_id": entry.entity_id,
                    "rejected": len(rejected),
                    "items": [i.model_dump() for i in rejected],
                }
            )
        return {
            "processed": len(results),
            "requested": len(request.decisions),
            "results": results,
        }

    return router
