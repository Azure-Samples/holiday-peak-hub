"""Review queue models and manager for the Truth HITL service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel

ReasoningPayload = str | list[str] | dict[str, Any] | list[dict[str, Any]]
SourceAssetPayload = str | dict[str, Any]


class ReviewItem(BaseModel):
    """A proposed attribute pending human review."""

    entity_id: str
    attr_id: str
    field_name: str
    proposed_value: Any
    confidence: float
    current_value: Any | None = None
    source: str  # 'ai', 'pim', 'manual'
    proposed_at: datetime
    product_title: str
    category_label: str
    status: str = "pending_review"  # pending_review | approved | rejected
    rejected_reason: str | None = None
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    original_data: dict[str, Any] | None = None
    enriched_data: dict[str, Any] | None = None
    reasoning: ReasoningPayload | None = None
    source_assets: list[SourceAssetPayload] | None = None
    source_type: str | None = None


class ReviewDecision(BaseModel):
    """Decision payload for approve/reject/edit actions."""

    attr_ids: list[str] | None = None  # None means all pending for the entity
    reason: str | None = None  # required for reject
    edited_value: Any | None = None  # used for edit
    reviewed_by: str | None = None


class AuditEvent(BaseModel):
    """Immutable record of a review action."""

    event_id: str
    entity_id: str
    attr_id: str
    action: str  # approved | rejected | edited
    old_value: Any | None
    new_value: Any | None
    reason: str | None
    reviewed_by: str | None
    timestamp: datetime
    original_data: dict[str, Any] | None = None
    enriched_data: dict[str, Any] | None = None
    reasoning: ReasoningPayload | None = None
    source_assets: list[SourceAssetPayload] | None = None
    source_type: str | None = None


class ReviewManager:
    """Manages the in-memory review queue with approve/reject/edit operations."""

    def __init__(self) -> None:
        self._queue: dict[str, ReviewItem] = {}
        self._audit_log: list[AuditEvent] = []

    # ------------------------------------------------------------------
    # Queue population
    # ------------------------------------------------------------------

    def enqueue(self, item: ReviewItem) -> None:
        """Add or update a review item in the queue."""
        self._queue[item.attr_id] = item

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def list_pending(
        self,
        *,
        entity_id: str | None = None,
        field_name: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> list[ReviewItem]:
        """Return pending review items, optionally filtered."""
        items = [
            i
            for i in self._queue.values()
            if i.status == "pending_review"
            and (entity_id is None or i.entity_id == entity_id)
            and (field_name is None or i.field_name == field_name)
        ]
        return items[skip : skip + limit]

    def get_by_entity(self, entity_id: str) -> list[ReviewItem]:
        """Return all pending proposals for a product."""
        return [
            i
            for i in self._queue.values()
            if i.entity_id == entity_id and i.status == "pending_review"
        ]

    def stats(self) -> dict[str, int]:
        """Return counts by status."""
        counts: dict[str, int] = {"pending_review": 0, "approved": 0, "rejected": 0}
        for item in self._queue.values():
            counts[item.status] = counts.get(item.status, 0) + 1
        return counts

    # ------------------------------------------------------------------
    # Review actions
    # ------------------------------------------------------------------

    def approve(self, entity_id: str, decision: ReviewDecision) -> list[ReviewItem]:
        """Approve proposed attributes and move them to truth."""
        targets = self._resolve_targets(entity_id, decision.attr_ids)
        now = datetime.now(timezone.utc)
        approved: list[ReviewItem] = []
        for item in targets:
            old_value = item.proposed_value
            item.status = "approved"
            item.reviewed_at = now
            item.reviewed_by = decision.reviewed_by
            self._queue[item.attr_id] = item
            self._record_audit(
                entity_id=entity_id,
                attr_id=item.attr_id,
                action="approved",
                old_value=old_value,
                new_value=item.proposed_value,
                reason=None,
                reviewed_by=decision.reviewed_by,
                item=item,
            )
            approved.append(item)
        return approved

    def reject(self, entity_id: str, decision: ReviewDecision) -> list[ReviewItem]:
        """Reject proposed attributes with an optional reason."""
        targets = self._resolve_targets(entity_id, decision.attr_ids)
        now = datetime.now(timezone.utc)
        rejected: list[ReviewItem] = []
        for item in targets:
            old_value = item.proposed_value
            item.status = "rejected"
            item.rejected_reason = decision.reason
            item.reviewed_at = now
            item.reviewed_by = decision.reviewed_by
            self._queue[item.attr_id] = item
            self._record_audit(
                entity_id=entity_id,
                attr_id=item.attr_id,
                action="rejected",
                old_value=old_value,
                new_value=None,
                reason=decision.reason,
                reviewed_by=decision.reviewed_by,
                item=item,
            )
            rejected.append(item)
        return rejected

    def edit_and_approve(self, entity_id: str, decision: ReviewDecision) -> list[ReviewItem]:
        """Edit a proposed value then approve it (source becomes 'human')."""
        targets = self._resolve_targets(entity_id, decision.attr_ids)
        now = datetime.now(timezone.utc)
        edited: list[ReviewItem] = []
        for item in targets:
            old_value = item.proposed_value
            item.proposed_value = decision.edited_value
            item.source = "human"
            item.status = "approved"
            item.reviewed_at = now
            item.reviewed_by = decision.reviewed_by
            self._queue[item.attr_id] = item
            self._record_audit(
                entity_id=entity_id,
                attr_id=item.attr_id,
                action="edited",
                old_value=old_value,
                new_value=decision.edited_value,
                reason=decision.reason,
                reviewed_by=decision.reviewed_by,
                item=item,
            )
            edited.append(item)
        return edited

    def audit_log(self, entity_id: str | None = None) -> list[AuditEvent]:
        """Return the audit log, optionally filtered by entity."""
        if entity_id is None:
            return list(self._audit_log)
        return [e for e in self._audit_log if e.entity_id == entity_id]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_targets(self, entity_id: str, attr_ids: list[str] | None) -> list[ReviewItem]:
        pending = self.get_by_entity(entity_id)
        if attr_ids is None:
            return pending
        id_set = set(attr_ids)
        return [i for i in pending if i.attr_id in id_set]

    def _record_audit(
        self,
        *,
        entity_id: str,
        attr_id: str,
        action: str,
        old_value: Any,
        new_value: Any,
        reason: str | None,
        reviewed_by: str | None,
        item: ReviewItem,
    ) -> None:
        import uuid

        self._audit_log.append(
            AuditEvent(
                event_id=str(uuid.uuid4()),
                entity_id=entity_id,
                attr_id=attr_id,
                action=action,
                old_value=old_value,
                new_value=new_value,
                reason=reason,
                reviewed_by=reviewed_by,
                timestamp=datetime.now(timezone.utc),
                original_data=item.original_data,
                enriched_data=item.enriched_data,
                reasoning=item.reasoning,
                source_assets=item.source_assets,
                source_type=item.source_type,
            )
        )
