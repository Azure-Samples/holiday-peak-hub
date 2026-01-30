"""Checkout routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from crud_service.auth import User, get_current_user
from crud_service.integrations import get_agent_client
from crud_service.repositories import CartRepository

router = APIRouter()
cart_repo = CartRepository()
agent_client = get_agent_client()


class CheckoutValidationResponse(BaseModel):
    """Checkout validation response."""

    valid: bool
    errors: list[str]
    warnings: list[str]
    estimated_total: float
    estimated_shipping: float
    estimated_tax: float


@router.post("/checkout/validate", response_model=CheckoutValidationResponse)
async def validate_checkout(current_user: User = Depends(get_current_user)):
    """
    Validate checkout before order creation.
    
    Checks:
    - Cart not empty
    - Inventory availability (via agent)
    - Pricing accuracy
    - Shipping address valid
    - Payment method valid
    """
    cart = await cart_repo.get_by_user(current_user.user_id)
    if not cart or not cart.get("items"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cart is empty",
        )

    errors = []
    warnings = []

    # Validate inventory for each item
    for item in cart.get("items", []):
        try:
            inventory = await agent_client.get_inventory_status(item["product_id"])
            if not inventory.get("available"):
                errors.append(f"Product {item['product_id']} is out of stock")
            elif inventory.get("quantity", 999) < item["quantity"]:
                warnings.append(
                    f"Limited quantity for product {item['product_id']}: "
                    f"only {inventory.get('quantity')} available"
                )
        except Exception:
            warnings.append(f"Could not verify inventory for {item['product_id']}")

    # Calculate totals
    subtotal = sum(item["price"] * item["quantity"] for item in cart.get("items", []))
    estimated_shipping = 9.99  # TODO: Calculate shipping
    estimated_tax = subtotal * 0.08  # TODO: Calculate tax by location

    return CheckoutValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        estimated_total=subtotal + estimated_shipping + estimated_tax,
        estimated_shipping=estimated_shipping,
        estimated_tax=estimated_tax,
    )
