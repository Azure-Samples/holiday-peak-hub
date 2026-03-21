"""FastAPI application for CRUD operations.

This is NOT an agent service - it's a pure REST API microservice
for transactional data operations and user-facing endpoints.
"""

import os
from contextlib import asynccontextmanager
from importlib import import_module
from typing import Any

from azure.monitor.opentelemetry import configure_azure_monitor
from crud_service.auth.dependencies import get_key_vault_secret
from crud_service.composition import register_routes
from crud_service.config.settings import get_settings
from crud_service.consumers import get_connector_sync_consumer
from crud_service.integrations.event_publisher import get_event_publisher
from crud_service.repositories.base import BaseRepository
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from holiday_peak_lib.utils import (
    CORRELATION_HEADER,
    clear_correlation_id,
    configure_logging,
    set_correlation_id,
)
from opentelemetry import trace

# Get settings
settings = get_settings()
logger = configure_logging(app_name=settings.service_name)


def create_connector_registry() -> Any | None:
    try:
        connector_module = import_module("holiday_peak_lib.connectors.registry")
        registry_class = getattr(connector_module, "ConnectorRegistry")
        return registry_class()
    except (ImportError, AttributeError) as exc:
        logger.warning("Connector registry unavailable; skipping connector bootstrap: %s", exc)
        return None


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

    configured_domains = [
        item.strip().lower()
        for item in (os.getenv("CONNECTOR_ENABLED_DOMAINS", "").split(","))
        if item.strip()
    ]
    if configured_domains:
        connector_registry = create_connector_registry()
        if connector_registry is not None:
            discovered = await connector_registry.discover()
            logger.info("Connector classes discovered: %s", discovered)
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
    connector_registry = getattr(_app.state, "connector_registry", None)
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


@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    incoming_correlation = (
        request.headers.get(CORRELATION_HEADER)
        or request.headers.get("X-Correlation-ID")
        or request.headers.get("x-request-id")
    )
    correlation_id = set_correlation_id(incoming_correlation)
    try:
        response = await call_next(request)
    finally:
        clear_correlation_id()
    response.headers["X-Correlation-ID"] = correlation_id
    return response


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


register_routes(app)


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
