"""Staff-scoped operational route composition."""

from crud_service.routes.staff import analytics
from crud_service.routes.staff import returns as staff_returns
from crud_service.routes.staff import shipments, tickets
from fastapi import FastAPI


def include_staff_routes(app: FastAPI) -> None:
    """Register staff and backoffice routes."""
    app.include_router(analytics.router, prefix="/api/staff/analytics", tags=["Staff Analytics"])
    app.include_router(tickets.router, prefix="/api/staff/tickets", tags=["Staff Tickets"])
    app.include_router(staff_returns.router, prefix="/api/staff/returns", tags=["Staff Returns"])
    app.include_router(shipments.router, prefix="/api/staff/shipments", tags=["Staff Shipments"])
