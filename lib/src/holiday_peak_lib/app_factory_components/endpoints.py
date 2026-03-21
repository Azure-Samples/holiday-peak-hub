"""Endpoint registration helpers for service apps."""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, HTTPException
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from holiday_peak_lib.utils import get_tracer
from holiday_peak_lib.utils.logging import log_async_operation


def register_standard_endpoints(
    app: FastAPI,
    *,
    service_name: str,
    registry: ConnectorRegistry,
    router: RoutingStrategy,
    tracer: Any,
    logger: Any,
    strict_foundry_mode: bool,
    is_foundry_ready: Callable[[], bool],
    set_foundry_ready: Callable[[bool], None],
    ensure_agents_handler: Callable[[dict | None], Awaitable[dict[str, Any]]],
) -> None:
    """Register common health, invoke, telemetry and Foundry endpoints."""

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "service": service_name,
            "integrations_registered": await registry.count(),
        }

    @app.get("/integrations")
    async def integrations() -> dict[str, Any]:
        return {
            "service": service_name,
            "domains": await registry.list_domains(),
            "health": await registry.health(),
        }

    @app.get("/ready")
    async def ready() -> dict[str, Any]:
        if strict_foundry_mode and not is_foundry_ready():
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "service": service_name,
                    "reason": "Foundry agents not provisioned. "
                    "Call POST /foundry/agents/ensure or set "
                    "FOUNDRY_AUTO_ENSURE_ON_STARTUP=true.",
                },
            )
        return {
            "status": "ready",
            "service": service_name,
            "foundry_ready": is_foundry_ready(),
            "integrations_registered": await registry.count(),
        }

    @app.post("/invoke")
    async def invoke(payload: dict) -> dict[str, Any]:
        if strict_foundry_mode and not is_foundry_ready():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Strict Foundry enforcement is enabled and no Foundry target is ready. "
                    "Call POST /foundry/agents/ensure first."
                ),
            )

        intent = str(payload.get("intent", "default"))
        request_payload = payload.get("payload", payload)
        if not isinstance(request_payload, dict):
            request_payload = {"query": str(request_payload)}

        otel_tracer = get_tracer(service_name)

        async def _route_with_span() -> dict[str, Any]:
            with otel_tracer.start_as_current_span("agent.handle") as span:
                try:
                    span.set_attribute("agent.service", service_name)
                    span.set_attribute("agent.intent", intent)
                    span.set_attribute("agent.payload_size", len(str(request_payload)))
                except (AttributeError, TypeError, ValueError):
                    pass
                return await router.route(intent, request_payload)

        return await log_async_operation(
            logger,
            name="service.invoke",
            intent=intent,
            func=_route_with_span,
            token_count=None,
            metadata={
                "payload_size": len(str(request_payload)),
                "service": service_name,
            },
        )

    @app.get("/agent/traces")
    async def agent_traces(limit: int = 50) -> dict[str, Any]:
        return {
            "service": service_name,
            "traces": tracer.get_traces(limit=limit),
        }

    @app.get("/agent/metrics")
    async def agent_metrics() -> dict[str, Any]:
        return tracer.get_metrics()

    @app.get("/agent/evaluation/latest")
    async def agent_evaluation_latest() -> dict[str, Any]:
        latest = tracer.get_latest_evaluation()
        return {
            "service": service_name,
            "latest": latest,
        }

    @app.post("/foundry/agents/ensure")
    async def ensure_agents(payload: dict | None = None) -> dict[str, Any]:
        result = await ensure_agents_handler(payload)
        set_foundry_ready(bool(result.get("foundry_ready", is_foundry_ready())))
        return result
