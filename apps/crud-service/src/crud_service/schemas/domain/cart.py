"""Internal domain models for cart business logic."""

from dataclasses import dataclass

from crud_service.auth import User


@dataclass(frozen=True)
class AddCartItemCommand:
    """Internal add-to-cart command."""

    product_id: str
    quantity: int
    current_user: User
