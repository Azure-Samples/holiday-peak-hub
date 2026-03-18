"""Cart routes."""

import logging
from datetime import datetime, timezone

from crud_service.auth import User, get_current_user
from crud_service.integrations import get_agent_client, get_event_publisher
from crud_service.repositories import CartRepository, ProductRepository
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()
cart_repo = CartRepository()
product_repo = ProductRepository()
agent_client = get_agent_client()
logger = logging.getLogger(__name__)
event_publisher = get_event_publisher()


class AddToCartRequest(BaseModel):
    """Add to cart request."""

    product_id: str
    quantity: int = 1


class CartItem(BaseModel):
    """Cart item."""

    product_id: str
    quantity: int
    price: float


class CartResponse(BaseModel):
    """Cart response."""

    user_id: str
    items: list[CartItem]
    total: float


class CartRecommendationsResponse(BaseModel):
    """Cart recommendations response."""

    user_id: str
    recommendations: dict | None


@router.get("/cart", response_model=CartResponse)
async def get_cart(current_user: User = Depends(get_current_user)):
    """Get current user's cart."""
    cart = await cart_repo.get_by_user(current_user.user_id)
    if not cart:
        return CartResponse(user_id=current_user.user_id, items=[], total=0.0)

    items = [CartItem(**item) for item in cart.get("items", [])]
    total = sum(item.price * item.quantity for item in items)

    return CartResponse(user_id=current_user.user_id, items=items, total=total)


@router.get("/cart/recommendations", response_model=CartRecommendationsResponse)
async def get_cart_recommendations(current_user: User = Depends(get_current_user)):
    """Get cart recommendations from the cart intelligence agent."""
    cart = await cart_repo.get_by_user(current_user.user_id)
    items = [
        {"sku": item["product_id"], "quantity": item.get("quantity", 1)}
        for item in (cart or {}).get("items", [])
    ]
    recommendations = await agent_client.get_user_recommendations(
        user_id=current_user.user_id,
        items=items,
    )
    return CartRecommendationsResponse(
        user_id=current_user.user_id,
        recommendations=recommendations,
    )


@router.post("/cart/items")
async def add_to_cart(
    request: AddToCartRequest,
    current_user: User = Depends(get_current_user),
):
    """Add item to cart (validates stock reservation when agent available)."""
    # Verify product exists
    product = await product_repo.get_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Validate reservation via inventory agent (non-blocking)
    try:
        reservation = await agent_client.validate_reservation(
            sku=request.product_id, quantity=request.quantity
        )
        if isinstance(reservation, dict) and reservation.get("valid") is False:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=reservation.get("reason", "Insufficient stock"),
            )
        if isinstance(reservation, dict) and reservation.get("valid") is True:
            try:
                await event_publisher.publish_inventory_reserved(
                    {
                        "user_id": current_user.user_id,
                        "sku": request.product_id,
                        "quantity": request.quantity,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception:
                pass
    except HTTPException:
        raise
    except Exception:
        logger.warning(
            "Inventory reservation validation unavailable for product_id=%s; continuing with optimistic add",
            request.product_id,
            exc_info=True,
        )

    # Get or create cart
    cart = await cart_repo.get_by_user(current_user.user_id)
    if not cart:
        cart = {
            "id": f"cart_{current_user.user_id}",
            "user_id": current_user.user_id,
            "items": [],
            "status": "active",
        }

    # Add or update item
    items = cart.get("items", [])
    existing_item = next((i for i in items if i["product_id"] == request.product_id), None)

    if existing_item:
        existing_item["quantity"] += request.quantity
    else:
        items.append(
            {
                "product_id": request.product_id,
                "quantity": request.quantity,
                "price": product["price"],
            }
        )

    cart["items"] = items
    await cart_repo.update(cart)

    return {"message": "Item added to cart"}


@router.delete("/cart/items/{product_id}")
async def remove_from_cart(
    product_id: str,
    current_user: User = Depends(get_current_user),
):
    """Remove item from cart."""
    cart = await cart_repo.get_by_user(current_user.user_id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

    items = cart.get("items", [])
    cart["items"] = [i for i in items if i["product_id"] != product_id]
    await cart_repo.update(cart)

    return {"message": "Item removed from cart"}


@router.delete("/cart")
async def clear_cart(current_user: User = Depends(get_current_user)):
    """Clear entire cart."""
    await cart_repo.clear_cart(current_user.user_id)
    return {"message": "Cart cleared"}
