"""Unit tests for TruthStoreAdapter with mocked Cosmos DB client."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from azure.cosmos.exceptions import CosmosHttpResponseError, CosmosResourceNotFoundError
from holiday_peak_lib.adapters.base import AdapterError
from holiday_peak_lib.adapters.truth_store import TruthStoreAdapter
from holiday_peak_lib.truth.models import (
    AttributeStatus,
    AuditEvent,
    AuditEventType,
    CategorySchema,
    MappingDocument,
    ProductStyle,
    ProposedAttribute,
    TenantConfig,
    TruthAttribute,
)


def _utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def _make_adapter(mock_client=None) -> TruthStoreAdapter:
    adapter = TruthStoreAdapter(
        account_uri="https://test.documents.azure.com:443/",
        database="truth",
        retries=0,
        timeout=5.0,
    )
    if mock_client is not None:
        adapter.client = mock_client
    return adapter


def _mock_cosmos_client(return_item=None, items=None):
    """Build a mock CosmosClient that returns fixed data."""
    client = MagicMock()
    db = MagicMock()
    container = MagicMock()

    # Sync item reads/writes
    container.read_item = AsyncMock(return_value=return_item)
    container.upsert_item = AsyncMock(return_value=return_item)
    container.delete_item = AsyncMock(return_value=None)

    # Async generator for query_items
    async def _query_items(*args, **kwargs):
        for item in items or []:
            yield item

    container.query_items = _query_items

    db.get_container_client = MagicMock(return_value=container)
    client.get_database_client = MagicMock(return_value=db)
    return client, container


class TestTruthStoreAdapterConnect:
    @pytest.mark.asyncio
    async def test_connect_creates_client(self):
        adapter = _make_adapter()
        with (
            patch("holiday_peak_lib.adapters.truth_store.DefaultAzureCredential") as mock_cred,
            patch("holiday_peak_lib.adapters.truth_store.CosmosClient") as mock_cls,
        ):
            mock_cls.return_value = MagicMock()
            await adapter.connect()
            mock_cls.assert_called_once()
            assert adapter.client is not None

    @pytest.mark.asyncio
    async def test_ensure_connected_auto_connects(self):
        adapter = _make_adapter()
        with (
            patch("holiday_peak_lib.adapters.truth_store.DefaultAzureCredential"),
            patch("holiday_peak_lib.adapters.truth_store.CosmosClient") as mock_cls,
        ):
            mock_cls.return_value = MagicMock()
            await adapter._ensure_connected()
            assert adapter.client is not None


class TestGetContainer:
    def test_get_container_raises_if_not_connected(self):
        adapter = _make_adapter()
        with pytest.raises(AdapterError, match="Not connected"):
            adapter._get_container("products")

    def test_get_container_raises_for_unknown_key(self):
        client, _ = _mock_cosmos_client()
        adapter = _make_adapter(mock_client=client)
        with pytest.raises(AdapterError, match="Unknown container key"):
            adapter._get_container("nonexistent")


class TestUpsertProduct:
    @pytest.mark.asyncio
    async def test_upsert_product_returns_style(self):
        style = ProductStyle(
            id="s1",
            categoryId="CAT-1",
            name="Blue Jacket",
            source_system="pim",
            source_id="ext-s1",
        )
        item = style.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.upsert_product(style)

        container.upsert_item.assert_called_once()
        assert isinstance(result, ProductStyle)
        assert result.id == "s1"


class TestGetProduct:
    @pytest.mark.asyncio
    async def test_get_product_returns_style(self):
        style = ProductStyle(
            id="s1",
            categoryId="CAT-1",
            name="Jacket",
            source_system="pim",
            source_id="ext-s1",
        )
        item = style.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.get_product("s1", "CAT-1")

        container.read_item.assert_called_once_with("s1", partition_key="CAT-1")
        assert isinstance(result, ProductStyle)

    @pytest.mark.asyncio
    async def test_get_product_returns_none_on_404(self):
        client, container = _mock_cosmos_client()
        container.read_item = AsyncMock(
            side_effect=CosmosResourceNotFoundError(message="not found", response=None)
        )
        adapter = _make_adapter(mock_client=client)

        result = await adapter.get_product("missing", "CAT-1")

        assert result is None


class TestListProducts:
    @pytest.mark.asyncio
    async def test_list_products_returns_list(self):
        style = ProductStyle(
            id="s1",
            categoryId="CAT-1",
            name="Jacket",
            source_system="pim",
            source_id="ext-s1",
        )
        item = style.model_dump(mode="json", by_alias=True)
        client, _ = _mock_cosmos_client(items=[item])
        adapter = _make_adapter(mock_client=client)

        results = await adapter.list_products("CAT-1", limit=10, offset=0)

        assert len(results) == 1
        assert isinstance(results[0], ProductStyle)


class TestTruthAttributes:
    @pytest.mark.asyncio
    async def test_upsert_truth_attribute(self):
        attr = TruthAttribute(
            entityId="s1",
            attribute_name="color",
            attribute_value="blue",
            confidence=0.99,
            source_system="enrichment",
            source_id="job-1",
        )
        item = attr.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.upsert_truth_attribute(attr)

        container.upsert_item.assert_called_once()
        assert isinstance(result, TruthAttribute)
        assert result.confidence == 0.99

    @pytest.mark.asyncio
    async def test_get_truth_attributes_returns_list(self):
        attr = TruthAttribute(
            entityId="s1",
            attribute_name="color",
            attribute_value="blue",
            confidence=0.9,
            source_system="enrichment",
            source_id="job-1",
        )
        item = attr.model_dump(mode="json", by_alias=True)
        client, _ = _mock_cosmos_client(items=[item])
        adapter = _make_adapter(mock_client=client)

        results = await adapter.get_truth_attributes("s1")

        assert len(results) == 1
        assert isinstance(results[0], TruthAttribute)


class TestProposedAttributes:
    @pytest.mark.asyncio
    async def test_upsert_proposed_attribute(self):
        attr = ProposedAttribute(
            entityId="s1",
            attribute_name="material",
            attribute_value="cotton",
            confidence=0.8,
            source_system="ai",
            source_id="run-42",
        )
        item = attr.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.upsert_proposed_attribute(attr)

        assert isinstance(result, ProposedAttribute)
        assert result.status == AttributeStatus.PENDING

    @pytest.mark.asyncio
    async def test_get_proposed_attributes_no_filter(self):
        attr = ProposedAttribute(
            entityId="s1",
            attribute_name="material",
            attribute_value="cotton",
            confidence=0.8,
            source_system="ai",
            source_id="run-42",
        )
        item = attr.model_dump(mode="json", by_alias=True)
        client, _ = _mock_cosmos_client(items=[item])
        adapter = _make_adapter(mock_client=client)

        results = await adapter.get_proposed_attributes("s1")

        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_proposed_attributes_with_status_filter(self):
        attr = ProposedAttribute(
            entityId="s1",
            attribute_name="material",
            attribute_value="cotton",
            confidence=0.8,
            source_system="ai",
            source_id="run-42",
            status=AttributeStatus.APPROVED,
        )
        item = attr.model_dump(mode="json", by_alias=True)
        client, _ = _mock_cosmos_client(items=[item])
        adapter = _make_adapter(mock_client=client)

        results = await adapter.get_proposed_attributes("s1", status="approved")

        assert len(results) == 1
        assert results[0].status == AttributeStatus.APPROVED

    @pytest.mark.asyncio
    async def test_update_proposed_status(self):
        attr = ProposedAttribute(
            id="p1",
            entityId="s1",
            attribute_name="material",
            attribute_value="cotton",
            confidence=0.8,
            source_system="ai",
            source_id="run-42",
            status=AttributeStatus.PENDING,
        )
        item = attr.model_dump(mode="json", by_alias=True)
        # read_item returns pending, upsert_item returns approved version
        approved_item = {**item, "status": "approved"}
        client, container = _mock_cosmos_client(return_item=item)
        container.upsert_item = AsyncMock(return_value=approved_item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.update_proposed_status("p1", "s1", "approved")

        assert result is not None
        assert result.status == AttributeStatus.APPROVED

    @pytest.mark.asyncio
    async def test_update_proposed_status_returns_none_if_not_found(self):
        client, container = _mock_cosmos_client()
        container.read_item = AsyncMock(
            side_effect=CosmosResourceNotFoundError(message="not found", response=None)
        )
        adapter = _make_adapter(mock_client=client)

        result = await adapter.update_proposed_status("missing", "s1", "approved")

        assert result is None


class TestSchemas:
    @pytest.mark.asyncio
    async def test_get_schema_returns_category_schema(self):
        schema = CategorySchema(
            id="CAT-1",
            categoryId="CAT-1",
            category_name="Category 1",
            required_attributes=["color"],
        )
        item = schema.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.get_schema("CAT-1")

        assert isinstance(result, CategorySchema)
        assert "color" in result.required_attributes

    @pytest.mark.asyncio
    async def test_get_schema_returns_none_on_404(self):
        client, container = _mock_cosmos_client()
        container.read_item = AsyncMock(
            side_effect=CosmosResourceNotFoundError(message="not found", response=None)
        )
        adapter = _make_adapter(mock_client=client)

        result = await adapter.get_schema("MISSING")

        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_schema(self):
        schema = CategorySchema(id="CAT-1", categoryId="CAT-1", category_name="Cat 1")
        item = schema.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.upsert_schema(schema)

        assert isinstance(result, CategorySchema)
        container.upsert_item.assert_called_once()


class TestMappings:
    @pytest.mark.asyncio
    async def test_get_mapping_returns_document(self):
        md = MappingDocument(
            id="gs1:2024.1",
            protocol="gs1",
            protocol_version="2024.1",
            mappings={"color": "ColourCode"},
        )
        item = md.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.get_mapping("gs1", "2024.1")

        assert isinstance(result, MappingDocument)
        assert result.protocol == "gs1"
        container.read_item.assert_called_once_with("gs1:2024.1", partition_key="2024.1")

    @pytest.mark.asyncio
    async def test_get_mapping_returns_none_on_404(self):
        client, container = _mock_cosmos_client()
        container.read_item = AsyncMock(
            side_effect=CosmosResourceNotFoundError(message="not found", response=None)
        )
        adapter = _make_adapter(mock_client=client)

        result = await adapter.get_mapping("unknown", "1.0")

        assert result is None


class TestAudit:
    @pytest.mark.asyncio
    async def test_write_audit(self):
        event = AuditEvent(
            entityId="s1",
            event_type=AuditEventType.APPROVED,
            actor="user@example.com",
            source_system="hitl",
            source_id="review-001",
        )
        item = event.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.write_audit(event)

        assert isinstance(result, AuditEvent)
        container.upsert_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_query_audit_no_action_filter(self):
        event = AuditEvent(
            entityId="s1",
            event_type=AuditEventType.APPROVED,
            actor="user@example.com",
            source_system="hitl",
            source_id="review-001",
        )
        item = event.model_dump(mode="json", by_alias=True)
        client, _ = _mock_cosmos_client(items=[item])
        adapter = _make_adapter(mock_client=client)

        results = await adapter.query_audit("s1")

        assert len(results) == 1
        assert isinstance(results[0], AuditEvent)

    @pytest.mark.asyncio
    async def test_query_audit_with_action_filter(self):
        event = AuditEvent(
            entityId="s1",
            event_type=AuditEventType.APPROVED,
            actor="user@example.com",
            source_system="hitl",
            source_id="review-001",
        )
        item = event.model_dump(mode="json", by_alias=True)
        client, _ = _mock_cosmos_client(items=[item])
        adapter = _make_adapter(mock_client=client)

        results = await adapter.query_audit("s1", event_type="approved")

        assert len(results) == 1


class TestConfig:
    @pytest.mark.asyncio
    async def test_upsert_config(self):
        config = TenantConfig(
            id="tenant-1",
            tenantId="tenant-1",
            tenant_name="Test Tenant",
            settings={"locale": "en-US"},
        )
        item = config.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.upsert_config(config)

        assert isinstance(result, TenantConfig)
        assert result.tenant_id == "tenant-1"
        container.upsert_item.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_config_returns_config(self):
        config = TenantConfig(
            id="tenant-1",
            tenantId="tenant-1",
            tenant_name="Test Tenant",
            settings={"locale": "en-US"},
        )
        item = config.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)
        adapter = _make_adapter(mock_client=client)

        result = await adapter.get_config("tenant-1")

        assert isinstance(result, TenantConfig)
        container.read_item.assert_called_once_with("tenant-1", partition_key="tenant-1")

    @pytest.mark.asyncio
    async def test_get_config_returns_none_on_404(self):
        client, container = _mock_cosmos_client()
        container.read_item = AsyncMock(
            side_effect=CosmosResourceNotFoundError(message="not found", response=None)
        )
        adapter = _make_adapter(mock_client=client)

        result = await adapter.get_config("missing")

        assert result is None


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_cosmos_429_retries(self):
        """Adapter should retry on 429 and eventually succeed."""
        style = ProductStyle(
            id="s1",
            categoryId="CAT-1",
            name="Jacket",
            source_system="pim",
            source_id="ext-s1",
        )
        item = style.model_dump(mode="json", by_alias=True)
        client, container = _mock_cosmos_client(return_item=item)

        call_count = 0

        async def flaky_upsert(payload):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                mock_response = MagicMock()
                mock_response.status_code = 429
                exc = CosmosHttpResponseError(message="Too many requests", response=mock_response)
                exc.status_code = 429
                exc.headers = {"x-ms-retry-after-ms": "10"}
                raise exc
            return payload

        container.upsert_item = flaky_upsert
        adapter = _make_adapter(mock_client=client)

        result = await adapter.upsert_product(style)

        assert call_count == 2
        assert isinstance(result, ProductStyle)

    @pytest.mark.asyncio
    async def test_cosmos_http_error_raises_adapter_error(self):
        """Non-429 Cosmos errors are wrapped in AdapterError."""
        client, container = _mock_cosmos_client()
        mock_response = MagicMock()
        mock_response.status_code = 500
        exc = CosmosHttpResponseError(message="Internal Server Error", response=mock_response)
        exc.status_code = 500
        container.read_item = AsyncMock(side_effect=exc)
        adapter = _make_adapter(mock_client=client)

        with pytest.raises(AdapterError, match="Cosmos operation failed"):
            await adapter.get_product("s1", "CAT-1")

    @pytest.mark.asyncio
    async def test_fetch_impl_requires_container(self):
        client, _ = _mock_cosmos_client()
        adapter = _make_adapter(mock_client=client)
        with pytest.raises(AdapterError, match="_container is required"):
            await adapter._fetch_impl({"_sql": "SELECT 1"})

    @pytest.mark.asyncio
    async def test_fetch_impl_requires_sql(self):
        client, _ = _mock_cosmos_client()
        adapter = _make_adapter(mock_client=client)
        with pytest.raises(AdapterError, match="_sql is required"):
            await adapter._fetch_impl({"_container": "products"})

    @pytest.mark.asyncio
    async def test_delete_impl_bad_identifier_format(self):
        client, _ = _mock_cosmos_client()
        adapter = _make_adapter(mock_client=client)
        with pytest.raises(AdapterError, match="identifier must be formatted"):
            await adapter._delete_impl("badformat")

    @pytest.mark.asyncio
    async def test_delete_impl_returns_false_on_404(self):
        client, container = _mock_cosmos_client()
        container.delete_item = AsyncMock(
            side_effect=CosmosResourceNotFoundError(message="not found", response=None)
        )
        adapter = _make_adapter(mock_client=client)

        result = await adapter._delete_impl("products:s1:CAT-1")

        assert result is False

    @pytest.mark.asyncio
    async def test_delete_impl_returns_true_on_success(self):
        client, container = _mock_cosmos_client()
        container.delete_item = AsyncMock(return_value=None)
        adapter = _make_adapter(mock_client=client)

        result = await adapter._delete_impl("products:s1:CAT-1")

        assert result is True
