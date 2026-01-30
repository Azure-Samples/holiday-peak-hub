"""Health check route."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "crud-service"}


@router.get("/ready")
async def readiness_check():
    """
    Readiness check with dependency validation.
    
    TODO: Check Cosmos DB, Event Hubs, Redis connectivity.
    """
    return {"status": "ready", "service": "crud-service"}
