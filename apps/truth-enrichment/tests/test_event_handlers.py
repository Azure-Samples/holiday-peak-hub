"""Unit tests for Truth Enrichment event handlers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from truth_enrichment.adapters import EnrichmentAdapters
from truth_enrichment.event_handlers import build_event_handlers


def test_build_event_handlers_includes_enrichment_jobs() -> None:
    handlers = build_event_handlers()
    assert "enrichment-jobs" in handlers


@pytest.mark.asyncio
async def test_enrichment_job_handler_runs_pipeline_for_sku_payload() -> None:
    products = AsyncMock()
    products.get_product = AsyncMock(
        return_value={"id": "sku-44", "name": "Commuter Bag", "category": "bags", "material": ""}
    )
    products.get_schema = AsyncMock(
        return_value={
            "required_attributes": ["material"],
            "optional_attributes": ["pattern"],
            "fields": {
                "material": {"type": "string", "required": True},
                "pattern": {"type": "string", "required": False},
            },
        }
    )

    dam = Mock()
    dam.set_vision_invoker = Mock()
    dam.set_vision_prompt_builder = Mock()
    dam.analyze_attribute_from_images = AsyncMock(
        return_value={
            "value": "canvas",
            "confidence": 0.84,
            "evidence": "bag texture appears canvas",
            "metadata": {"assets": ["https://cdn.example.com/bag.jpg"]},
        }
    )

    proposed = AsyncMock()
    proposed.upsert = AsyncMock(side_effect=lambda payload: payload)

    truth = AsyncMock()
    truth.upsert = AsyncMock()

    audit = AsyncMock()
    audit.append = AsyncMock()

    hitl = AsyncMock()
    hitl.publish = AsyncMock()

    adapters = EnrichmentAdapters(
        products=products,
        proposed=proposed,
        truth=truth,
        audit=audit,
        dam=dam,
        hitl_publisher=hitl,
    )

    fake_event = Mock()
    fake_event.body_as_str.return_value = json.dumps({"data": {"sku": "sku-44"}})

    with patch("truth_enrichment.event_handlers.build_enrichment_adapters", return_value=adapters):
        handlers = build_event_handlers()
        await handlers["enrichment-jobs"](None, fake_event)

    assert proposed.upsert.await_count == 2
    first_payload = proposed.upsert.await_args_list[0].args[0]
    assert first_payload["entity_id"] == "sku-44"
