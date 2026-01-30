"""Order routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from crud_service.auth import User, get_current_user
from crud_service.integrations import get_event_publisher
from crud_service.repositories import CartRepository, OrderRepository

router = APIRouter()
order_repo = OrderRepository()
cart_repo = CartRepository()
event_publisher = get_event_publisher()


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


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(order_id: str, current_user: User = Depends(get_current_user)):
    """Get order details."""
    order = await order_repo.get_by_id(order_id, partition_key=current_user.user_id)
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")

    # Verify order belongs to user
    if order["user_id"] != current_user.user_id and "staff" not in current_user.roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    return OrderResponse(**order)


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
        "created_at": datetime.utcnow().isoformat(),
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
