"""Tests for app_factory_components.endpoints."""

from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from holiday_peak_lib.app_factory_components.endpoints import register_standard_endpoints
from holiday_peak_lib.mcp.server import FastAPIMCPServer
from holiday_peak_lib.self_healing import SelfHealingKernel, default_surface_manifest
from pydantic import BaseModel


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


class _ToolInput(BaseModel):
    query: str


class _ToolOutput(BaseModel):
    ok: bool


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


def _register_app(
    *,
    router: Any | None = None,
    logger: _Logger | None = None,
    strict_foundry_mode: bool = False,
    require_foundry_readiness: bool = False,
    readiness: dict[str, Any] | None = None,
    kernel: SelfHealingKernel | None = None,
    prompt_catalog_provider: Any | None = None,
    mcp_tool_descriptions_provider: Any | None = None,
) -> tuple[FastAPI, _Logger]:
    app = FastAPI()
    records = logger or _Logger()
    payload = readiness or {
        "project_configured": True,
        "endpoint_configured": True,
        "ready": True,
        "runtime_resolution_required": False,
        "configured_roles": ["fast"],
        "bound_roles": ["fast"],
        "unbound_roles": [],
    }

    register_standard_endpoints(
        app,
        service_name="svc",
        registry=_Registry(),
        router=router or _Router(),
        tracer=_Tracer(),
        logger=records,
        strict_foundry_mode=strict_foundry_mode,
        require_foundry_readiness=require_foundry_readiness,
        is_foundry_ready=lambda: bool(payload.get("ready")),
        requires_foundry_runtime_resolution=lambda: bool(
            payload.get("runtime_resolution_required")
        ),
        foundry_capabilities=lambda: dict(payload),
        self_healing_kernel=kernel,
        prompt_catalog_provider=prompt_catalog_provider,
        mcp_tool_descriptions_provider=mcp_tool_descriptions_provider,
    )
    return app, records


def test_register_standard_endpoints_ready_reports_direct_model_status():
    app, _logger = _register_app(
        require_foundry_readiness=True,
        readiness={
            "project_configured": True,
            "endpoint_configured": True,
            "ready": True,
            "runtime_resolution_required": False,
            "configured_roles": ["fast", "rich"],
            "bound_roles": ["fast", "rich"],
            "unbound_roles": [],
        },
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 200
    payload = response.json()
    assert payload["foundry_ready"] is True
    assert payload["foundry_required"] is True
    assert payload["foundry"]["bound_roles"] == ["fast", "rich"]


def test_ready_fails_with_direct_model_language_when_required_and_unbound():
    app, _logger = _register_app(
        require_foundry_readiness=True,
        readiness={
            "project_configured": True,
            "endpoint_configured": True,
            "ready": False,
            "runtime_resolution_required": True,
            "configured_roles": ["fast"],
            "bound_roles": [],
            "unbound_roles": ["fast"],
        },
    )

    response = TestClient(app).get("/ready")

    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["status"] == "not_ready"
    assert "Direct-model targets are not ready" in detail["reason"]
    assert detail["foundry"]["unbound_roles"] == ["fast"]


def test_invoke_does_not_block_on_unbound_targets_when_not_enforced():
    app, _logger = _register_app(
        readiness={
            "project_configured": True,
            "endpoint_configured": True,
            "ready": False,
            "runtime_resolution_required": True,
            "configured_roles": ["fast"],
            "bound_roles": [],
            "unbound_roles": ["fast"],
        },
    )

    response = TestClient(app).post("/invoke", json={"query": "hello"})

    assert response.status_code == 200
    assert response.json()["ok"] is True


def test_invoke_fails_closed_when_direct_model_required_and_unbound():
    app, _logger = _register_app(
        require_foundry_readiness=True,
        readiness={
            "project_configured": True,
            "endpoint_configured": True,
            "ready": False,
            "runtime_resolution_required": True,
            "configured_roles": ["fast"],
            "bound_roles": [],
            "unbound_roles": ["fast"],
        },
    )

    response = TestClient(app).post("/invoke", json={"query": "hello"})

    assert response.status_code == 503
    assert "Direct-model targets are not ready" in response.json()["detail"]


def test_retired_route_is_absent():
    app, _logger = _register_app()
    route_paths = {route.path for route in app.routes}
    retired_route = "/foundry/agents/" + "ensure"

    assert retired_route not in route_paths
    assert TestClient(app).post(retired_route, json={}).status_code == 404


def test_invoke_emits_degraded_outcome_telemetry():
    logger = _Logger()
    app, _logger = _register_app(router=_DegradedRouter(), logger=logger)

    response = TestClient(app).post(
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
    logger = _Logger()
    app, _logger = _register_app(router=_FailingRouter(), logger=logger)

    response = TestClient(app).post(
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
    kernel = SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=True,
        detect_only=True,
    )
    app, _logger = _register_app(router=_FailingRouter(), kernel=kernel)
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


def test_prompt_and_mcp_introspection_endpoints_return_registered_metadata():
    app = FastAPI(title="svc")
    mcp = FastAPIMCPServer(app)

    def _tool_handler(payload: dict[str, Any]) -> dict[str, Any]:
        return {"ok": bool(payload.get("query"))}

    mcp.add_tool(
        "/inventory_lookup",
        _tool_handler,
        input_model=_ToolInput,
        output_model=_ToolOutput,
        metadata={"description": "Look up live inventory evidence."},
    )
    prompt_catalog = [
        {
            "name": "instructions.md",
            "content": "# Instructions\nKeep it grounded.",
            "sha": "sha-123",
            "last_modified": "2026-04-05T12:00:00+00:00",
        }
    ]

    register_standard_endpoints(
        app,
        service_name="svc",
        registry=_Registry(),
        router=_Router(),
        tracer=_Tracer(),
        logger=_Logger(),
        strict_foundry_mode=False,
        require_foundry_readiness=False,
        is_foundry_ready=lambda: True,
        requires_foundry_runtime_resolution=lambda: False,
        foundry_capabilities=lambda: {"project_configured": True, "ready": True},
        prompt_catalog_provider=lambda: prompt_catalog,
        mcp_tool_descriptions_provider=lambda: [
            {
                "name": details.get("name"),
                "path": path,
                "description": details.get("metadata", {}).get("description"),
                "input_schema": details.get("input_schema"),
                "output_schema": details.get("output_schema"),
            }
            for path, details in mcp.tool_metadata.items()
        ],
    )

    client = TestClient(app)
    assert client.get("/agent/prompts").json()["prompts"] == prompt_catalog
    assert client.get("/mcp/tool_descriptions").json()["tools"] == [
        {
            "name": "inventory_lookup",
            "path": "/inventory_lookup",
            "description": "Look up live inventory evidence.",
            "input_schema": _ToolInput.model_json_schema(),
            "output_schema": _ToolOutput.model_json_schema(),
        }
    ]
