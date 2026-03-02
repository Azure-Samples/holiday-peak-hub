"""Routes package."""

from crud_service.routes import (
    acp_products,
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
    "acp_products",
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
