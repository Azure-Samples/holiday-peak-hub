"""FastAPI application for CRUD operations.

This is NOT an agent service - it's a pure REST API microservice
for transactional data operations and user-facing endpoints.
"""

import logging
from contextlib import asynccontextmanager

from azure.monitor.opentelemetry import configure_azure_monitor
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry import trace

from crud_service.config.settings import get_settings
from crud_service.integrations.event_publisher import get_event_publisher
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
from crud_service.routes.staff import analytics, returns, shipments, tickets

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager - startup and shutdown logic."""
    # Startup
    logger.info("Starting CRUD Service...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Service Name: {settings.service_name}")

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

    logger.info("CRUD Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down CRUD Service...")
    await event_publisher.stop()
    logger.info("Event publisher stopped")
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
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("error_handler") as span:
        span.set_attribute("error.type", type(exc).__name__)
        span.set_attribute("error.message", str(exc))
        logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return {
        "detail": "Internal server error",
        "type": type(exc).__name__,
    }


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
app.include_router(reviews.router, prefix="/api", tags=["Reviews"])

# Staff routes
app.include_router(analytics.router, prefix="/api/staff/analytics", tags=["Staff Analytics"])
app.include_router(tickets.router, prefix="/api/staff/tickets", tags=["Staff Tickets"])
app.include_router(returns.router, prefix="/api/staff/returns", tags=["Staff Returns"])
app.include_router(shipments.router, prefix="/api/staff/shipments", tags=["Staff Shipments"])


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
        log_level=settings.log_level.lower(),
    )
