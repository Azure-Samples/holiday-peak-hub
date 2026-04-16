"""Unit tests for TruthEnrichmentAgent orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest
from holiday_peak_lib.agents.base_agent import AgentDependencies, ModelTarget
from truth_enrichment.adapters import EnrichmentAdapters
from truth_enrichment.agents import TruthEnrichmentAgent, _detect_gaps


@pytest.fixture()
def agent_config_with_slm() -> AgentDependencies:
    """Create agent dependencies with an enabled fast-model route."""

    async def dummy_invoker(*, messages, tools=None, **kwargs):  # noqa: ANN001
        return {"value": "dummy", "confidence": 0.0, "evidence": "dummy"}

    slm = ModelTarget(name="slm", model="fast-model", invoker=dummy_invoker)
    setattr(slm, "deployment_name", "fast-model")
    return AgentDependencies(
        service_name="truth-enrichment-test",
        router=None,
        tools={},
        slm=slm,
        llm=None,
    )


@pytest.fixture()
def agent_config_without_models() -> AgentDependencies:
    """Create agent dependencies without available model backends."""
    return AgentDependencies(
        service_name="truth-enrichment-test",
        router=None,
        tools={},
        slm=None,
        llm=None,
    )


def _build_mock_adapters(image_response: dict[str, object]) -> EnrichmentAdapters:
    image_adapter = Mock()
    image_adapter.set_vision_invoker = Mock()
    image_adapter.set_vision_prompt_builder = Mock()
    image_adapter.analyze_attribute_from_images = AsyncMock(return_value=image_response)

    proposed = AsyncMock()
    proposed.upsert = AsyncMock(side_effect=lambda payload: payload)

    truth = AsyncMock()
    truth.upsert = AsyncMock()

    audit = AsyncMock()
    audit.append = AsyncMock()

    hitl = AsyncMock()
    hitl.publish = AsyncMock()

    products = AsyncMock()

    return EnrichmentAdapters(
        products=products,
        proposed=proposed,
        truth=truth,
        audit=audit,
        image_analysis=image_adapter,
        hitl_publisher=hitl,
    )


@pytest.mark.asyncio
async def test_enrich_field_runs_image_before_text_and_marks_hybrid(
    agent_config_with_slm: AgentDependencies,
) -> None:
    """DAM image analysis runs before text enrichment and yields hybrid source type."""
    sequence: list[str] = []

    adapters = _build_mock_adapters(
        {
            "value": "black",
            "confidence": 0.91,
            "evidence": "dominant color from product images",
            "metadata": {
                "source": "image_analysis",
                "assets": ["https://cdn.example.com/a.jpg"],
            },
        }
    )

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=adapters):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)

        async def fake_image(*, entity_id, field_name, product, field_definition):  # noqa: ANN001
            sequence.append("image")
            return {
                "value": "black",
                "confidence": 0.91,
                "evidence": "dominant color from product images",
                "metadata": {
                    "source": "image_analysis",
                    "assets": ["https://cdn.example.com/a.jpg"],
                },
            }

        async def fake_model(*, request, messages):  # noqa: ANN001
            sequence.append("text")
            return {
                "value": "jet black",
                "confidence": 0.84,
                "evidence": "text mentions jet-black finish",
                "metadata": {"source": "text_enrichment"},
            }

        agent.adapters.image_analysis.analyze_attribute_from_images = AsyncMock(
            side_effect=fake_image
        )
        agent.invoke_model = AsyncMock(side_effect=fake_model)

        proposed = await agent.enrich_field(
            entity_id="sku-1",
            field_name="color",
            product={"name": "Trail Jacket", "color": None},
            field_definition={"type": "string", "required": True},
        )

    assert sequence == ["image", "text"]
    assert proposed["source_type"] == "hybrid"
    assert proposed["source_assets"] == ["https://cdn.example.com/a.jpg"]
    assert proposed["original_data"] == {"color": None}
    assert proposed["enriched_data"]["color"] in {"black", "jet black"}
    assert isinstance(proposed["reasoning"], str) and proposed["reasoning"]
    adapters.truth.upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_enrich_field_gracefully_falls_back_to_text_when_dam_unavailable(
    agent_config_with_slm: AgentDependencies,
) -> None:
    """Text enrichment still works when DAM image analysis returns no usable signal."""
    adapters = _build_mock_adapters(
        {
            "value": None,
            "confidence": 0.0,
            "evidence": "image analysis unavailable for material",
            "metadata": {"source": "image_analysis", "fallback_reason": "no_assets"},
        }
    )

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=adapters):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value={
                "value": "canvas",
                "confidence": 0.79,
                "evidence": "title and description indicate canvas",
                "metadata": {"source": "text_enrichment"},
            }
        )

        proposed = await agent.enrich_field(
            entity_id="sku-2",
            field_name="material",
            product={"name": "Urban Bag", "material": None},
        )

    assert proposed["source_type"] == "text_enrichment"
    assert proposed["proposed_value"] == "canvas"
    assert proposed["source_assets"] == []
    adapters.truth.upsert.assert_not_awaited()


@pytest.mark.asyncio
async def test_enrich_field_uses_image_when_models_unavailable(
    agent_config_without_models: AgentDependencies,
) -> None:
    """Existing behavior remains valid when Foundry/model path is unavailable."""
    adapters = _build_mock_adapters(
        {
            "value": None,
            "confidence": 0.0,
            "evidence": "image analysis unavailable for pattern",
            "metadata": {"source": "image_analysis", "fallback_reason": "adapter_failure"},
        }
    )

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=adapters):
        agent = TruthEnrichmentAgent(config=agent_config_without_models)
        proposed = await agent.enrich_field(
            entity_id="sku-3",
            field_name="pattern",
            product={"name": "Scarf", "pattern": None},
        )

    assert proposed["source_type"] == "image_analysis"
    assert proposed["proposed_value"] is None
    assert proposed["status"] == "pending_review"
    adapters.truth.upsert.assert_not_awaited()
    adapters.hitl_publisher.publish.assert_awaited_once()
    payload = adapters.hitl_publisher.publish.await_args.args[0]
    assert payload["event_type"] == "attribute.proposed"
    assert payload["data"]["entity_id"] == "sku-3"
    assert payload["data"]["attr_id"] == proposed["id"]
    assert payload["data"]["field_name"] == "pattern"


def test_detect_gaps_uses_full_schema_fields_list() -> None:
    """Gap detection supports required and optional fields from a full schema payload."""
    product = {"name": "Trail Jacket", "material": "nylon", "color": ""}
    schema = {
        "category_id": "outerwear",
        "fields": [
            {"name": "material", "type": "string", "required": True},
            {"name": "color", "type": "string", "required": True},
            {"name": "fit", "type": "string", "required": False},
        ],
    }

    gaps = _detect_gaps(product, schema)

    assert gaps == ["color", "fit"]


@pytest.mark.asyncio
async def test_handle_orchestrates_dam_plus_text_for_missing_fields(
    agent_config_with_slm: AgentDependencies,
) -> None:
    """Handle() fetches product/schema and produces proposals for full-schema gaps."""
    adapters = _build_mock_adapters(
        {
            "value": "slim",
            "confidence": 0.88,
            "evidence": "fit inferred from product imagery",
            "metadata": {
                "source": "image_analysis",
                "assets": ["https://cdn.example.com/fit.jpg"],
            },
        }
    )
    adapters.products.get_product = AsyncMock(
        return_value={"id": "sku-10", "name": "Trail Jacket", "category": "outerwear", "color": ""}
    )
    adapters.products.get_schema = AsyncMock(
        return_value={
            "category_id": "outerwear",
            "required_attributes": ["color"],
            "optional_attributes": ["fit"],
            "fields": {
                "color": {"type": "string", "required": True},
                "fit": {"type": "string", "required": False},
            },
        }
    )

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=adapters):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value={
                "value": "black",
                "confidence": 0.76,
                "evidence": "description includes black shell",
                "metadata": {"source": "text_enrichment"},
            }
        )

        response = await agent.handle({"entity_id": "sku-10"})

    assert response["entity_id"] == "sku-10"
    assert len(response["proposed"]) == 2
    proposed_fields = {item["field_name"] for item in response["proposed"]}
    assert proposed_fields == {"color", "fit"}


@pytest.mark.asyncio
async def test_handle_publishes_to_search_enrichment_bridge(
    agent_config_with_slm: AgentDependencies,
) -> None:
    """Handle() publishes to search-enrichment-jobs after enrichment completes."""
    adapters = _build_mock_adapters(
        {
            "value": "red",
            "confidence": 0.85,
            "evidence": "color visible in product imagery",
            "metadata": {
                "source": "image_analysis",
                "assets": ["https://cdn.example.com/c.jpg"],
            },
        }
    )
    adapters.products.get_product = AsyncMock(
        return_value={
            "id": "sku-20",
            "name": "Cozy Blanket",
            "category": "home_furniture",
            "color": "",
        }
    )
    adapters.products.get_schema = AsyncMock(
        return_value={
            "category_id": "home_furniture",
            "fields": {"color": {"type": "string", "required": True}},
        }
    )

    search_pub = AsyncMock()
    search_pub.publish = AsyncMock()
    adapters.search_enrichment_publisher = search_pub

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=adapters):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value={
                "value": "red",
                "confidence": 0.80,
                "evidence": "description says warm red",
                "metadata": {"source": "text_enrichment"},
            }
        )

        response = await agent.handle({"entity_id": "sku-20"})

    assert response["entity_id"] == "sku-20"
    assert len(response["proposed"]) == 1

    search_pub.publish.assert_awaited_once()
    payload = search_pub.publish.await_args.args[0]
    assert payload["event_type"] == "enrichment.completed"
    assert payload["data"]["entity_id"] == "sku-20"
    assert payload["data"]["proposed_count"] == 1
    assert payload["data"]["source"] == "truth-enrichment"


@pytest.mark.asyncio
async def test_handle_skips_search_enrichment_when_publisher_is_none(
    agent_config_with_slm: AgentDependencies,
) -> None:
    """Handle() gracefully skips bridge when search_enrichment_publisher is None."""
    adapters = _build_mock_adapters(
        {
            "value": "oak",
            "confidence": 0.90,
            "evidence": "material visible",
            "metadata": {"source": "image_analysis", "assets": []},
        }
    )
    adapters.products.get_product = AsyncMock(
        return_value={
            "id": "sku-21",
            "name": "Desk",
            "category": "home_furniture",
            "material": "",
        }
    )
    adapters.products.get_schema = AsyncMock(
        return_value={
            "category_id": "home_furniture",
            "fields": {"material": {"type": "string", "required": True}},
        }
    )
    # Explicitly None (default from _build_mock_adapters)
    adapters.search_enrichment_publisher = None

    with patch("truth_enrichment.agents.build_enrichment_adapters", return_value=adapters):
        agent = TruthEnrichmentAgent(config=agent_config_with_slm)
        agent.invoke_model = AsyncMock(
            return_value={
                "value": "oak",
                "confidence": 0.88,
                "evidence": "oak material",
                "metadata": {"source": "text_enrichment"},
            }
        )

        response = await agent.handle({"entity_id": "sku-21"})

    assert response["entity_id"] == "sku-21"
    assert len(response["proposed"]) == 1
