"""Staff ticket management routes."""

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from crud_service.auth import User, get_current_user
from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter()

TicketStatus = Literal[
    "open",
    "in_progress",
    "pending_customer",
    "escalated",
    "resolved",
    "closed",
]
TicketPriority = Literal["low", "medium", "high", "urgent"]

ALLOWED_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "open": {"in_progress", "pending_customer", "escalated", "resolved"},
    "in_progress": {"pending_customer", "escalated", "resolved"},
    "pending_customer": {"in_progress", "escalated", "resolved"},
    "escalated": {"in_progress", "pending_customer", "resolved"},
    "resolved": {"closed"},
    "closed": set(),
}


class TicketRepository(BaseRepository):
    """Repository for support tickets."""

    def __init__(self):
        super().__init__(container_name="tickets")


ticket_repo = TicketRepository()


class TicketResponse(BaseModel):
    """Support ticket response."""

    id: str
    user_id: str
    subject: str
    status: TicketStatus
    priority: TicketPriority
    created_at: str
    description: str | None = None
    assignee_id: str | None = None
    updated_at: str | None = None
    updated_by: str | None = None
    resolved_at: str | None = None
    resolved_by: str | None = None
    escalation_reason: str | None = None
    escalated_at: str | None = None
    escalated_by: str | None = None
    resolution_note: str | None = None
    status_history: list[dict[str, Any]] = Field(default_factory=list)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)


class CreateTicketRequest(BaseModel):
    """Ticket creation request."""

    user_id: str
    subject: str
    priority: TicketPriority = "medium"
    description: str | None = None

    @field_validator("user_id", "subject")
    @classmethod
    def _required_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value


class UpdateTicketRequest(BaseModel):
    """Partial ticket update request."""

    subject: str | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    assignee_id: str | None = None
    reason: str | None = None
    note: str | None = None


class ResolveTicketRequest(BaseModel):
    """Ticket resolve request."""

    reason: str | None = "Resolved by staff"
    resolution_note: str | None = None


class EscalateTicketRequest(BaseModel):
    """Ticket escalate request."""

    reason: str

    @field_validator("reason")
    @classmethod
    def _reason_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be empty")
        return value


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def require_staff_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require either staff or admin role for staff ticket endpoints."""
    if not {"staff", "admin"}.intersection(set(current_user.roles or [])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role 'staff' or 'admin' required",
        )
    return current_user


def _append_audit(
    ticket: dict[str, Any],
    *,
    action: str,
    actor: User,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    entry: dict[str, Any] = {
        "action": action,
        "at": _utc_now_iso(),
        "actor_id": actor.user_id,
        "actor_roles": list(actor.roles or []),
    }
    if reason:
        entry["reason"] = reason
    if details:
        entry["details"] = details
    ticket.setdefault("audit_log", []).append(entry)


def _transition_status(
    ticket: dict[str, Any],
    *,
    new_status: str,
    actor: User,
    reason: str | None,
    action: str,
) -> bool:
    current_status = ticket.get("status", "open")
    if new_status == current_status:
        return False

    allowed_next = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    if new_status not in allowed_next:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Invalid status transition: {current_status} -> {new_status}",
        )

    now = _utc_now_iso()
    ticket["status"] = new_status
    ticket["updated_at"] = now
    ticket["updated_by"] = actor.user_id
    ticket.setdefault("status_history", []).append(
        {
            "from": current_status,
            "to": new_status,
            "at": now,
            "actor_id": actor.user_id,
            "reason": reason,
        }
    )

    if new_status == "resolved":
        ticket["resolved_at"] = now
        ticket["resolved_by"] = actor.user_id

    if new_status == "escalated":
        ticket["escalated_at"] = now
        ticket["escalated_by"] = actor.user_id

    _append_audit(
        ticket,
        action=action,
        actor=actor,
        reason=reason,
        details={"from": current_status, "to": new_status},
    )
    return True


@router.get("/", response_model=list[TicketResponse])
async def list_tickets(_current_user: User = Depends(require_staff_or_admin)):
    """
    List support tickets.

    Requires staff role.
    """
    tickets = await ticket_repo.query(
        query="SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT 50",
    )
    return [TicketResponse(**ticket) for ticket in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, _current_user: User = Depends(require_staff_or_admin)):
    """Get ticket details."""
    ticket = await ticket_repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return TicketResponse(**ticket)


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    request: CreateTicketRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Create a staff ticket with initial audit metadata."""
    now = _utc_now_iso()
    ticket = {
        "id": str(uuid.uuid4()),
        "user_id": request.user_id,
        "subject": request.subject,
        "priority": request.priority,
        "description": request.description,
        "status": "open",
        "created_at": now,
        "updated_at": now,
        "updated_by": current_user.user_id,
        "status_history": [
            {
                "from": None,
                "to": "open",
                "at": now,
                "actor_id": current_user.user_id,
                "reason": "Ticket created",
            }
        ],
        "audit_log": [],
    }
    _append_audit(ticket, action="created", actor=current_user, reason="Ticket created")

    await ticket_repo.create(ticket)
    return TicketResponse(**ticket)


@router.patch("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: str,
    request: UpdateTicketRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Update mutable ticket fields and optionally transition status."""
    ticket = await ticket_repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    changed_fields: list[str] = []

    if request.subject is not None:
        ticket["subject"] = request.subject
        changed_fields.append("subject")
    if request.priority is not None:
        ticket["priority"] = request.priority
        changed_fields.append("priority")
    if request.assignee_id is not None:
        ticket["assignee_id"] = request.assignee_id
        changed_fields.append("assignee_id")

    status_changed = False
    if request.status is not None:
        status_changed = _transition_status(
            ticket,
            new_status=request.status,
            actor=current_user,
            reason=request.reason,
            action="status_updated",
        )
        if status_changed:
            changed_fields.append("status")

    if not changed_fields and not request.note:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No mutable fields provided",
        )

    if changed_fields or request.note:
        ticket["updated_at"] = _utc_now_iso()
        ticket["updated_by"] = current_user.user_id
        _append_audit(
            ticket,
            action="updated",
            actor=current_user,
            reason=request.reason,
            details={
                "changed_fields": changed_fields,
                "note": request.note,
                "status_changed": status_changed,
            },
        )

    await ticket_repo.update(ticket)
    return TicketResponse(**ticket)


@router.post("/{ticket_id}/resolve", response_model=TicketResponse)
async def resolve_ticket(
    ticket_id: str,
    request: ResolveTicketRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Resolve an existing ticket."""
    ticket = await ticket_repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    _transition_status(
        ticket,
        new_status="resolved",
        actor=current_user,
        reason=(request.reason or "Resolved by staff").strip(),
        action="resolved",
    )
    if request.resolution_note is not None:
        ticket["resolution_note"] = request.resolution_note

    ticket["updated_at"] = _utc_now_iso()
    ticket["updated_by"] = current_user.user_id
    await ticket_repo.update(ticket)
    return TicketResponse(**ticket)


@router.post("/{ticket_id}/escalate", response_model=TicketResponse)
async def escalate_ticket(
    ticket_id: str,
    request: EscalateTicketRequest,
    current_user: User = Depends(require_staff_or_admin),
):
    """Escalate an existing ticket."""
    ticket = await ticket_repo.get_by_id(ticket_id)
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )

    _transition_status(
        ticket,
        new_status="escalated",
        actor=current_user,
        reason=request.reason,
        action="escalated",
    )
    ticket["escalation_reason"] = request.reason
    if ticket.get("priority") not in {"high", "urgent"}:
        ticket["priority"] = "high"

    ticket["updated_at"] = _utc_now_iso()
    ticket["updated_by"] = current_user.user_id
    await ticket_repo.update(ticket)
    return TicketResponse(**ticket)
