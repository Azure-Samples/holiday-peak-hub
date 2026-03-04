"""Integration tests for the completeness-jobs event consumer."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from product_management_consistency_validation.completeness_engine import (
    CategorySchema,
    FieldDefinition,
)
from product_management_consistency_validation.event_consumer import (
    build_completeness_event_handlers,
)


def _make_event(payload: dict) -> MagicMock:
    event = MagicMock()
    event.body_as_str.return_value = json.dumps(payload)
    return event


def _make_product(sku: str = "SKU-1", category: str = "apparel"):
    from holiday_peak_lib.schemas.product import CatalogProduct

    return CatalogProduct(
        sku=sku,
        name="Test Product",
        category=category,
        price=29.99,
        currency="USD",
        image_url="https://example.com/image.jpg",
    )


def _make_schema(category_id: str = "apparel") -> CategorySchema:
    return CategorySchema(
        category_id=category_id,
        schema_version="1.0",
        fields=[
            FieldDefinition(
                field_name="name",
                field_path="name",
                expected_type="str",
                weight=2.0,
            ),
            FieldDefinition(
                field_name="price",
                field_path="price",
                expected_type="float",
                weight=1.0,
            ),
            FieldDefinition(
                field_name="description",
                field_path="description",
                expected_type="str",
                weight=1.0,
                enrichable=True,
            ),
        ],
    )


@pytest.mark.asyncio
async def test_handler_key_is_completeness_jobs():
    handlers = build_completeness_event_handlers()
    assert "completeness-jobs" in handlers


@pytest.mark.asyncio
async def test_skips_event_without_entity_id():
    handlers = build_completeness_event_handlers()
    handler = handlers["completeness-jobs"]

    event = _make_event({"event_type": "completeness_requested", "data": {}})
    # Should not raise
    await handler(MagicMock(), event)


@pytest.mark.asyncio
async def test_skips_event_when_product_missing():
    from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter
    from holiday_peak_lib.adapters.product_adapter import ProductConnector
    from product_management_consistency_validation.adapters import (
        CompletenessStorageAdapter,
        ProductConsistencyAdapters,
        ProductConsistencyValidator,
    )

    connector = ProductConnector(adapter=MockProductAdapter())
    # Mock get_product to return None
    connector.get_product = AsyncMock(return_value=None)  # type: ignore[method-assign]
    completeness = CompletenessStorageAdapter()
    adapters = ProductConsistencyAdapters(
        products=connector,
        validator=ProductConsistencyValidator(),
        completeness=completeness,
    )

    with patch(
        "product_management_consistency_validation.event_consumer.build_consistency_adapters",
        return_value=adapters,
    ):
        handlers = build_completeness_event_handlers()
        handler = handlers["completeness-jobs"]
        event = _make_event(
            {"event_type": "completeness_requested", "data": {"entity_id": "MISSING-SKU"}}
        )
        await handler(MagicMock(), event)


@pytest.mark.asyncio
async def test_evaluates_completeness_and_stores_report():
    from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter
    from holiday_peak_lib.adapters.product_adapter import ProductConnector
    from product_management_consistency_validation.adapters import (
        CompletenessStorageAdapter,
        ProductConsistencyAdapters,
        ProductConsistencyValidator,
    )

    product = _make_product(sku="SKU-10", category="apparel")
    schema = _make_schema("apparel")

    connector = ProductConnector(adapter=MockProductAdapter())
    connector.get_product = AsyncMock(return_value=product)  # type: ignore[method-assign]
    completeness = CompletenessStorageAdapter()
    completeness.seed_schema(schema)
    adapters = ProductConsistencyAdapters(
        products=connector,
        validator=ProductConsistencyValidator(),
        completeness=completeness,
    )

    with patch(
        "product_management_consistency_validation.event_consumer.build_consistency_adapters",
        return_value=adapters,
    ):
        handlers = build_completeness_event_handlers(completeness_threshold=0.7)
        handler = handlers["completeness-jobs"]
        event = _make_event(
            {
                "event_type": "completeness_requested",
                "data": {"entity_id": "SKU-10", "category_id": "apparel"},
            }
        )
        await handler(MagicMock(), event)

    # Report should be stored in memory
    assert "SKU-10" in completeness._report_store
    stored = completeness._report_store["SKU-10"]
    assert stored["entity_id"] == "SKU-10"
    assert stored["completeness_score"] > 0.0


@pytest.mark.asyncio
async def test_publishes_enrichment_job_below_threshold(monkeypatch):
    from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter
    from holiday_peak_lib.adapters.product_adapter import ProductConnector
    from holiday_peak_lib.schemas.product import CatalogProduct
    from product_management_consistency_validation.adapters import (
        CompletenessStorageAdapter,
        ProductConsistencyAdapters,
        ProductConsistencyValidator,
    )

    # Product missing description (enrichable) and price → score < 0.7 (name only: 2/4)
    product = CatalogProduct(
        sku="SKU-LOW",
        name="Low Score Product",
        category="apparel",
    )
    schema = _make_schema("apparel")

    connector = ProductConnector(adapter=MockProductAdapter())
    connector.get_product = AsyncMock(return_value=product)  # type: ignore[method-assign]
    completeness = CompletenessStorageAdapter()
    completeness.seed_schema(schema)
    adapters = ProductConsistencyAdapters(
        products=connector,
        validator=ProductConsistencyValidator(),
        completeness=completeness,
    )

    published: list[str] = []

    async def _fake_publish(entity_id, report):
        published.append(entity_id)

    with (
        patch(
            "product_management_consistency_validation.event_consumer.build_consistency_adapters",
            return_value=adapters,
        ),
        patch(
            "product_management_consistency_validation.event_consumer._publish_enrichment_job",
            side_effect=_fake_publish,
        ),
    ):
        handlers = build_completeness_event_handlers(completeness_threshold=0.9)
        handler = handlers["completeness-jobs"]
        event = _make_event(
            {
                "event_type": "completeness_requested",
                "data": {"entity_id": "SKU-LOW", "category_id": "apparel"},
            }
        )
        await handler(MagicMock(), event)

    # The product has name filled (score = 2/4 = 0.5 < 0.9 threshold)
    # so enrichment should be triggered
    assert "SKU-LOW" in published
