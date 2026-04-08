"""Ecommerce Catalog Search service entrypoint."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from ecommerce_catalog_search.agents import CatalogSearchAgent, register_mcp_tools
from ecommerce_catalog_search.ai_search import (
    AISearchIndexStatus,
    AISearchSeedResult,
    ai_search_required_runtime_enabled,
    get_catalog_index_status,
    resolve_seed_batch_size,
    resolve_seed_max_attempts,
    seed_catalog_index_from_crud,
)
from ecommerce_catalog_search.event_handlers import build_event_handlers
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "ecommerce-catalog-search"
logger = logging.getLogger(__name__)


def _ensure_seed_runtime_state(service_app: FastAPI, *, reset: bool) -> None:
    max_attempts = resolve_seed_max_attempts()
    batch_size = resolve_seed_batch_size()

    if reset or not hasattr(service_app.state, "catalog_ai_search_seed_attempts_remaining"):
        remaining = max_attempts
    else:
        remaining_raw = getattr(
            service_app.state,
            "catalog_ai_search_seed_attempts_remaining",
            max_attempts,
        )
        try:
            remaining = int(remaining_raw)
        except (TypeError, ValueError):
            remaining = max_attempts
        remaining = max(0, min(remaining, max_attempts))

    service_app.state.catalog_ai_search_seed_max_attempts = max_attempts
    service_app.state.catalog_ai_search_seed_batch_size = batch_size
    service_app.state.catalog_ai_search_seed_attempts_remaining = remaining


async def _seed_with_budget(
    service_app: FastAPI,
    *,
    trigger: str,
    status_reason: str | None,
) -> AISearchSeedResult | None:
    lock = getattr(service_app.state, "catalog_ai_search_seed_lock", None)
    if lock is None:
        lock = asyncio.Lock()
        service_app.state.catalog_ai_search_seed_lock = lock

    async with lock:
        _ensure_seed_runtime_state(service_app, reset=False)
        remaining = int(getattr(service_app.state, "catalog_ai_search_seed_attempts_remaining", 0))
        batch_size = int(
            getattr(
                service_app.state, "catalog_ai_search_seed_batch_size", resolve_seed_batch_size()
            )
        )
        if remaining <= 0:
            logger.warning(
                "catalog_ai_search_seed_budget_exhausted",
                extra={
                    "trigger": trigger,
                    "reason": status_reason,
                },
            )
            return None

        seed_result = await seed_catalog_index_from_crud(
            max_attempts=remaining,
            batch_size=batch_size,
        )
        attempts_used = seed_result.attempt_count if seed_result.attempted else 0
        service_app.state.catalog_ai_search_seed_attempts_remaining = max(
            0,
            remaining - attempts_used,
        )
        service_app.state.catalog_ai_search_last_seed_result = seed_result
        logger.info(
            "catalog_ai_search_seed_attempts_consumed",
            extra={
                "trigger": trigger,
                "reason": status_reason,
                "attempts_used": attempts_used,
                "attempts_remaining": int(
                    getattr(service_app.state, "catalog_ai_search_seed_attempts_remaining", 0)
                ),
                "seed_success": seed_result.success,
                "seed_reason": seed_result.reason,
            },
        )
        return seed_result


def _catalog_dependency_payload(
    service_app: FastAPI,
    *,
    strict_mode: bool,
    status: AISearchIndexStatus,
    seed_result: AISearchSeedResult | None,
) -> dict[str, Any]:
    return {
        "strict_mode": strict_mode,
        "configured": status.configured,
        "reachable": status.reachable,
        "index_non_empty": status.non_empty,
        "ready": bool(status.configured and status.reachable and status.non_empty),
        "reason": status.reason,
        "seed_attempts_remaining": int(
            getattr(service_app.state, "catalog_ai_search_seed_attempts_remaining", 0)
        ),
        "seed_max_attempts": int(
            getattr(service_app.state, "catalog_ai_search_seed_max_attempts", 0)
        ),
        "seed_batch_size": int(getattr(service_app.state, "catalog_ai_search_seed_batch_size", 0)),
        "seed_last": (
            {
                "attempted": seed_result.attempted,
                "success": seed_result.success,
                "attempt_count": seed_result.attempt_count,
                "seeded_documents": seed_result.seeded_documents,
                "reason": seed_result.reason,
            }
            if seed_result is not None
            else None
        ),
    }


async def _run_startup_seed_if_needed(service_app: FastAPI) -> None:
    _ensure_seed_runtime_state(service_app, reset=True)

    status = await get_catalog_index_status()
    service_app.state.catalog_ai_search_last_status = status
    logger.info(
        "catalog_ai_search_startup_check",
        extra={
            "configured": status.configured,
            "reachable": status.reachable,
            "index_non_empty": status.non_empty,
            "reason": status.reason,
        },
    )

    if not status.configured or status.non_empty:
        return

    seed_result = await _seed_with_budget(
        service_app,
        trigger="startup",
        status_reason=status.reason,
    )
    if seed_result is None:
        return

    refreshed_status = await get_catalog_index_status()
    service_app.state.catalog_ai_search_last_status = refreshed_status
    logger.info(
        "catalog_ai_search_startup_post_seed",
        extra={
            "configured": refreshed_status.configured,
            "reachable": refreshed_status.reachable,
            "index_non_empty": refreshed_status.non_empty,
            "reason": refreshed_status.reason,
            "seed_success": seed_result.success,
            "seed_reason": seed_result.reason,
        },
    )


async def _evaluate_catalog_ai_search_readiness(service_app: FastAPI) -> dict[str, Any]:
    _ensure_seed_runtime_state(service_app, reset=False)
    strict_mode = ai_search_required_runtime_enabled()
    status = await get_catalog_index_status()
    service_app.state.catalog_ai_search_last_status = status

    logger.info(
        "catalog_ai_search_readiness_check",
        extra={
            "strict_mode": strict_mode,
            "configured": status.configured,
            "reachable": status.reachable,
            "index_non_empty": status.non_empty,
            "reason": status.reason,
        },
    )

    seed_result: AISearchSeedResult | None = None
    if strict_mode and status.configured and not status.non_empty:
        seed_result = await _seed_with_budget(
            service_app,
            trigger="readiness",
            status_reason=status.reason,
        )
        if seed_result is not None:
            status = await get_catalog_index_status()
            service_app.state.catalog_ai_search_last_status = status

    return _catalog_dependency_payload(
        service_app,
        strict_mode=strict_mode,
        status=status,
        seed_result=seed_result,
    )


def _extract_base_ready_handler(
    service_app: FastAPI,
) -> Callable[[], Awaitable[dict[str, Any]]]:
    for route in list(service_app.router.routes):
        if not isinstance(route, APIRoute):
            continue
        if route.path != "/ready":
            continue
        methods = route.methods or set()
        if "GET" not in methods:
            continue

        endpoint = route.endpoint
        service_app.router.routes.remove(route)
        return endpoint  # type: ignore[return-value]

    raise RuntimeError("Base /ready endpoint is missing from service app.")


def _install_catalog_readiness_guards(service_app: FastAPI) -> FastAPI:
    base_ready_handler = _extract_base_ready_handler(service_app)
    original_lifespan = service_app.router.lifespan_context

    @asynccontextmanager
    async def _catalog_lifespan(wrapped_app: FastAPI):
        async with original_lifespan(wrapped_app):
            await _run_startup_seed_if_needed(wrapped_app)
            yield

    service_app.router.lifespan_context = _catalog_lifespan

    @service_app.get("/ready")
    async def ready() -> dict[str, Any]:
        base_payload = await base_ready_handler()
        catalog_dependency = await _evaluate_catalog_ai_search_readiness(service_app)
        if catalog_dependency["strict_mode"] and not catalog_dependency["ready"]:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "service": SERVICE_NAME,
                    "reason": "Catalog AI Search strict readiness check failed.",
                    "catalog_ai_search": catalog_dependency,
                },
            )

        response = dict(base_payload)
        response["catalog_ai_search"] = catalog_dependency
        return response

    return service_app


def create_app() -> FastAPI:
    service_app = create_standard_app(
        require_foundry_readiness=True,
        disable_tracing_without_foundry=True,
        service_name=SERVICE_NAME,
        agent_class=CatalogSearchAgent,
        mcp_setup=register_mcp_tools,
        subscriptions=[
            EventHubSubscription("product-events", "catalog-search-group"),
        ],
        handlers=build_event_handlers(),
    )
    return _install_catalog_readiness_guards(service_app)


app = create_app()
