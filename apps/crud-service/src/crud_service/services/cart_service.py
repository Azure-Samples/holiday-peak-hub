"""Business logic for cart operations."""

from datetime import datetime, timezone
from typing import Any

import httpx
from circuitbreaker import CircuitBreakerError
from crud_service.schemas.domain.cart import AddCartItemCommand
from fastapi import HTTPException, status

AGENT_FALLBACK_EXCEPTIONS = (httpx.HTTPError, CircuitBreakerError)


async def add_item_to_cart(
    command: AddCartItemCommand,
    *,
    product_repo: Any,
    cart_repo: Any,
    agent_client: Any,
    event_publisher: Any,
    logger: Any,
) -> None:
    """Execute add-to-cart flow with optional reservation validation."""
    product = await product_repo.get_by_id(command.product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    try:
        reservation = await agent_client.validate_reservation(
            sku=command.product_id,
            quantity=command.quantity,
        )
        if isinstance(reservation, dict):
            is_approved = reservation.get("approved")
            if is_approved is None:
                is_approved = reservation.get("valid")
            if is_approved is False:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=reservation.get("reason", "Insufficient stock"),
                )
            if is_approved is True:
                try:
                    await event_publisher.publish_inventory_reserved(
                        {
                            "user_id": command.current_user.user_id,
                            "sku": command.product_id,
                            "quantity": command.quantity,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )
                except (RuntimeError, ValueError, TypeError) as exc:
                    logger.warning(
                        "Inventory reservation publish failed for user_id=%s sku=%s",
                        command.current_user.user_id,
                        command.product_id,
                        extra={"error_type": type(exc).__name__},
                        exc_info=True,
                    )
    except AGENT_FALLBACK_EXCEPTIONS as exc:
        logger.warning(
            "Inventory reservation validation unavailable for product_id=%s; continuing with optimistic add",
            command.product_id,
            extra={"error_type": type(exc).__name__},
            exc_info=True,
        )

    cart = await cart_repo.get_by_user(command.current_user.user_id)
    if not cart:
        cart = {
            "id": f"cart_{command.current_user.user_id}",
            "user_id": command.current_user.user_id,
            "items": [],
            "status": "active",
        }

    items = cart.get("items", [])
    existing_item = next((item for item in items if item["product_id"] == command.product_id), None)

    if existing_item:
        existing_item["quantity"] += command.quantity
    else:
        items.append(
            {
                "product_id": command.product_id,
                "quantity": command.quantity,
                "price": product["price"],
            }
        )

    cart["items"] = items
    await cart_repo.update(cart)
