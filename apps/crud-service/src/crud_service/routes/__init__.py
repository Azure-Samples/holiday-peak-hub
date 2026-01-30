"""Routes package."""

from crud_service.routes import (
    auth,
    cart,
    categories,
    checkout,
    health,
    orders,
    payments,
    products,
    reviews,
    users,
)

__all__ = [
    "health",
    "auth",
    "users",
    "products",
    "categories",
    "cart",
    "orders",
    "checkout",
    "payments",
    "reviews",
]
