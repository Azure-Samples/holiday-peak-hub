"""FastAPI application for CRUD operations.

This is NOT an agent service - it's a pure REST API microservice
for transactional data operations and user-facing endpoints.
"""

import logging
import os
from contextlib import asynccontextmanager

from azure.monitor.opentelemetry import configure_azure_monitor
from crud_service.auth.dependencies import get_key_vault_secret
from crud_service.config.settings import get_settings
from crud_service.consumers import get_connector_sync_consumer
from crud_service.integrations.event_publisher import get_event_publisher
from crud_service.repositories.base import BaseRepository
from crud_service.routes import (
    acp_checkout,
    acp_payments,
    acp_products,
    audit_trail,
    auth,
    cart,
    categories,
    checkout,
    completeness,
    connector_webhooks,
    health,
    orders,
    payments,
    products,
    proposed_attributes,
    reviews,
    schemas_registry,
    truth_attributes,
    ucp_products,
    users,
    webhooks,
)
from crud_service.routes.staff import analytics, returns, shipments, tickets
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from opentelemetry import trace

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Application lifespan manager - startup and shutdown logic."""
    # Startup
    logger.info("Starting CRUD Service...")
    logger.info("Environment: %s", settings.environment)
    logger.info("Service Name: %s", settings.service_name)

    # Configure Application Insights if instrumentation key is provided
    if settings.app_insights_connection_string:
        configure_azure_monitor(
            connection_string=settings.app_insights_connection_string,
            logger_name="crud_service",
        )
        logger.info("Application Insights configured")

    # Initialize event publisher
    event_publisher = get_event_publisher()
    await event_publisher.start()
    logger.info("Event publisher started")

    connector_sync_consumer = get_connector_sync_consumer()
    await connector_sync_consumer.start()
    _app.state.connector_sync_consumer = connector_sync_consumer
    logger.info("Connector sync consumer initialized")

    connector_registry = ConnectorRegistry()
    discovered = await connector_registry.discover()
    logger.info("Connector classes discovered: %s", discovered)

    configured_domains = [
        item.strip().lower()
        for item in (os.getenv("CONNECTOR_ENABLED_DOMAINS", "").split(","))
        if item.strip()
    ]
    for domain in configured_domains:
        try:
            await connector_registry.create(domain)
            logger.info("Connector created for domain '%s'", domain)
        except ValueError as exc:
            logger.warning("Connector bootstrap skipped for domain '%s': %s", domain, exc)

    health_interval = float(os.getenv("CONNECTOR_HEALTH_INTERVAL_SECONDS", "60"))
    await connector_registry.start_health_monitor(interval_seconds=health_interval)
    _app.state.connector_registry = connector_registry
    logger.info("Connector health monitor started")

    # Resolve DB credentials from Key Vault only for password mode
    if settings.postgres_auth_mode == "password" and not settings.postgres_password:
        settings.postgres_password = await get_key_vault_secret(
            settings.postgres_password_secret_name
        )
    if settings.postgres_auth_mode == "entra":
        logger.info("PostgreSQL auth mode: Entra token")

    # Initialize PostgreSQL connection pool
    _app.state.db_pool_init_error = None
    try:
        await BaseRepository.initialize_pool()
        logger.info("PostgreSQL pool initialized")
    except Exception as exc:
        _app.state.db_pool_init_error = f"{type(exc).__name__}: {exc}"
        logger.warning("PostgreSQL pool initialization failed: %s", exc)

    logger.info("CRUD Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down CRUD Service...")
    connector_registry: ConnectorRegistry | None = getattr(_app.state, "connector_registry", None)
    if connector_registry:
        await connector_registry.stop_health_monitor()
        logger.info("Connector health monitor stopped")
    await event_publisher.stop()
    logger.info("Event publisher stopped")
    connector_sync_consumer = getattr(_app.state, "connector_sync_consumer", None)
    if connector_sync_consumer:
        await connector_sync_consumer.stop()
        logger.info("Connector sync consumer stopped")
    await BaseRepository.close_pool()
    logger.info("PostgreSQL pool closed")
    logger.info("CRUD Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Holiday Peak Hub CRUD API",
    description="Transactional data operations and user-facing REST APIs",
    version="1.0.0",
    redoc_url="/redoc" if settings.environment != "prod" else None,
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(_request, exc):
    """Global exception handler for unhandled errors."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("error_handler") as span:
        span.set_attribute("error.type", type(exc).__name__)
        span.set_attribute("error.message", str(exc))
        logger.error("Unhandled exception: %s", exc, exc_info=True)

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "type": type(exc).__name__,
        },
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api", tags=["Users"])
app.include_router(products.router, prefix="/api", tags=["Products"])
app.include_router(categories.router, prefix="/api", tags=["Categories"])
app.include_router(cart.router, prefix="/api", tags=["Cart"])
app.include_router(orders.router, prefix="/api", tags=["Orders"])
app.include_router(checkout.router, prefix="/api", tags=["Checkout"])
app.include_router(payments.router, prefix="/api", tags=["Payments"])
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(connector_webhooks.router, tags=["Connector Webhooks"])
app.include_router(reviews.router, prefix="/api", tags=["Reviews"])
app.include_router(acp_products.router, prefix="/acp", tags=["ACP Products"])
app.include_router(acp_checkout.router, prefix="/acp", tags=["ACP Checkout"])
app.include_router(acp_payments.router, prefix="/acp", tags=["ACP Payments"])

# Staff routes
app.include_router(analytics.router, prefix="/api/staff/analytics", tags=["Staff Analytics"])
app.include_router(tickets.router, prefix="/api/staff/tickets", tags=["Staff Tickets"])
app.include_router(returns.router, prefix="/api/staff/returns", tags=["Staff Returns"])
app.include_router(shipments.router, prefix="/api/staff/shipments", tags=["Staff Shipments"])

# Truth-layer routes
app.include_router(truth_attributes.router, prefix="/api", tags=["Truth Attributes"])
app.include_router(proposed_attributes.router, prefix="/api", tags=["Proposed Attributes"])
app.include_router(schemas_registry.router, prefix="/api", tags=["Schemas Registry"])
app.include_router(completeness.router, prefix="/api", tags=["Completeness"])
app.include_router(audit_trail.router, prefix="/api", tags=["Audit Trail"])
app.include_router(ucp_products.router, prefix="/api", tags=["UCP Products"])


@app.get("/")
async def root():
    """Root endpoint - service information."""
    return {
        "service": "crud-service",
        "version": "1.0.0",
        "description": "Holiday Peak Hub CRUD API",
        "docs": "/docs" if settings.environment != "prod" else None,
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "crud_service.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "dev",
        log_level=str(settings.log_level).lower(),
    )
