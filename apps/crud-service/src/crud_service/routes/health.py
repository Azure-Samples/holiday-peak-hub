"""Health check route."""

import logging
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)


async def _check_redis() -> tuple[str, str]:
    """Return (status, detail) for the Redis connection."""
    redis_host = os.getenv("REDIS_HOST", "")
    if not redis_host:
        return "unconfigured", "REDIS_HOST not set"
    try:
        import redis.asyncio as aioredis  # type: ignore[import]

        redis_port = int(os.getenv("REDIS_PORT", "6380"))
        redis_ssl = os.getenv("REDIS_SSL", "true").lower() == "true"
        client = aioredis.Redis(host=redis_host, port=redis_port, ssl=redis_ssl, socket_timeout=2)
        await client.ping()
        await client.aclose()
        return "healthy", "ping ok"
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("health_check redis error: %s", exc)
        return "unhealthy", str(exc)


async def _check_cosmos() -> tuple[str, str]:
    """Return (status, detail) for the Cosmos DB connection."""
    cosmos_uri = os.getenv("COSMOS_ACCOUNT_URI", "")
    if not cosmos_uri:
        return "unconfigured", "COSMOS_ACCOUNT_URI not set"
    try:
        from azure.cosmos.aio import CosmosClient  # type: ignore[import]
        from azure.identity.aio import DefaultAzureCredential  # type: ignore[import]

        credential = DefaultAzureCredential()
        async with CosmosClient(cosmos_uri, credential=credential) as client:
            await client.get_database_client(os.getenv("COSMOS_DATABASE", "holiday_peak")).read()
        return "healthy", "read ok"
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("health_check cosmos error: %s", exc)
        return "unhealthy", str(exc)


@router.get("/health")
async def health_check():
    """Basic liveness endpoint — always returns 200 when the process is up."""
    return {"status": "healthy", "service": "crud-service"}


@router.get("/ready")
async def readiness_check():
    """Readiness probe: checks Redis and Cosmos DB connectivity."""
    checks: dict[str, dict] = {}
    overall = "ready"

    redis_status, redis_detail = await _check_redis()
    checks["redis"] = {"status": redis_status, "detail": redis_detail}
    if redis_status == "unhealthy":
        overall = "degraded"

    cosmos_status, cosmos_detail = await _check_cosmos()
    checks["cosmos"] = {"status": cosmos_status, "detail": cosmos_detail}
    if cosmos_status == "unhealthy":
        overall = "degraded"

    status_code = 200 if overall == "ready" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "service": "crud-service", "checks": checks},
    )
