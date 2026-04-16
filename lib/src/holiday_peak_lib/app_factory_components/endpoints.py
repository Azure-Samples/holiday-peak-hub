"""Endpoint registration helpers for service apps."""

import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, HTTPException
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from holiday_peak_lib.self_healing import FailureSignal, SelfHealingKernel, SurfaceType
from holiday_peak_lib.utils import get_tracer
from holiday_peak_lib.utils.logging import log_async_operation
from starlette.responses import StreamingResponse

_DEFAULT_ENDPOINT_TIMEOUT = float(os.getenv("AGENT_ENDPOINT_TIMEOUT_SECONDS", "120"))


@dataclass(frozen=True, slots=True)
class EndpointContext:
    """Bundles all dependencies needed by ``register_standard_endpoints``.

    Replaces the 14-parameter function signature with a single immutable
    Parameter Object (Refactoring: *Introduce Parameter Object*).
    """

    service_name: str
    registry: ConnectorRegistry
    router: RoutingStrategy
    tracer: Any
    logger: Any
    strict_foundry_mode: bool
    require_foundry_readiness: bool
    is_foundry_ready: Callable[[], bool]
    set_foundry_ready: Callable[[bool], None]
    requires_foundry_runtime_resolution: Callable[[], bool]
    foundry_capabilities: Callable[[], dict[str, Any]]
    ensure_agents_handler: Callable[[dict | None], Awaitable[dict[str, Any]]]
    self_healing_kernel: SelfHealingKernel | None = field(default=None)


def _sse_event(event_type: str, data: Any) -> str:
    """Format a single Server-Sent Event frame.

    # No GoF pattern applies — pure data formatting utility.
    """
    payload = json.dumps(data, default=str) if not isinstance(data, str) else data
    return f"event: {event_type}\ndata: {payload}\n\n"


def register_standard_endpoints(
    app: FastAPI,
    *,
    # Accept either an EndpointContext or individual keyword arguments.
    ctx: EndpointContext | None = None,
    service_name: str = "",
    registry: ConnectorRegistry | None = None,
    router: RoutingStrategy | None = None,
    tracer: Any = None,
    logger: Any = None,
    strict_foundry_mode: bool = False,
    require_foundry_readiness: bool = False,
    is_foundry_ready: Callable[[], bool] | None = None,
    set_foundry_ready: Callable[[bool], None] | None = None,
    requires_foundry_runtime_resolution: Callable[[], bool] | None = None,
    foundry_capabilities: Callable[[], dict[str, Any]] | None = None,
    ensure_agents_handler: Callable[[dict | None], Awaitable[dict[str, Any]]] | None = None,
    self_healing_kernel: SelfHealingKernel | None = None,
) -> None:
    """Register common health, invoke, telemetry and Foundry endpoints.

    Accepts either an ``EndpointContext`` via *ctx* or individual keyword
    arguments for backward compatibility.  When *ctx* is supplied, the
    individual kwargs are ignored.

    Foundry readiness enforcement is controlled by
    ``require_foundry_readiness`` and ``strict_foundry_mode``.
    """
    # --- Resolve EndpointContext -------------------------------------------
    if ctx is not None:
        service_name = ctx.service_name
        registry = ctx.registry
        router = ctx.router
        tracer = ctx.tracer
        logger = ctx.logger
        strict_foundry_mode = ctx.strict_foundry_mode
        require_foundry_readiness = ctx.require_foundry_readiness
        is_foundry_ready = ctx.is_foundry_ready
        set_foundry_ready = ctx.set_foundry_ready
        requires_foundry_runtime_resolution = ctx.requires_foundry_runtime_resolution
        foundry_capabilities = ctx.foundry_capabilities
        ensure_agents_handler = ctx.ensure_agents_handler
        self_healing_kernel = ctx.self_healing_kernel

    def _log_info(message: str, extra: dict[str, Any] | None = None) -> None:
        _log_with_level("info", message, extra=extra)

    def _log_with_level(
        level: str,
        message: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> None:
        log_method = getattr(logger, level, None)
        if not callable(log_method):
            log_method = getattr(logger, "info", None)

        if callable(log_method):
            try:
                log_method(message, extra=extra or {})
            except TypeError:
                log_method(message)

    def _coerce_optional_string(value: Any) -> str | None:
        if value is None:
            return None
        resolved = str(value).strip()
        return resolved or None

    def _emit_invoke_outcome_telemetry(
        *,
        intent: str,
        request_payload: dict[str, Any],
        response_payload: dict[str, Any] | None = None,
        error: Exception | None = None,
    ) -> None:
        payload = response_payload if isinstance(response_payload, dict) else {}

        degraded = bool(payload.get("degraded"))
        degraded_reason = _coerce_optional_string(payload.get("degraded_reason"))
        requested_mode = _coerce_optional_string(
            payload.get("requested_mode")
            if payload.get("requested_mode") is not None
            else request_payload.get("mode")
        )
        resolved_mode = _coerce_optional_string(payload.get("mode"))
        search_stage = _coerce_optional_string(payload.get("search_stage"))
        correlation_id = _coerce_optional_string(request_payload.get("correlation_id"))
        session_id = _coerce_optional_string(
            request_payload.get("session_id")
            if request_payload.get("session_id") is not None
            else payload.get("session_id")
        )
        trace_id = _coerce_optional_string(payload.get("trace_id"))
        result_type = _coerce_optional_string(payload.get("result_type"))
        model_status = _coerce_optional_string(payload.get("model_status"))
        model_attempted = bool(payload.get("model_attempted"))

        if error is not None:
            outcome_status = "error"
            log_level = "error"
            status_code = int(error.status_code) if isinstance(error, HTTPException) else 500
            failure_reason = "invoke_error"
            error_class = type(error).__name__
            result_type = result_type or "error"
        elif degraded:
            outcome_status = "degraded"
            log_level = "warning"
            status_code = 200
            failure_reason = degraded_reason
            error_class = None
            result_type = result_type or "degraded_fallback"
        else:
            outcome_status = "success"
            log_level = "info"
            status_code = 200
            failure_reason = None
            error_class = None
            result_type = result_type or "deterministic"

        outcome_metadata = {
            "service": service_name,
            "endpoint": "/invoke",
            "intent": intent,
            "outcome_status": outcome_status,
            "result_type": result_type,
            "degraded": degraded,
            "degraded_reason": degraded_reason,
            "failure_reason": failure_reason,
            "error_class": error_class,
            "requested_mode": requested_mode,
            "resolved_mode": resolved_mode,
            "search_stage": search_stage,
            "model_attempted": model_attempted,
            "model_status": model_status,
            "session_id": session_id,
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "http_status_code": status_code,
        }

        _log_with_level(log_level, "service_invoke_outcome", extra=outcome_metadata)

        trace_decision = getattr(tracer, "trace_decision", None)
        if callable(trace_decision):
            try:
                trace_decision(  # pylint: disable=not-callable
                    decision="invoke_outcome",
                    outcome=outcome_status,
                    metadata=outcome_metadata,
                )
            except (AttributeError, TypeError, ValueError, RuntimeError):
                _log_info(
                    "service_invoke_outcome_trace_failed",
                    extra={
                        "service": service_name,
                        "intent": intent,
                        "outcome_status": outcome_status,
                    },
                )

    async def _emit_self_healing_failure(
        *,
        surface: SurfaceType,
        component: str,
        error: Exception,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self_healing_kernel is None or not self_healing_kernel.enabled:
            return

        status_code = None
        if isinstance(error, HTTPException):
            status_code = int(error.status_code)
        else:
            status_code = 500

        signal = FailureSignal(
            service_name=service_name,
            surface=surface,
            component=component,
            status_code=status_code,
            error_type=type(error).__name__,
            error_message=str(error),
            metadata=metadata or {},
        )
        try:
            await self_healing_kernel.handle_failure_signal(signal)
        except (AttributeError, TypeError, ValueError, RuntimeError):
            _log_info(
                "self_healing_signal_failed",
                extra={"service": service_name, "component": component},
            )

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
        capability_payload = foundry_capabilities()
        foundry_enforced = require_foundry_readiness or strict_foundry_mode
        foundry_ready = bool(capability_payload.get("ready", is_foundry_ready()))
        if foundry_enforced and not foundry_ready:
            raise HTTPException(
                status_code=503,
                detail={
                    "status": "not_ready",
                    "service": service_name,
                    "reason": "Foundry runtime is not ready. "
                    "Call POST /foundry/agents/ensure and verify Foundry "
                    "SLM/LLM targets are bound before serving traffic.",
                    "foundry": capability_payload,
                },
            )
        return {
            "status": "ready",
            "service": service_name,
            "foundry_ready": foundry_ready,
            "foundry_required": foundry_enforced,
            "foundry": capability_payload,
            "integrations_registered": await registry.count(),
        }

    @app.post("/invoke")
    async def invoke(payload: dict) -> dict[str, Any]:
        intent = str(payload.get("intent", "default"))
        request_payload = payload.get("payload", payload)
        if not isinstance(request_payload, dict):
            request_payload = {"query": str(request_payload)}

        try:
            invoke_foundry_enforced = require_foundry_readiness or strict_foundry_mode
            capability_payload = foundry_capabilities()
            needs_runtime_resolution = bool(
                capability_payload.get(
                    "runtime_resolution_required",
                    requires_foundry_runtime_resolution(),
                )
            )
            foundry_ready = bool(capability_payload.get("ready", is_foundry_ready()))
            if needs_runtime_resolution or (invoke_foundry_enforced and not foundry_ready):
                _log_info(
                    "foundry_invoke_auto_ensure_start",
                    extra={
                        "service": service_name,
                        "require_foundry_readiness": require_foundry_readiness,
                        "strict_mode": strict_foundry_mode,
                        "needs_runtime_resolution": needs_runtime_resolution,
                        "foundry_ready_before": foundry_ready,
                        "configured_roles": capability_payload.get("configured_roles"),
                        "unresolved_roles": capability_payload.get("unresolved_roles"),
                    },
                )
                ensure_result: dict[str, Any] | None = None
                ensure_failure: (
                    AttributeError | ImportError | RuntimeError | TypeError | ValueError | None
                ) = None
                try:
                    ensure_result = await ensure_agents_handler(None)
                except (AttributeError, ImportError, RuntimeError, TypeError, ValueError) as exc:
                    ensure_failure = exc

                if ensure_failure is not None:
                    if invoke_foundry_enforced:
                        raise HTTPException(
                            status_code=503,
                            detail=(
                                "Unable to resolve Foundry runtime definitions before invoke. "
                                "Call POST /foundry/agents/ensure and retry."
                            ),
                        ) from ensure_failure

                    _log_info(
                        "foundry_invoke_auto_ensure_non_blocking_failure",
                        extra={
                            "service": service_name,
                            "require_foundry_readiness": require_foundry_readiness,
                            "strict_mode": strict_foundry_mode,
                            "error_type": type(ensure_failure).__name__,
                        },
                    )

                if isinstance(ensure_result, dict):
                    set_foundry_ready(bool(ensure_result.get("foundry_ready", foundry_ready)))
                    capability_payload = foundry_capabilities()
                    foundry_ready = bool(capability_payload.get("ready", is_foundry_ready()))
                    needs_runtime_resolution = bool(
                        capability_payload.get(
                            "runtime_resolution_required",
                            requires_foundry_runtime_resolution(),
                        )
                    )
                    _log_info(
                        "foundry_invoke_auto_ensure_done",
                        extra={
                            "service": service_name,
                            "require_foundry_readiness": require_foundry_readiness,
                            "strict_mode": strict_foundry_mode,
                            "foundry_ready_after": foundry_ready,
                            "unresolved_roles": capability_payload.get("unresolved_roles"),
                            "last_error": capability_payload.get("last_error"),
                            "resolved_roles": [
                                role
                                for role, details in (ensure_result.get("results") or {}).items()
                                if isinstance(details, dict)
                                and bool(details.get("agent_id"))
                                and details.get("status") in {"exists", "found_by_name", "created"}
                            ],
                        },
                    )

            if invoke_foundry_enforced and not foundry_ready:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Foundry readiness enforcement is enabled and no Foundry target is ready. "
                        "Call POST /foundry/agents/ensure first."
                    ),
                )

            if invoke_foundry_enforced and needs_runtime_resolution:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Foundry runtime definitions are unresolved. "
                        "Call POST /foundry/agents/ensure and retry."
                    ),
                )

            otel_tracer = get_tracer(service_name)

            async def _route_with_span() -> dict[str, Any]:
                with otel_tracer.start_as_current_span("agent.handle") as span:
                    try:
                        span.set_attribute("agent.service", service_name)
                        span.set_attribute("agent.intent", intent)
                        span.set_attribute("agent.payload_size", len(str(request_payload)))
                    except (AttributeError, TypeError, ValueError):
                        _log_info(
                            "agent_handle_span_attribute_failed",
                            extra={"service": service_name, "intent": intent},
                        )
                    return await router.route(intent, request_payload)

            try:
                response_payload = await asyncio.wait_for(
                    log_async_operation(
                        logger,
                        name="service.invoke",
                        intent=intent,
                        func=_route_with_span,
                        token_count=None,
                        metadata={
                            "payload_size": len(str(request_payload)),
                            "service": service_name,
                        },
                    ),
                    timeout=_DEFAULT_ENDPOINT_TIMEOUT,
                )
            except asyncio.TimeoutError:
                _log_info(
                    "invoke_endpoint_timeout",
                    extra={
                        "service": service_name,
                        "intent": intent,
                        "timeout_seconds": _DEFAULT_ENDPOINT_TIMEOUT,
                    },
                )
                _emit_invoke_outcome_telemetry(
                    intent=intent,
                    request_payload=request_payload,
                    error=TimeoutError(f"Invoke timed out after {_DEFAULT_ENDPOINT_TIMEOUT}s"),
                )
                raise HTTPException(
                    status_code=504,
                    detail=(
                        f"Agent invocation timed out after {_DEFAULT_ENDPOINT_TIMEOUT:.0f}s. "
                        "Please retry with a simpler query."
                    ),
                )
            _emit_invoke_outcome_telemetry(
                intent=intent,
                request_payload=request_payload,
                response_payload=response_payload if isinstance(response_payload, dict) else None,
            )
            return response_payload
        except Exception as exc:
            _emit_invoke_outcome_telemetry(
                intent=intent,
                request_payload=request_payload,
                error=exc,
            )
            await _emit_self_healing_failure(
                surface=SurfaceType.API,
                component="/invoke",
                error=exc,
                metadata={"intent": intent, "payload_size": len(str(request_payload))},
            )
            raise

    @app.post("/invoke/stream")
    async def invoke_stream(payload: dict) -> StreamingResponse:
        """SSE endpoint that streams agent responses as Server-Sent Events.

        Event types:
        - ``results``: deterministic search results (emitted first)
        - ``token``: model answer text chunk
        - ``done``: final metadata
        - ``error``: on failure
        """
        intent = str(payload.get("intent", "default"))
        request_payload = payload.get("payload", payload)
        if not isinstance(request_payload, dict):
            request_payload = {"query": str(request_payload)}

        # Signal the agent handler to return a streaming response
        request_payload["_stream"] = True

        async def event_generator():
            try:
                result = await router.route(intent, request_payload)

                # If the agent returned an async generator, iterate it
                if hasattr(result, "__aiter__"):
                    async for event in result:
                        if isinstance(event, dict):
                            event_type = event.get("event", "token")
                            yield _sse_event(event_type, event)
                        else:
                            yield _sse_event("token", {"text": str(event)})
                elif isinstance(result, dict):
                    # Non-streaming fallback: emit the entire response as one SSE event
                    yield _sse_event("results", result)

                yield _sse_event("done", {"status": "complete"})

            except asyncio.TimeoutError:
                yield _sse_event(
                    "error",
                    {
                        "error": "timeout",
                        "message": f"Agent invocation timed out after {_DEFAULT_ENDPOINT_TIMEOUT:.0f}s.",
                    },
                )
            except Exception as exc:
                yield _sse_event(
                    "error",
                    {
                        "error": type(exc).__name__,
                        "message": str(exc)[:500],
                    },
                )

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/self-healing/status")
    async def self_healing_status() -> dict[str, Any]:
        if self_healing_kernel is None:
            return {
                "service": service_name,
                "enabled": False,
                "detect_only": False,
                "manifest": None,
            }
        return self_healing_kernel.status()

    @app.get("/self-healing/incidents")
    async def self_healing_incidents(limit: int = 50) -> dict[str, Any]:
        if self_healing_kernel is None:
            return {"service": service_name, "incidents": []}

        incidents = [
            incident.model_dump(mode="json")
            for incident in self_healing_kernel.list_incidents(limit=limit)
        ]
        return {
            "service": service_name,
            "count": len(incidents),
            "incidents": incidents,
        }

    @app.post("/self-healing/reconcile")
    async def self_healing_reconcile(payload: dict | None = None) -> dict[str, Any]:
        if self_healing_kernel is None:
            return {
                "service": service_name,
                "enabled": False,
                "reconciled_incidents": 0,
                "incident_ids": [],
            }

        body = payload if isinstance(payload, dict) else {}
        incident_id_raw = body.get("incident_id")
        incident_id = str(incident_id_raw) if incident_id_raw else None
        return await self_healing_kernel.reconcile(incident_id=incident_id)

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
