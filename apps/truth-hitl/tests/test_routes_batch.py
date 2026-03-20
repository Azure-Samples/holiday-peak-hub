"""Unit tests for Truth HITL batch review routes."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from truth_hitl.adapters import EventHubPublisher, build_hitl_adapters
from truth_hitl.review_manager import ReviewItem
from truth_hitl.routes import build_review_router


class _StubPublisher(EventHubPublisher):
    def __init__(self) -> None:
        super().__init__(topic="export-jobs")
        self.published: list[dict[str, Any]] = []

    async def publish(self, payload: dict[str, Any]) -> None:
        self.published.append(payload)


def _make_item(*, entity_id: str, attr_id: str) -> ReviewItem:
    return ReviewItem(
        entity_id=entity_id,
        attr_id=attr_id,
        field_name="color",
        proposed_value="Midnight Blue",
        confidence=0.91,
        current_value="Blue",
        source="ai",
        proposed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        product_title="Winter Jacket",
        category_label="Apparel",
        original_data={"color": "Blue"},
        enriched_data={"color": "Midnight Blue"},
        reasoning="Matched product imagery and source data",
        source_assets=[{"asset_id": "dam-001"}],
        source_type="dam",
    )


def _build_client() -> tuple[TestClient, object, _StubPublisher]:
    publisher = _StubPublisher()
    adapters = build_hitl_adapters(export_publisher=publisher)
    app = FastAPI()
    app.include_router(build_review_router(adapters))
    return TestClient(app), adapters.review_manager, publisher


def test_batch_approve_multiple_entities():
    client, manager, publisher = _build_client()
    manager.enqueue(_make_item(entity_id="prod-001", attr_id="attr-001"))
    manager.enqueue(_make_item(entity_id="prod-002", attr_id="attr-002"))

    resp = client.post(
        "/review/approve/batch",
        json={
            "decisions": [
                {"entity_id": "prod-001", "reviewed_by": "staff-1"},
                {"entity_id": "prod-002", "reviewed_by": "staff-1"},
            ]
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["requested"] == 2
    assert data["processed"] == 2
    assert data["results"][0]["approved"] == 1
    assert data["results"][1]["approved"] == 1
    assert len(publisher.published) == 2
    assert publisher.published[0]["event_type"] == "hitl.approved"
    assert publisher.published[0]["data"]["approved_fields"] == ["color"]


def test_batch_reject_preserves_audit_context():
    client, manager, _ = _build_client()
    manager.enqueue(_make_item(entity_id="prod-001", attr_id="attr-001"))

    resp = client.post(
        "/review/reject/batch",
        json={
            "decisions": [
                {
                    "entity_id": "prod-001",
                    "attr_ids": ["attr-001"],
                    "reason": "insufficient confidence",
                    "reviewed_by": "staff-2",
                }
            ]
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["processed"] == 1
    assert data["results"][0]["rejected"] == 1

    log = manager.audit_log(entity_id="prod-001")
    assert len(log) == 1
    assert log[0].action == "rejected"
    assert log[0].original_data == {"color": "Blue"}
    assert log[0].enriched_data == {"color": "Midnight Blue"}
    assert log[0].reasoning == "Matched product imagery and source data"
    assert log[0].source_assets == [{"asset_id": "dam-001"}]
    assert log[0].source_type == "dam"


def test_batch_approve_skips_missing_entities_without_error():
    client, manager, publisher = _build_client()
    manager.enqueue(_make_item(entity_id="prod-001", attr_id="attr-001"))

    resp = client.post(
        "/review/approve/batch",
        json={
            "decisions": [
                {"entity_id": "prod-001", "reviewed_by": "staff-1"},
                {"entity_id": "missing-entity", "reviewed_by": "staff-1"},
            ]
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["requested"] == 2
    assert data["processed"] == 1
    assert len(data["results"]) == 1
    assert len(publisher.published) == 1


def test_single_approve_publishes_export_job_payload():
    client, manager, publisher = _build_client()
    manager.enqueue(_make_item(entity_id="prod-003", attr_id="attr-003"))

    resp = client.post(
        "/review/prod-003/approve",
        json={"reviewed_by": "reviewer-7"},
    )

    assert resp.status_code == 200
    assert len(publisher.published) == 1
    payload = publisher.published[0]
    assert payload["source"] == "truth-hitl"
    assert payload["data"]["entity_id"] == "prod-003"
    assert payload["data"]["approved_fields"] == ["color"]
    assert payload["data"]["reviewer_id"] == "reviewer-7"
