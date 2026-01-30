"""Cart routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from crud_service.auth import User, get_current_user
from crud_service.repositories import CartRepository, ProductRepository

router = APIRouter()
cart_repo = CartRepository()
product_repo = ProductRepository()


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


@router.get("/cart", response_model=CartResponse)
async def get_cart(current_user: User = Depends(get_current_user)):
    """Get current user's cart."""
    cart = await cart_repo.get_by_user(current_user.user_id)
    if not cart:
        return CartResponse(user_id=current_user.user_id, items=[], total=0.0)

    items = [CartItem(**item) for item in cart.get("items", [])]
    total = sum(item.price * item.quantity for item in items)

    return CartResponse(user_id=current_user.user_id, items=items, total=total)


@router.post("/cart/items")
async def add_to_cart(
    request: AddToCartRequest,
    current_user: User = Depends(get_current_user),
):
    """Add item to cart."""
    # Verify product exists
    product = await product_repo.get_by_id(request.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

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
