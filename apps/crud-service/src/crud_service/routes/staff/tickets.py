"""Staff ticket management routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from crud_service.auth import User, require_staff
from crud_service.repositories.base import BaseRepository

router = APIRouter()


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
    status: str
    priority: str
    created_at: str


@router.get("/", response_model=list[TicketResponse])
async def list_tickets(current_user: User = Depends(require_staff)):
    """
    List support tickets.
    
    Requires staff role.
    """
    tickets = await ticket_repo.query(
        query="SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT 50",
    )
    return [TicketResponse(**ticket) for ticket in tickets]


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(ticket_id: str, current_user: User = Depends(require_staff)):
    """Get ticket details."""
    ticket = await ticket_repo.get_by_id(ticket_id)
    if not ticket:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticket not found",
        )
    return TicketResponse(**ticket)
