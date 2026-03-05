"""Unit tests for Truth HITL event handlers."""

from __future__ import annotations

import json

import pytest
from truth_hitl.event_handlers import build_event_handlers


class FakeEvent:
    """Minimal Event Hub event stub."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def body_as_str(self) -> str:
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_handle_hitl_job_enqueues_item():
    handlers = build_event_handlers()
    handler = handlers["hitl-jobs"]

    payload = {
        "event_type": "proposed_attribute",
        "data": {
            "entity_id": "prod-999",
            "attr_id": "attr-xyz",
            "field_name": "description",
            "proposed_value": "A warm winter coat",
            "confidence": 0.88,
            "current_value": None,
            "source": "ai",
            "proposed_at": "2026-01-15T10:00:00+00:00",
            "product_title": "Winter Coat",
            "category_label": "Outerwear",
        },
    }
    await handler(None, FakeEvent(payload))
    # Handler should complete without raising


@pytest.mark.asyncio
async def test_handle_hitl_job_skips_missing_entity_id():
    handlers = build_event_handlers()
    handler = handlers["hitl-jobs"]

    payload = {
        "event_type": "proposed_attribute",
        "data": {"attr_id": "attr-xyz"},
    }
    # Should not raise even when entity_id is missing
    await handler(None, FakeEvent(payload))


@pytest.mark.asyncio
async def test_handle_hitl_job_skips_missing_attr_id():
    handlers = build_event_handlers()
    handler = handlers["hitl-jobs"]

    payload = {
        "event_type": "proposed_attribute",
        "data": {"entity_id": "prod-001"},
    }
    await handler(None, FakeEvent(payload))


def test_build_event_handlers_includes_hitl_jobs():
    handlers = build_event_handlers()
    assert "hitl-jobs" in handlers
