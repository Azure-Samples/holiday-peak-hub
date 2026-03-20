"""Order routes."""

import logging
import uuid
from datetime import datetime, timezone

import httpx
from circuitbreaker import CircuitBreakerError
from crud_service.auth import User, get_current_user
from crud_service.integrations import get_agent_client, get_event_publisher
from crud_service.repositories import CartRepository, OrderRepository
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()
order_repo = OrderRepository()
cart_repo = CartRepository()
event_publisher = get_event_publisher()
agent_client = get_agent_client()
logger = logging.getLogger(__name__)
AGENT_FALLBACK_EXCEPTIONS = (httpx.HTTPError, CircuitBreakerError)


class OrderItem(BaseModel):
    """Order item."""

    product_id: str
    quantity: int
    price: float


class CreateOrderRequest(BaseModel):
    """Create order request."""

    shipping_address_id: str
    payment_method_id: str


class OrderResponse(BaseModel):
    """Order response."""

    id: str
    user_id: str
    items: list[OrderItem]
    total: float
    status: str
    created_at: str


@router.get("/orders", response_model=list[OrderResponse])
async def list_orders(current_user: User = Depends(get_current_user)):
    """List user's orders."""
    orders = await order_repo.get_by_user(current_user.user_id, limit=50)
    return [OrderResponse(**order) for order in orders]


class OrderTrackingResponse(BaseModel):
    """Order with tracking/status enrichment."""

    id: str
    user_id: str
    items: list[OrderItem]
    total: float
    status: str
    created_at: str
    tracking: dict | None = None
    eta: dict | None = None
    carrier: dict | None = None


class ReturnPlanResponse(BaseModel):
    """Return plan for an order."""

    order_id: str
    plan: dict | None = None


@router.get("/orders/{order_id}", response_model=OrderTrackingResponse)
async def get_order(order_id: str, current_user: User = Depends(get_current_user)):
    """Get order details enriched with tracking status and ETA."""
    order = await order_repo.get_by_id(order_id, partition_key=current_user.user_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Verify order belongs to user
    if order["user_id"] != current_user.user_id and "staff" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Enrich with agent-driven tracking & ETA
    tracking = None
    eta = None
    carrier = None
    try:
        tracking = await agent_client.get_order_status(order_id)
    except AGENT_FALLBACK_EXCEPTIONS as exc:
        logger.warning(
            "Order status enrichment failed for order_id=%s",
            order_id,
            extra={"error_type": type(exc).__name__},
            exc_info=True,
        )
    tracking_id = order.get("tracking_id") or order_id
    try:
        eta = await agent_client.get_delivery_eta(tracking_id)
    except AGENT_FALLBACK_EXCEPTIONS as exc:
        logger.warning(
            "Delivery ETA enrichment failed for tracking_id=%s",
            tracking_id,
            extra={"error_type": type(exc).__name__},
            exc_info=True,
        )
    try:
        carrier = await agent_client.get_carrier_recommendation(tracking_id)
    except AGENT_FALLBACK_EXCEPTIONS as exc:
        logger.warning(
            "Carrier enrichment failed for tracking_id=%s",
            tracking_id,
            extra={"error_type": type(exc).__name__},
            exc_info=True,
        )

    return OrderTrackingResponse(
        **{k: v for k, v in order.items() if k in OrderResponse.model_fields},
        tracking=tracking,
        eta=eta,
        carrier=carrier,
    )


@router.get("/orders/{order_id}/returns", response_model=ReturnPlanResponse)
async def get_return_plan(order_id: str, current_user: User = Depends(get_current_user)):
    """Get a returns plan for an order via the logistics agent."""
    order = await order_repo.get_by_id(order_id, partition_key=current_user.user_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    if order["user_id"] != current_user.user_id and "staff" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    tracking_id = order.get("tracking_id") or order_id
    plan = await agent_client.get_return_plan(tracking_id)
    return ReturnPlanResponse(order_id=order_id, plan=plan)


@router.post("/orders", response_model=OrderResponse)
async def create_order(
    request: CreateOrderRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Create order from cart.

    Publishes OrderCreated event to event-hub for agent processing.
    """
    # Get cart
    cart = await cart_repo.get_by_user(current_user.user_id)
    if not cart or not cart.get("items"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty")

    # Create order
    order_id = str(uuid.uuid4())
    items = cart["items"]
    total = sum(item["price"] * item["quantity"] for item in items)

    order = {
        "id": order_id,
        "user_id": current_user.user_id,
        "items": items,
        "total": total,
        "status": "pending",
        "shipping_address_id": request.shipping_address_id,
        "payment_method_id": request.payment_method_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    # Save order
    await order_repo.create(order)

    # Clear cart
    await cart_repo.clear_cart(current_user.user_id)

    # Publish OrderCreated event (agents will process inventory, payment, shipment)
    await event_publisher.publish_order_created(order)

    return OrderResponse(**order)


@router.patch("/orders/{order_id}/cancel")
async def cancel_order(order_id: str, current_user: User = Depends(get_current_user)):
    """Cancel order."""
    order = await order_repo.get_by_id(order_id, partition_key=current_user.user_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    if order["user_id"] != current_user.user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    if order["status"] not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order cannot be cancelled",
        )

    order["status"] = "cancelled"
    await order_repo.update(order)

    # Publish OrderCancelled event
    await event_publisher.publish("order-events", "OrderCancelled", order)

    return {"message": "Order cancelled"}
