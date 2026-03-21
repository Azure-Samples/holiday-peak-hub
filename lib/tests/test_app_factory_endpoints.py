"""Tests for app_factory_components.endpoints."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from holiday_peak_lib.app_factory_components.endpoints import register_standard_endpoints


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


class _Tracer:
    def get_traces(self, limit: int = 50) -> list[dict]:
        return [{"limit": limit}]

    def get_metrics(self) -> dict[str, int]:
        return {"count": 1}

    def get_latest_evaluation(self) -> dict[str, str]:
        return {"status": "pass"}


class _Logger:
    pass


def test_register_standard_endpoints_ready_and_ensure_flow():
    app = FastAPI()
    foundry_ready = False

    def _is_ready() -> bool:
        return foundry_ready

    def _set_ready(value: bool) -> None:
        nonlocal foundry_ready
        foundry_ready = value

    async def _ensure_handler(_payload: dict | None) -> dict:
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
        is_foundry_ready=_is_ready,
        set_foundry_ready=_set_ready,
        ensure_agents_handler=_ensure_handler,
    )

    client = TestClient(app)
    assert client.get("/ready").status_code == 503
    ensure_response = client.post("/foundry/agents/ensure", json={"role": "fast"})
    assert ensure_response.status_code == 200
    assert client.get("/ready").status_code == 200
