"""Staff analytics routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from crud_service.auth import User, require_staff

router = APIRouter()


class SalesAnalyticsResponse(BaseModel):
    """Sales analytics response."""

    total_revenue: float
    total_orders: int
    average_order_value: float
    top_products: list[dict]


@router.get("/summary", response_model=SalesAnalyticsResponse)
async def get_sales_analytics(current_user: User = Depends(require_staff)):
    """
    Get sales analytics summary.
    
    Requires staff role.
    """
    # TODO: Implement analytics aggregation
    # This should query orders and aggregate metrics
    return SalesAnalyticsResponse(
        total_revenue=0.0,
        total_orders=0,
        average_order_value=0.0,
        top_products=[],
    )
