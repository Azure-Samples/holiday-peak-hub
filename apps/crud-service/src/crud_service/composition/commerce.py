"""Commerce-scoped transactional route composition."""

from crud_service.routes import (
    acp_checkout,
    acp_payments,
    acp_products,
    brand_shopping,
    cart,
    categories,
    checkout,
    inventory,
    orders,
    payments,
    products,
)
from crud_service.routes import returns as customer_returns
from crud_service.routes import (
    reviews,
)
from fastapi import FastAPI


def include_commerce_routes(app: FastAPI) -> None:
    """Register commerce APIs without changing external contracts."""
    app.include_router(products.router, prefix="/api", tags=["Products"])
    app.include_router(categories.router, prefix="/api", tags=["Categories"])
    app.include_router(cart.router, prefix="/api", tags=["Cart"])
    app.include_router(orders.router, prefix="/api", tags=["Orders"])
    app.include_router(inventory.router, prefix="/api", tags=["Inventory"])
    app.include_router(checkout.router, prefix="/api", tags=["Checkout"])
    app.include_router(payments.router, prefix="/api", tags=["Payments"])
    app.include_router(customer_returns.router, prefix="/api/returns", tags=["Returns"])
    app.include_router(reviews.router, prefix="/api", tags=["Reviews"])
    app.include_router(brand_shopping.router, prefix="/api", tags=["Brand Shopping"])
    app.include_router(acp_products.router, prefix="/acp", tags=["ACP Products"])
    app.include_router(acp_checkout.router, prefix="/acp", tags=["ACP Checkout"])
    app.include_router(acp_payments.router, prefix="/acp", tags=["ACP Payments"])
