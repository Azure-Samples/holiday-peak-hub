"""Ecommerce Catalog Search service entrypoint.

Agent isolation rules:
    * No CRUD service calls.
    * Product read path is Azure AI Search; agent applies a secondary
      intent-grounding filter on retrieved results.
    * AI Search index population is owned by the ``search-enrichment-agent``
      service (async, Event Hub driven). This agent does NOT seed the index.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from ecommerce_catalog_search.agents import CatalogSearchAgent, register_mcp_tools
from ecommerce_catalog_search.ai_search import (
    AISearchIndexStatus,
    ai_search_required_runtime_enabled,
    get_catalog_index_status,
)
from ecommerce_catalog_search.event_handlers import build_event_handlers
from fastapi import FastAPI, HTTPException
from fastapi.routing import APIRoute
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription

SERVICE_NAME = "ecommerce-catalog-search"
logger = logging.getLogger(__name__)


def _catalog_dependency_payload(
    *,
    strict_mode: bool,
    status: AISearchIndexStatus,
) -> dict[str, Any]:
    return {
        "strict_mode": strict_mode,
        "configured": status.configured,
        "reachable": status.reachable,
        "index_non_empty": status.non_empty,
        "ready": bool(status.configured and status.reachable and status.non_empty),
        "reason": status.reason,
    }


async def _evaluate_catalog_ai_search_readiness(service_app: FastAPI) -> dict[str, Any]:
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

    return _catalog_dependency_payload(strict_mode=strict_mode, status=status)


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
