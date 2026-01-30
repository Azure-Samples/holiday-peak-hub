"""Staff shipment management routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from crud_service.auth import User, require_staff
from crud_service.repositories.base import BaseRepository

router = APIRouter()


class ShipmentRepository(BaseRepository):
    """Repository for shipments."""

    def __init__(self):
        super().__init__(container_name="shipments")


shipment_repo = ShipmentRepository()


class ShipmentResponse(BaseModel):
    """Shipment response."""

    id: str
    order_id: str
    status: str
    carrier: str
    tracking_number: str
    created_at: str


@router.get("/", response_model=list[ShipmentResponse])
async def list_shipments(current_user: User = Depends(require_staff)):
    """
    List shipments.
    
    Requires staff role.
    """
    shipments = await shipment_repo.query(
        query="SELECT * FROM c ORDER BY c.created_at DESC OFFSET 0 LIMIT 50",
    )
    return [ShipmentResponse(**shipment) for shipment in shipments]


@router.get("/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(shipment_id: str, current_user: User = Depends(require_staff)):
    """Get shipment details."""
    shipment = await shipment_repo.get_by_id(shipment_id)
    if not shipment:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Shipment not found",
        )
    return ShipmentResponse(**shipment)
