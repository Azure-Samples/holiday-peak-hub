import pytest
from fastapi.testclient import TestClient
from inventory_health_check.main import app

pytestmark = pytest.mark.usefixtures("mock_foundry_readiness")


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "inventory-health-check"


def test_invoke_requires_sku():
    client = TestClient(app)
    response = client.post("/invoke", json={})
    assert response.status_code == 200
    assert response.json().get("error") == "sku is required"


def test_responses_adapter_mounts_on_same_fastapi_app_when_sdk_present():
    pytest.importorskip("agent_framework_foundry_hosting")

    direct_paths = {getattr(route, "path", "") for route in app.routes}
    assert "/health" in direct_paths
    assert "/ready" in direct_paths
    assert "/invoke" in direct_paths
    assert any(path.startswith("/mcp") for path in direct_paths)

    mounted_apps = [route for route in app.routes if getattr(route, "path", "") == ""]
    assert mounted_apps, "Responses adapter should mount into the existing FastAPI app"

    host_server = mounted_apps[-1].app
    response_paths = {
        getattr(route, "path", None) or getattr(route, "path_format", None)
        for route in host_server.routes
    }
    response_paths.discard(None)
    assert "/responses" in response_paths
