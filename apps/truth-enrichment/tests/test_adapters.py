"""Unit tests for truth enrichment adapters."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from holiday_peak_lib.utils import (
    PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
    PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV,
)
from truth_enrichment.adapters import (
    DAMImageAnalysisAdapter,
    EventHubPublisher,
    build_enrichment_adapters,
)


@pytest.mark.asyncio
async def test_dam_image_analysis_success() -> None:
    dam_connector = AsyncMock()
    dam_connector.get_assets_by_product.return_value = [
        {"url": "https://cdn.example.com/a.jpg"},
        {"url": "https://cdn.example.com/b.jpg"},
    ]

    async def fake_vision_invoker(*, request, messages):  # noqa: ANN001
        assert request["entity_id"] == "sku-1"
        assert request["field_name"] == "color"
        assert len(messages) == 2
        content = messages[1]["content"]
        assert isinstance(content, list)
        assert content[0]["type"] == "text"
        assert content[1]["type"] == "image_url"
        assert content[2]["type"] == "image_url"
        return {
            "value": "red",
            "confidence": 0.92,
            "evidence": "dominant color appears red",
            "metadata": {"model": "vision-rich"},
        }

    adapter = DAMImageAnalysisAdapter(
        dam_connector=dam_connector,
        vision_invoker=fake_vision_invoker,
    )

    result = await adapter.analyze_attribute_from_images(
        entity_id="sku-1",
        field_name="color",
        product={"name": "Runner Shoe"},
    )

    assert result["value"] == "red"
    assert result["confidence"] == pytest.approx(0.92)
    assert result["metadata"]["source"] == "image_analysis"
    assert result["metadata"]["assets_count"] == 2


@pytest.mark.asyncio
async def test_dam_image_analysis_graceful_when_assets_missing() -> None:
    dam_connector = AsyncMock()
    dam_connector.get_assets_by_product.return_value = []

    adapter = DAMImageAnalysisAdapter(
        dam_connector=dam_connector,
        vision_invoker=AsyncMock(),
    )

    result = await adapter.analyze_attribute_from_images(
        entity_id="sku-2",
        field_name="material",
        product={"name": "Bag"},
    )

    assert result["value"] is None
    assert result["confidence"] == pytest.approx(0.0)
    assert result["metadata"]["fallback_reason"] == "no_assets"


@pytest.mark.asyncio
async def test_dam_image_analysis_graceful_when_vision_unavailable() -> None:
    dam_connector = AsyncMock()
    dam_connector.get_assets_by_product.return_value = [{"url": "https://cdn.example.com/a.jpg"}]

    async def failing_vision_invoker(*, request, messages):  # noqa: ANN001
        raise RuntimeError("foundry unavailable")

    adapter = DAMImageAnalysisAdapter(
        dam_connector=dam_connector,
        vision_invoker=failing_vision_invoker,
    )

    result = await adapter.analyze_attribute_from_images(
        entity_id="sku-3",
        field_name="pattern",
        product={"name": "Scarf"},
    )

    assert result["value"] is None
    assert result["confidence"] == pytest.approx(0.0)
    assert result["metadata"]["fallback_reason"] == "adapter_failure"


def test_build_enrichment_adapters_includes_image_analysis() -> None:
    adapters = build_enrichment_adapters()
    assert isinstance(adapters.dam, DAMImageAnalysisAdapter)
    assert isinstance(adapters.image_analysis, DAMImageAnalysisAdapter)
    assert adapters.image_analysis.resilience_status()["threshold"] == 5


@pytest.mark.asyncio
async def test_event_hub_publisher_delegates_to_truth_publisher() -> None:
    truth_publisher = AsyncMock()
    truth_publisher.publish_payload = AsyncMock()
    publisher = EventHubPublisher(topic="hitl-jobs", publisher=truth_publisher)
    payload = {"event_type": "attribute.proposed", "data": {"entity_id": "sku-9"}}

    await publisher.publish(payload)

    truth_publisher.publish_payload.assert_awaited_once_with(
        "hitl-jobs",
        payload,
        metadata={"domain": "truth-enrichment", "entity_id": "sku-9"},
        remediation_context={
            "preferred_action": "reset_messaging_publisher_bindings",
            "workflow": "hitl_review_dispatch",
            "target_topic": "hitl-jobs",
        },
    )


def test_event_hub_publisher_uses_platform_jobs_binding_envs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("EVENT_HUB_NAMESPACE", "retail-namespace")
    monkeypatch.setenv("EVENT_HUB_CONNECTION_STRING", "retail-connection")
    monkeypatch.setenv(PLATFORM_JOBS_EVENT_HUB_NAMESPACE_ENV, "platform-namespace")
    monkeypatch.setenv(
        PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING_ENV,
        "platform-connection",
    )

    publisher = EventHubPublisher()

    assert publisher._publisher._namespace == "platform-namespace"  # pylint: disable=protected-access
    assert publisher._publisher._connection_string == "platform-connection"  # pylint: disable=protected-access
