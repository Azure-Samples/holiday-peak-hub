"""Staff returns management routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from crud_service.auth import User, require_staff
from crud_service.repositories.base import BaseRepository

router = APIRouter()


class ReturnRepository(BaseRepository):
    """Repository for returns."""

    def __init__(self):
        super().__init__(container_name="returns")


return_repo = ReturnRepository()


class ReturnResponse(BaseModel):
    """Return response."""

    id: str
    order_id: str
    user_id: str
    status: str
    reason: str
    created_at: str


@router.get("/", response_model=list[ReturnResponse])
async def list_returns(current_user: User = Depends(require_staff)):
    """
    List return requests.
    
    Requires staff role.
    """
    returns = await return_repo.query(
        query="SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT 50",
    )
    return [ReturnResponse(**ret) for ret in returns]


@router.patch("/{return_id}/approve")
async def approve_return(return_id: str, current_user: User = Depends(require_staff)):
    """Approve a return request."""
    ret = await return_repo.get_by_id(return_id)
    if not ret:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found",
        )

    ret["status"] = "approved"
    await return_repo.update(ret)

    return {"message": "Return approved"}
