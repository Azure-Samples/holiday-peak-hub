"""Endpoint registration helpers for service apps."""

from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import FastAPI, HTTPException
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy
from holiday_peak_lib.connectors.registry import ConnectorRegistry
from holiday_peak_lib.self_healing import FailureSignal, SelfHealingKernel, SurfaceType
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
    requires_foundry_runtime_resolution: Callable[[], bool],
    ensure_agents_handler: Callable[[dict | None], Awaitable[dict[str, Any]]],
    self_healing_kernel: SelfHealingKernel | None = None,
) -> None:
    """Register common health, invoke, telemetry and Foundry endpoints."""

    def _log_info(message: str, extra: dict[str, Any] | None = None) -> None:
        log_method = getattr(logger, "info", None)
        if callable(log_method):
            try:
                log_method(message, extra=extra or {})
            except TypeError:
                log_method(message)

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
        intent = str(payload.get("intent", "default"))
        request_payload = payload.get("payload", payload)
        if not isinstance(request_payload, dict):
            request_payload = {"query": str(request_payload)}

        try:
            needs_runtime_resolution = requires_foundry_runtime_resolution()
            if needs_runtime_resolution or (strict_foundry_mode and not is_foundry_ready()):
                _log_info(
                    "foundry_invoke_auto_ensure_start",
                    extra={
                        "service": service_name,
                        "strict_mode": strict_foundry_mode,
                        "needs_runtime_resolution": needs_runtime_resolution,
                        "foundry_ready_before": is_foundry_ready(),
                    },
                )
                try:
                    ensure_result = await ensure_agents_handler(None)
                except HTTPException:
                    raise
                except Exception as exc:  # pragma: no cover - defensive endpoint guard
                    raise HTTPException(
                        status_code=503,
                        detail=(
                            "Unable to resolve Foundry runtime definitions before invoke. "
                            "Call POST /foundry/agents/ensure and retry."
                        ),
                    ) from exc

                set_foundry_ready(bool(ensure_result.get("foundry_ready", is_foundry_ready())))
                _log_info(
                    "foundry_invoke_auto_ensure_done",
                    extra={
                        "service": service_name,
                        "strict_mode": strict_foundry_mode,
                        "foundry_ready_after": is_foundry_ready(),
                        "resolved_roles": [
                            role
                            for role, details in (ensure_result.get("results") or {}).items()
                            if isinstance(details, dict)
                            and bool(details.get("agent_id"))
                            and details.get("status") in {"exists", "found_by_name", "created"}
                        ],
                    },
                )

            if strict_foundry_mode and not is_foundry_ready():
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Strict Foundry enforcement is enabled and no Foundry target is ready. "
                        "Call POST /foundry/agents/ensure first."
                    ),
                )

            if requires_foundry_runtime_resolution():
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
        except Exception as exc:
            await _emit_self_healing_failure(
                surface=SurfaceType.API,
                component="/invoke",
                error=exc,
                metadata={"intent": intent, "payload_size": len(str(request_payload))},
            )
            raise

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
