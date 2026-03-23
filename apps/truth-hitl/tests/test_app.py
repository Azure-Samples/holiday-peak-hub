"""Unit tests for the Truth HITL service app."""

from fastapi.testclient import TestClient
from truth_hitl.main import app


def test_health():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "truth-hitl"


def test_review_queue_empty():
    client = TestClient(app)
    resp = client.get("/review/queue")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["items"] == []


def test_review_stats_empty():
    client = TestClient(app)
    resp = client.get("/review/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "pending_review" in data


def test_get_entity_proposals_empty():
    client = TestClient(app)
    resp = client.get("/review/unknown-entity")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []


def test_approve_missing_entity_returns_404():
    client = TestClient(app)
    resp = client.post("/review/no-such-entity/approve", json={})
    assert resp.status_code == 404


def test_reject_missing_entity_returns_404():
    client = TestClient(app)
    resp = client.post("/review/no-such-entity/reject", json={"reason": "bad data"})
    assert resp.status_code == 404


def test_edit_missing_entity_returns_404():
    client = TestClient(app)
    resp = client.post(
        "/review/no-such-entity/edit",
        json={"edited_value": "New Value"},
    )
    assert resp.status_code == 404


def test_invoke_queue_action_returns_items_shape():
    client = TestClient(app)
    invoke_response = client.post(
        "/invoke",
        json={
            "action": "queue",
            "limit": 10,
        },
    )
    assert invoke_response.status_code == 200
    payload = invoke_response.json()
    assert "items" in payload
    assert "count" in payload
