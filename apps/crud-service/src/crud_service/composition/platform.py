"""Platform-scoped routes for service operations and authentication."""

from crud_service.routes import auth, connector_webhooks, health, users, webhooks
from fastapi import FastAPI


def include_platform_routes(app: FastAPI) -> None:
    """Register platform and identity route surfaces."""
    app.include_router(health.router, tags=["Health"])
    app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(users.router, prefix="/api", tags=["Users"])
    app.include_router(webhooks.router, tags=["Webhooks"])
    app.include_router(connector_webhooks.router, tags=["Connector Webhooks"])
