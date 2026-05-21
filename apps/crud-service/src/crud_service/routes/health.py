"""Health check route."""

import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

from crud_service.config.settings import get_settings
from crud_service.repositories.base import BaseRepository
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()
logger = logging.getLogger(__name__)

ReadinessDetail = str | dict[str, Any]
ReadinessResult = tuple[str, ReadinessDetail]
ReadinessCheck = Callable[[], Awaitable[ReadinessResult]]


async def _check_redis(request: Request) -> tuple[str, str]:
    """Return (status, detail) for the Redis connection."""
    init_error = getattr(request.app.state, "redis_secret_init_error", None)
    try:
        import redis.asyncio as aioredis  # type: ignore[import]

        redis_url = get_settings().redis_url
        client = aioredis.Redis.from_url(redis_url, socket_timeout=2)
        await client.ping()
        await client.aclose()
        if init_error:
            logger.info("Redis recovered after startup secret retrieval error: %s", init_error)
            request.app.state.redis_secret_init_error = None
        return "healthy", "ping ok"
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("health_check redis error: %s", exc)
        if init_error:
            return "unhealthy", f"{init_error}; latest: {exc}"
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


async def _check_postgres(request: Request) -> tuple[str, str]:
    """Return (status, detail) for PostgreSQL pool readiness."""
    init_error = getattr(request.app.state, "db_pool_init_error", None)
    pool_status, pool_detail = await BaseRepository.check_pool_health()

    # A startup init error can be transient (for example, during dependency warm-up).
    # If the current health check succeeds, clear stale state so readiness can recover.
    if pool_status == "healthy":
        if init_error:
            logger.info("PostgreSQL pool recovered after startup init error: %s", init_error)
            request.app.state.db_pool_init_error = None
        return pool_status, pool_detail

    if init_error:
        return "unhealthy", f"{init_error}; latest: {pool_detail}"

    return pool_status, pool_detail


async def _check_connectors(request: Request) -> ReadinessResult:
    """Return (status, detail) for runtime connector readiness."""
    connector_registry = getattr(request.app.state, "connector_registry", None)
    if connector_registry is None:
        return "unconfigured", "No runtime connector registry configured"

    connector_health = await connector_registry.health()
    if not connector_health:
        return "unconfigured", "No runtime connectors registered"

    unhealthy = [name for name, ok in connector_health.items() if not ok]
    return (
        "healthy" if not unhealthy else "unhealthy",
        {
            "registered": len(connector_health),
            "unhealthy": unhealthy,
        },
    )


async def _run_readiness_check(
    name: str,
    check: ReadinessCheck,
    timeout_seconds: float,
) -> tuple[str, dict[str, Any]]:
    """Apply the readiness timeout policy around one dependency check."""
    try:
        status, detail = await asyncio.wait_for(check(), timeout=timeout_seconds)
        return name, {"status": status, "detail": detail}
    except TimeoutError:
        logger.warning(
            "readiness_check %s timeout after %.3f seconds",
            name,
            timeout_seconds,
        )
        return name, {
            "status": "unhealthy",
            "detail": {
                "error": "timeout",
                "timeout_seconds": timeout_seconds,
                "message": (f"{name} readiness check exceeded " f"{timeout_seconds:g} seconds"),
            },
        }
    except Exception as exc:  # pylint: disable=broad-except
        logger.warning("readiness_check %s error: %s", name, exc)
        return name, {
            "status": "unhealthy",
            "detail": {
                "error": type(exc).__name__,
                "message": str(exc),
            },
        }


@router.get("/health")
async def health_check():
    """Basic liveness endpoint — always returns 200 when the process is up."""
    return {"status": "healthy", "service": "crud-service"}


@router.get("/ready")
async def readiness_check(request: Request):
    """Readiness probe: checks Redis, Cosmos DB, and PostgreSQL connectivity."""
    timeout_seconds = get_settings().readiness_dependency_timeout_seconds
    readiness_checks: list[tuple[str, ReadinessCheck]] = [
        ("postgres", lambda: _check_postgres(request)),
        ("redis", lambda: _check_redis(request)),
        ("cosmos", _check_cosmos),
    ]
    if getattr(request.app.state, "connector_registry", None) is not None:
        readiness_checks.append(("connectors", lambda: _check_connectors(request)))

    check_results = await asyncio.gather(
        *(_run_readiness_check(name, check, timeout_seconds) for name, check in readiness_checks)
    )
    checks = dict(check_results)
    overall = (
        "degraded"
        if any(result["status"] == "unhealthy" for result in checks.values())
        else "ready"
    )

    status_code = 200 if overall == "ready" else 503
    return JSONResponse(
        status_code=status_code,
        content={"status": overall, "service": "crud-service", "checks": checks},
    )
