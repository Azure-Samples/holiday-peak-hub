"""Tests for app_factory_components.endpoints."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from holiday_peak_lib.app_factory_components.endpoints import register_standard_endpoints
from holiday_peak_lib.self_healing import SelfHealingKernel, default_surface_manifest


class _Registry:
    async def count(self) -> int:
        return 1

    async def list_domains(self) -> dict[str, list[str]]:
        return {"pim": ["mock"]}

    async def health(self) -> dict[str, str]:
        return {"mock": "ok"}


class _Router:
    async def route(self, _intent: str, payload: dict) -> dict:
        return {"ok": True, "payload": payload}


class _FailingRouter:
    async def route(self, _intent: str, _payload: dict) -> dict:
        raise HTTPException(status_code=503, detail="upstream_unavailable")


class _DegradedRouter:
    async def route(self, _intent: str, _payload: dict) -> dict:
        return {
            "service": "svc",
            "mode": "intelligent",
            "requested_mode": "intelligent",
            "search_stage": "rerank",
            "session_id": "session-123",
            "trace_id": "trace-123",
            "result_type": "degraded_fallback",
            "degraded": True,
            "degraded_reason": "model_timeout",
            "model_attempted": True,
            "model_status": "timeout",
            "results": [],
        }


class _Tracer:
    def get_traces(self, limit: int = 50) -> list[dict]:
        return [{"limit": limit}]

    def get_metrics(self) -> dict[str, int]:
        return {"count": 1}

    def get_latest_evaluation(self) -> dict[str, str]:
        return {"status": "pass"}


class _Logger:
    def __init__(self) -> None:
        self.records: list[dict[str, object]] = []

    def _record(self, level: str, message: object, kwargs: dict) -> None:
        self.records.append(
            {
                "level": level,
                "message": str(message),
                "extra": kwargs.get("extra") or {},
            }
        )

    def info(self, *_args, **_kwargs) -> None:
        self._record("info", _args[0] if _args else "", _kwargs)

    def warning(self, *_args, **_kwargs) -> None:
        self._record("warning", _args[0] if _args else "", _kwargs)

    def error(self, *_args, **_kwargs) -> None:
        self._record("error", _args[0] if _args else "", _kwargs)

    def exception(self, *_args, **_kwargs) -> None:
        self._record("exception", _args[0] if _args else "", _kwargs)


def test_register_standard_endpoints_ready_and_ensure_flow():
    app = FastAPI()
    foundry_ready = False
    runtime_definitions_missing = True

    def _is_ready() -> bool:
        return foundry_ready

    def _set_ready(value: bool) -> None:
        nonlocal foundry_ready
        foundry_ready = value

    def _requires_runtime_resolution() -> bool:
        return runtime_definitions_missing

    async def _ensure_handler(_payload: dict | None) -> dict:
        nonlocal runtime_definitions_missing
        runtime_definitions_missing = False
        return {
            "service": "svc",
            "strict_foundry_mode": True,
            "foundry_ready": True,
            "results": {"fast": {"status": "exists", "agent_id": "a1"}},
        }

    register_standard_endpoints(
        app,
        service_name="svc",
        registry=_Registry(),
        router=_Router(),
        tracer=_Tracer(),
        logger=_Logger(),
        strict_foundry_mode=True,
        require_foundry_readiness=False,
        is_foundry_ready=_is_ready,
        set_foundry_ready=_set_ready,
        requires_foundry_runtime_resolution=_requires_runtime_resolution,
        foundry_capabilities=lambda: {"project_configured": True},
        ensure_agents_handler=_ensure_handler,
    )

    client = TestClient(app)
    assert client.get("/ready").status_code == 503
    ensure_response = client.post("/foundry/agents/ensure", json={"role": "fast"})
    assert ensure_response.status_code == 200
    assert client.get("/ready").status_code == 200


def test_invoke_auto_ensures_foundry_before_routing():
    app = FastAPI()
    foundry_ready = True
    runtime_definitions_missing = True
    ensure_calls = 0

    def _is_ready() -> bool:
        return foundry_ready

    def _set_ready(value: bool) -> None:
        nonlocal foundry_ready
        foundry_ready = value

    def _requires_runtime_resolution() -> bool:
        return runtime_definitions_missing

    async def _ensure_handler(_payload: dict | None) -> dict:
        nonlocal runtime_definitions_missing
        nonlocal ensure_calls
        ensure_calls += 1
        runtime_definitions_missing = False
        return {
            "service": "svc",
            "strict_foundry_mode": False,
            "foundry_ready": True,
            "results": {"fast": {"status": "exists", "agent_id": "a1"}},
        }

    register_standard_endpoints(
        app,
        service_name="svc",
        registry=_Registry(),
        router=_Router(),
        tracer=_Tracer(),
        logger=_Logger(),
        strict_foundry_mode=False,
        require_foundry_readiness=False,
        is_foundry_ready=_is_ready,
        set_foundry_ready=_set_ready,
        requires_foundry_runtime_resolution=_requires_runtime_resolution,
        foundry_capabilities=lambda: {"project_configured": True},
        ensure_agents_handler=_ensure_handler,
    )

    client = TestClient(app)
    response = client.post("/invoke", json={"query": "hello"})

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert ensure_calls == 1


def test_invoke_fails_closed_when_foundry_required_and_unresolved():
    app = FastAPI()
    foundry_ready = False
    runtime_definitions_missing = True
    ensure_calls = 0

    def _is_ready() -> bool:
        return foundry_ready

    def _set_ready(value: bool) -> None:
        nonlocal foundry_ready
        foundry_ready = value

    def _requires_runtime_resolution() -> bool:
        return runtime_definitions_missing

    async def _ensure_handler(_payload: dict | None) -> dict:
        nonlocal ensure_calls
        ensure_calls += 1
        return {
            "service": "svc",
            "strict_foundry_mode": False,
            "foundry_ready": False,
            "results": {"fast": {"status": "missing", "agent_id": None}},
        }

    register_standard_endpoints(
        app,
        service_name="svc",
        registry=_Registry(),
        router=_Router(),
        tracer=_Tracer(),
        logger=_Logger(),
        strict_foundry_mode=False,
        require_foundry_readiness=True,
        is_foundry_ready=_is_ready,
        set_foundry_ready=_set_ready,
        requires_foundry_runtime_resolution=_requires_runtime_resolution,
        foundry_capabilities=lambda: {
            "project_configured": True,
            "ready": foundry_ready,
            "configured_roles": ["fast"],
            "resolved_roles": [],
            "unresolved_roles": ["fast"],
            "runtime_resolution_required": runtime_definitions_missing,
            "last_error": {"status": "missing", "role": "fast"},
        },
        ensure_agents_handler=_ensure_handler,
    )

    client = TestClient(app)
    response = client.post("/invoke", json={"query": "hello"})

    assert response.status_code == 503
    assert ensure_calls == 1


def test_invoke_emits_degraded_outcome_telemetry():
    app = FastAPI()
    foundry_ready = True
    runtime_definitions_missing = False
    logger = _Logger()

    def _is_ready() -> bool:
        return foundry_ready

    def _set_ready(value: bool) -> None:
        nonlocal foundry_ready
        foundry_ready = value

    def _requires_runtime_resolution() -> bool:
        return runtime_definitions_missing

    async def _ensure_handler(_payload: dict | None) -> dict:
        return {
            "service": "svc",
            "strict_foundry_mode": False,
            "foundry_ready": True,
            "results": {},
        }

    register_standard_endpoints(
        app,
        service_name="svc",
        registry=_Registry(),
        router=_DegradedRouter(),
        tracer=_Tracer(),
        logger=logger,
        strict_foundry_mode=False,
        require_foundry_readiness=False,
        is_foundry_ready=_is_ready,
        set_foundry_ready=_set_ready,
        requires_foundry_runtime_resolution=_requires_runtime_resolution,
        foundry_capabilities=lambda: {"project_configured": True},
        ensure_agents_handler=_ensure_handler,
    )

    client = TestClient(app)
    response = client.post(
        "/invoke",
        json={
            "query": "winter jacket",
            "mode": "intelligent",
            "correlation_id": "corr-abc",
            "session_id": "session-123",
        },
    )

    assert response.status_code == 200

    outcome_record = next(
        record for record in logger.records if record["message"] == "service_invoke_outcome"
    )
    assert outcome_record["level"] == "warning"
    extra = outcome_record["extra"]
    assert extra["outcome_status"] == "degraded"
    assert extra["result_type"] == "degraded_fallback"
    assert extra["degraded"] is True
    assert extra["degraded_reason"] == "model_timeout"
    assert extra["requested_mode"] == "intelligent"
    assert extra["resolved_mode"] == "intelligent"
    assert extra["correlation_id"] == "corr-abc"
    assert extra["session_id"] == "session-123"


def test_invoke_emits_error_outcome_telemetry():
    app = FastAPI()
    foundry_ready = True
    runtime_definitions_missing = False
    logger = _Logger()

    def _is_ready() -> bool:
        return foundry_ready

    def _set_ready(value: bool) -> None:
        nonlocal foundry_ready
        foundry_ready = value

    def _requires_runtime_resolution() -> bool:
        return runtime_definitions_missing

    async def _ensure_handler(_payload: dict | None) -> dict:
        return {
            "service": "svc",
            "strict_foundry_mode": False,
            "foundry_ready": True,
            "results": {},
        }

    register_standard_endpoints(
        app,
        service_name="svc",
        registry=_Registry(),
        router=_FailingRouter(),
        tracer=_Tracer(),
        logger=logger,
        strict_foundry_mode=False,
        require_foundry_readiness=False,
        is_foundry_ready=_is_ready,
        set_foundry_ready=_set_ready,
        requires_foundry_runtime_resolution=_requires_runtime_resolution,
        foundry_capabilities=lambda: {"project_configured": True},
        ensure_agents_handler=_ensure_handler,
    )

    client = TestClient(app)
    response = client.post(
        "/invoke",
        json={
            "query": "winter jacket",
            "mode": "intelligent",
            "correlation_id": "corr-xyz",
            "session_id": "session-999",
        },
    )

    assert response.status_code == 503

    outcome_record = next(
        record for record in logger.records if record["message"] == "service_invoke_outcome"
    )
    assert outcome_record["level"] == "error"
    extra = outcome_record["extra"]
    assert extra["outcome_status"] == "error"
    assert extra["result_type"] == "error"
    assert extra["error_class"] == "HTTPException"
    assert extra["failure_reason"] == "invoke_error"
    assert extra["http_status_code"] == 503
    assert extra["correlation_id"] == "corr-xyz"
    assert extra["session_id"] == "session-999"


def test_self_healing_endpoints_capture_invoke_failures():
    app = FastAPI()
    foundry_ready = True
    runtime_definitions_missing = False
    kernel = SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=True,
        detect_only=True,
    )

    def _is_ready() -> bool:
        return foundry_ready

    def _set_ready(value: bool) -> None:
        nonlocal foundry_ready
        foundry_ready = value

    def _requires_runtime_resolution() -> bool:
        return runtime_definitions_missing

    async def _ensure_handler(_payload: dict | None) -> dict:
        return {
            "service": "svc",
            "strict_foundry_mode": False,
            "foundry_ready": True,
            "results": {},
        }

    register_standard_endpoints(
        app,
        service_name="svc",
        registry=_Registry(),
        router=_FailingRouter(),
        tracer=_Tracer(),
        logger=_Logger(),
        strict_foundry_mode=False,
        require_foundry_readiness=False,
        is_foundry_ready=_is_ready,
        set_foundry_ready=_set_ready,
        requires_foundry_runtime_resolution=_requires_runtime_resolution,
        foundry_capabilities=lambda: {"project_configured": True},
        ensure_agents_handler=_ensure_handler,
        self_healing_kernel=kernel,
    )

    client = TestClient(app)
    status_response = client.get("/self-healing/status")
    assert status_response.status_code == 200
    assert status_response.json()["enabled"] is True

    invoke_response = client.post("/invoke", json={"query": "fail"})
    assert invoke_response.status_code == 503

    incidents_response = client.get("/self-healing/incidents")
    assert incidents_response.status_code == 200
    incidents_payload = incidents_response.json()
    assert incidents_payload["count"] >= 1
    assert incidents_payload["incidents"][0]["surface"] == "api"

    reconcile_response = client.post("/self-healing/reconcile", json={})
    assert reconcile_response.status_code == 200
    assert "reconciled_incidents" in reconcile_response.json()
