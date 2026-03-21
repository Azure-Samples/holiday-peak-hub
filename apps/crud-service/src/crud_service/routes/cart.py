"""Cart routes."""

import logging

from crud_service.auth import User, get_current_user
from crud_service.integrations import get_agent_client, get_event_publisher
from crud_service.repositories import CartRepository, ProductRepository
from crud_service.schemas.api.cart import (
    AddToCartRequest,
    CartItem,
    CartRecommendationsResponse,
    CartResponse,
)
from crud_service.schemas.domain.cart import AddCartItemCommand
from crud_service.services.cart_service import add_item_to_cart as add_item_to_cart_service
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter()
cart_repo = CartRepository()
product_repo = ProductRepository()
agent_client = get_agent_client()
logger = logging.getLogger(__name__)
event_publisher = get_event_publisher()


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
    await add_item_to_cart_service(
        AddCartItemCommand(
            product_id=request.product_id,
            quantity=request.quantity,
            current_user=current_user,
        ),
        product_repo=product_repo,
        cart_repo=cart_repo,
        agent_client=agent_client,
        event_publisher=event_publisher,
        logger=logger,
    )

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
