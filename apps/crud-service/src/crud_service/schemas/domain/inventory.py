"""Internal domain models for inventory business logic."""

from dataclasses import dataclass

from crud_service.auth import User


@dataclass(frozen=True)
class InventoryActor:
    """Internal actor model used for inventory mutations."""

    user: User
