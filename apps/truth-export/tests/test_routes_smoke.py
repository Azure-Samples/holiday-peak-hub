"""Lightweight smoke tests for truth-export routes."""

from __future__ import annotations

from fastapi.testclient import TestClient

from truth_export.main import app


def test_export_routes_smoke() -> None:
    client = TestClient(app)

    health = client.get("/health")
    protocols = client.get("/export/protocols")

    assert health.status_code == 200
    assert protocols.status_code == 200
    assert "ucp" in protocols.json()["protocols"]
