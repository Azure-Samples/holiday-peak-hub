"""Internal domain models for product business logic."""

from dataclasses import dataclass

from crud_service.auth import User


@dataclass(frozen=True)
class ProductQuery:
    """Internal query input for product listing service."""

    search: str | None
    category: str | None
    limit: int
    current_user: User | None
