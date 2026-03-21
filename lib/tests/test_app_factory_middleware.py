"""Tests for app_factory_components.middleware."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from holiday_peak_lib.app_factory_components.middleware import register_correlation_middleware


def test_register_correlation_middleware_propagates_header():
    app = FastAPI()
    register_correlation_middleware(app)

    @app.get("/ping")
    async def ping() -> dict[str, str]:
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/ping", headers={"X-Correlation-ID": "cid-123"})

    assert response.status_code == 200
    assert response.headers.get("x-correlation-id") == "cid-123"
