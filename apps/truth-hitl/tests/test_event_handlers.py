"""Unit tests for Truth HITL event handlers."""

from __future__ import annotations

import json

import pytest
import truth_hitl.event_handlers as event_handlers
from truth_hitl.adapters import build_hitl_adapters
from truth_hitl.review_manager import ReviewManager


class FakeEvent:
    """Minimal Event Hub event stub."""

    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def body_as_str(self) -> str:
        return json.dumps(self._payload)


@pytest.mark.asyncio
async def test_handle_hitl_job_enqueues_item():
    handlers = event_handlers.build_event_handlers()
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
    handlers = event_handlers.build_event_handlers()
    handler = handlers["hitl-jobs"]

    payload = {
        "event_type": "proposed_attribute",
        "data": {"attr_id": "attr-xyz"},
    }
    # Should not raise even when entity_id is missing
    await handler(None, FakeEvent(payload))


@pytest.mark.asyncio
async def test_handle_hitl_job_skips_missing_attr_id():
    handlers = event_handlers.build_event_handlers()
    handler = handlers["hitl-jobs"]

    payload = {
        "event_type": "proposed_attribute",
        "data": {"entity_id": "prod-001"},
    }
    await handler(None, FakeEvent(payload))


def test_build_event_handlers_includes_hitl_jobs():
    handlers = event_handlers.build_event_handlers()
    assert "hitl-jobs" in handlers


@pytest.mark.asyncio
async def test_build_event_handlers_uses_provided_adapters():
    review_manager = ReviewManager()
    adapters = build_hitl_adapters(review_manager=review_manager)

    handlers = event_handlers.build_event_handlers(adapters=adapters)
    handler = handlers["hitl-jobs"]

    payload = {
        "event_type": "proposed_attribute",
        "data": {
            "entity_id": "prod-777",
            "attr_id": "attr-777",
            "field_name": "color",
            "proposed_value": "Black",
            "confidence": 0.77,
        },
    }

    await handler(None, FakeEvent(payload))

    queued = review_manager.get_by_entity("prod-777")
    assert len(queued) == 1
    assert queued[0].attr_id == "attr-777"


@pytest.mark.asyncio
async def test_handle_hitl_job_accepts_enhanced_ui_payload_shapes(monkeypatch):
    review_manager = ReviewManager()

    def _stub_build_hitl_adapters():
        return build_hitl_adapters(review_manager=review_manager)

    monkeypatch.setattr(event_handlers, "build_hitl_adapters", _stub_build_hitl_adapters)

    handlers = event_handlers.build_event_handlers()
    handler = handlers["hitl-jobs"]

    payload = {
        "event_type": "proposed_attribute",
        "data": {
            "entity_id": "prod-100",
            "attr_id": "attr-200",
            "field_name": "material",
            "proposed_value": "Organic Cotton",
            "confidence": 0.92,
            "source": "ai",
            "product_title": "Heritage Shirt",
            "category_label": "Apparel",
            "reasoning": [
                "Image texture suggests cotton",
                "Catalog title includes 'cotton'",
            ],
            "source_assets": [
                "https://cdn.example.com/products/prod-100/front.jpg",
                {
                    "url": "https://cdn.example.com/products/prod-100/zoom.jpg",
                    "asset_id": "dam-200",
                    "kind": "image",
                },
            ],
            "source_type": "hybrid",
        },
    }

    await handler(None, FakeEvent(payload))

    queued = review_manager.get_by_entity("prod-100")
    assert len(queued) == 1
    assert queued[0].reasoning == [
        "Image texture suggests cotton",
        "Catalog title includes 'cotton'",
    ]
    assert queued[0].source_assets == [
        "https://cdn.example.com/products/prod-100/front.jpg",
        {
            "url": "https://cdn.example.com/products/prod-100/zoom.jpg",
            "asset_id": "dam-200",
            "kind": "image",
        },
    ]
