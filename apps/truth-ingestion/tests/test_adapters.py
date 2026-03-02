"""Unit tests for Truth Ingestion adapters and domain logic."""

from __future__ import annotations

import pytest

from truth_ingestion.adapters import (
    AuditEvent,
    DAMConnector,
    EventPublisher,
    PIMConnector,
    ProductStyle,
    ProductVariant,
    TruthStoreAdapter,
    apply_field_mapping,
    ingest_bulk_products,
    ingest_single_product,
    map_pim_to_product_style,
    map_pim_to_product_variant,
)


class TestApplyFieldMapping:
    def test_maps_canonical_to_source_keys(self):
        raw = {"product_id": "P1", "title": "Widget", "cat": "tools"}
        mapping = {"entity_id": "product_id", "name": "title", "category": "cat"}
        result = apply_field_mapping(raw, mapping)
        assert result["entity_id"] == "P1"
        assert result["name"] == "Widget"
        assert result["category"] == "tools"

    def test_preserves_unmapped_keys(self):
        raw = {"id": "X1", "extra_field": "keep_me"}
        result = apply_field_mapping(raw, {"entity_id": "id"})
        assert result["entity_id"] == "X1"
        assert result["extra_field"] == "keep_me"

    def test_handles_empty_mapping(self):
        raw = {"id": "X1", "name": "Foo"}
        result = apply_field_mapping(raw, {})
        assert result == raw


class TestMapPimToProductStyle:
    def test_default_mapping(self, sample_pim_product):
        style = map_pim_to_product_style(sample_pim_product)
        assert style.entity_id == "PROD-001"
        assert style.name == "Winter Jacket"
        assert style.category == "outerwear"
        assert style.brand == "PeakWear"
        assert style.description == "A warm winter jacket"

    def test_custom_field_mapping(self):
        raw = {"product_code": "PC-01", "title": "Scarf", "dept": "accessories"}
        style = map_pim_to_product_style(
            raw,
            field_mapping={"entity_id": "product_code", "name": "title", "category": "dept"},
        )
        assert style.entity_id == "PC-01"
        assert style.name == "Scarf"
        assert style.category == "accessories"

    def test_generates_entity_id_when_missing(self):
        style = map_pim_to_product_style({"name": "Unknown"})
        assert style.entity_id  # auto-generated UUID

    def test_to_dict_includes_record_type(self, sample_pim_product):
        style = map_pim_to_product_style(sample_pim_product)
        d = style.to_dict()
        assert d["record_type"] == "product_style"
        assert d["id"] == d["entity_id"]


class TestMapPimToProductVariant:
    def test_default_mapping(self):
        raw = {"variant_id": "V1", "sku": "WJ-BLU-L", "color": "blue", "size": "L", "price": 99.0}
        variant = map_pim_to_product_variant(raw, style_id="PROD-001")
        assert variant.entity_id == "V1"
        assert variant.sku == "WJ-BLU-L"
        assert variant.color == "blue"
        assert variant.size == "L"
        assert variant.price == 99.0
        assert variant.style_id == "PROD-001"

    def test_to_dict_includes_record_type(self):
        raw = {"variant_id": "V2", "sku": "X-S"}
        variant = map_pim_to_product_variant(raw, style_id="PROD-002")
        d = variant.to_dict()
        assert d["record_type"] == "product_variant"
        assert d["style_id"] == "PROD-002"


class TestProductStyleToDict:
    def test_round_trip(self):
        style = ProductStyle(
            entity_id="E1",
            name="Test",
            category="cat",
            brand="brand",
            description="desc",
        )
        d = style.to_dict()
        assert d["entity_id"] == "E1"
        assert d["id"] == "E1"
        assert d["record_type"] == "product_style"


class TestProductVariantToDict:
    def test_round_trip(self):
        variant = ProductVariant(
            entity_id="V1",
            style_id="S1",
            sku="SKU-001",
        )
        d = variant.to_dict()
        assert d["entity_id"] == "V1"
        assert d["style_id"] == "S1"
        assert d["record_type"] == "product_variant"


class TestAuditEvent:
    def test_to_dict(self):
        event = AuditEvent(entity_id="E1", operation="upsert")
        d = event.to_dict()
        assert d["entity_id"] == "E1"
        assert d["operation"] == "upsert"
        assert "id" in d
        assert "timestamp" in d


class TestTruthStoreAdapterInMemory:
    @pytest.mark.asyncio
    async def test_upsert_and_get_product_style(self):
        store = TruthStoreAdapter()  # No Cosmos URI — uses in-memory
        style = ProductStyle(entity_id="E1", name="Hat", category="hats", brand="B")
        await store.upsert_product_style(style)
        record = await store.get_product_style("E1")
        assert record is not None
        assert record["entity_id"] == "E1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_returns_none(self):
        store = TruthStoreAdapter()
        result = await store.get_product_style("does-not-exist")
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_is_idempotent(self):
        store = TruthStoreAdapter()
        style = ProductStyle(entity_id="E2", name="Glove", category="accessories", brand="B")
        await store.upsert_product_style(style)
        await store.upsert_product_style(style)  # upsert again — no duplicates
        assert len(store._in_memory) == 1

    @pytest.mark.asyncio
    async def test_write_audit_event(self):
        store = TruthStoreAdapter()
        event = AuditEvent(entity_id="E1")
        await store.write_audit_event(event)
        assert len(store._audit_store) == 1


class TestIngestSingleProduct:
    @pytest.mark.asyncio
    async def test_ingest_creates_style_and_variant(
        self, sample_pim_product, mock_adapters
    ):
        result = await ingest_single_product(sample_pim_product, mock_adapters)
        assert result["entity_id"] == "PROD-001"
        assert "style" in result
        assert "variants" in result
        assert len(result["variants"]) == 1
        assert result["assets_resolved"] == 1

    @pytest.mark.asyncio
    async def test_ingest_publishes_events(self, sample_pim_product, mock_adapters):
        await ingest_single_product(sample_pim_product, mock_adapters)
        mock_adapters.events.publish_completeness_job.assert_called_once_with("PROD-001")
        mock_adapters.events.publish_ingestion_notification.assert_called_once_with(
            "PROD-001", source="pim"
        )

    @pytest.mark.asyncio
    async def test_ingest_writes_audit_event(self, sample_pim_product, mock_adapters):
        await ingest_single_product(sample_pim_product, mock_adapters)
        mock_adapters.truth_store.write_audit_event.assert_called_once()

    @pytest.mark.asyncio
    async def test_ingest_no_variants(
        self, sample_pim_product_no_variants, mock_adapters
    ):
        result = await ingest_single_product(
            sample_pim_product_no_variants, mock_adapters
        )
        assert result["entity_id"] == "PROD-002"
        assert result["variants"] == []

    @pytest.mark.asyncio
    async def test_ingest_with_custom_field_mapping(self, mock_adapters):
        raw = {"product_code": "PC-999", "title": "Boots", "dept": "footwear", "maker": "Brand X"}
        result = await ingest_single_product(
            raw,
            mock_adapters,
            field_mapping={"entity_id": "product_code", "name": "title", "category": "dept",
                           "brand": "maker"},
        )
        assert result["entity_id"] == "PC-999"


class TestIngestBulkProducts:
    @pytest.mark.asyncio
    async def test_bulk_ingest_returns_all_results(
        self, sample_pim_product, sample_pim_product_no_variants, mock_adapters
    ):
        products = [sample_pim_product, sample_pim_product_no_variants]
        results = await ingest_bulk_products(products, mock_adapters)
        assert len(results) == 2
        entity_ids = {r["entity_id"] for r in results}
        assert "PROD-001" in entity_ids
        assert "PROD-002" in entity_ids

    @pytest.mark.asyncio
    async def test_bulk_ingest_handles_single_error(self, mock_adapters):
        """One bad product should not stop other ingestions."""
        from unittest.mock import AsyncMock as AM

        good = {"id": "G1", "name": "Good", "category": "c", "brand": "b"}
        bad = {"id": "BAD"}

        original = mock_adapters.truth_store.upsert_product_style
        call_count = 0

        async def sometimes_fail(style):
            nonlocal call_count
            call_count += 1
            if style.entity_id == "BAD":
                raise ValueError("simulated failure")
            return style.to_dict()

        mock_adapters.truth_store.upsert_product_style = sometimes_fail

        results = await ingest_bulk_products([good, bad], mock_adapters)
        assert len(results) == 2
        errors = [r for r in results if "error" in r]
        assert len(errors) == 1
        assert errors[0]["entity_id"] == "BAD"


class TestPIMConnectorNoUrl:
    @pytest.mark.asyncio
    async def test_fetch_product_returns_none_without_url(self):
        pim = PIMConnector(base_url="")
        result = await pim.fetch_product("X1")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_all_returns_empty_without_url(self):
        pim = PIMConnector(base_url="")
        result = await pim.fetch_all_products()
        assert result == []


class TestDAMConnectorNoUrl:
    @pytest.mark.asyncio
    async def test_fetch_assets_returns_empty_without_url(self):
        dam = DAMConnector(base_url="")
        result = await dam.fetch_assets("PROD-001")
        assert result == []


class TestEventPublisherNoConnection:
    @pytest.mark.asyncio
    async def test_publish_is_noop_without_connection_string(self):
        publisher = EventPublisher(connection_string="")
        # Should not raise
        await publisher.publish("test-hub", {"key": "value"})

    @pytest.mark.asyncio
    async def test_publish_completeness_job_noop(self):
        publisher = EventPublisher(connection_string="")
        await publisher.publish_completeness_job("PROD-001")

    @pytest.mark.asyncio
    async def test_publish_ingestion_notification_noop(self):
        publisher = EventPublisher(connection_string="")
        await publisher.publish_ingestion_notification("PROD-001")
