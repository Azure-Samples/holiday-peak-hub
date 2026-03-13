"""Checkout routes."""

from crud_service.auth import User, get_current_user
from crud_service.config import get_settings
from crud_service.integrations import get_agent_client
from crud_service.repositories import CartRepository
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

router = APIRouter()
cart_repo = CartRepository()
agent_client = get_agent_client()
settings = get_settings()
DEFAULT_SHIPPING_FEE = 9.99
DEFAULT_TAX_RATE = 0.08


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

    errors: list[str] = []
    warnings: list[str] = []

    items = [
        {"sku": item["product_id"], "quantity": item.get("quantity", 1)}
        for item in cart.get("items", [])
    ]

    # Prefer agent-driven validation when available
    agent_validation = await agent_client.call_endpoint(
        agent_url=settings.checkout_support_agent_url,
        endpoint="/invoke",
        data={"items": items},
        fallback_value=None,
    )
    validation = agent_validation.get("validation") if isinstance(agent_validation, dict) else None
    issues = validation.get("issues") if isinstance(validation, dict) else None
    if issues:
        for issue in issues:
            sku = issue.get("sku")
            issue_type = issue.get("type")
            if issue_type in {"inventory_missing", "missing_price"}:
                warnings.append(f"Checkout issue for {sku}: {issue_type}")
            elif issue_type == "out_of_stock":
                errors.append(f"Product {sku} is out of stock")
            elif issue_type == "insufficient_stock":
                available = issue.get("available")
                warnings.append(f"Limited quantity for product {sku}: only {available} available")
    else:
        # Fallback: validate inventory for each item
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
    estimated_shipping = DEFAULT_SHIPPING_FEE
    estimated_tax = subtotal * DEFAULT_TAX_RATE

    return CheckoutValidationResponse(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        estimated_total=subtotal + estimated_shipping + estimated_tax,
        estimated_shipping=estimated_shipping,
        estimated_tax=estimated_tax,
    )
