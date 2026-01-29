"""Tests for memory modules."""
import pytest
from unittest.mock import AsyncMock, patch
from holiday_peak_lib.agents.memory.hot import HotMemory
from holiday_peak_lib.agents.memory.warm import WarmMemory
from holiday_peak_lib.agents.memory.cold import ColdMemory


class TestHotMemory:
    """Test HotMemory (Redis) functionality."""

    def test_create_hot_memory(self):
        """Test creating hot memory instance."""
        memory = HotMemory("redis://localhost:6379")
        assert memory.url == "redis://localhost:6379"
        assert memory.client is None

    def test_create_with_options(self):
        """Test creating hot memory with options."""
        memory = HotMemory(
            "redis://localhost:6379",
            max_connections=50,
            socket_timeout=5.0,
            socket_connect_timeout=2.0,
            health_check_interval=30,
            retry_on_timeout=True
        )
        assert memory.max_connections == 50
        assert memory.socket_timeout == 5.0
        assert memory.retry_on_timeout is True

    @pytest.mark.asyncio
    async def test_connect(self, mock_redis_client, monkeypatch):
        """Test connecting to Redis."""
        memory = HotMemory("redis://localhost:6379")
        
        with patch("redis.asyncio.ConnectionPool.from_url") as mock_pool:
            with patch("redis.asyncio.Redis") as mock_redis:
                mock_redis.return_value = mock_redis_client
                await memory.connect()
                assert memory.client is not None

    @pytest.mark.asyncio
    async def test_set_value(self, mock_redis_client, monkeypatch):
        """Test setting a value in Redis."""
        memory = HotMemory("redis://localhost:6379")
        monkeypatch.setattr(memory, "client", mock_redis_client)
        
        await memory.set("test_key", "test_value", ttl_seconds=300)
        mock_redis_client.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_connects_if_needed(self, mock_redis_client):
        """Test set auto-connects if not connected."""
        memory = HotMemory("redis://localhost:6379")
        
        with patch.object(memory, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            memory.client = mock_redis_client
            await memory.set("key", "value")
            # Should check connection status

    @pytest.mark.asyncio
    async def test_get_value(self, mock_redis_client, monkeypatch):
        """Test getting a value from Redis."""
        memory = HotMemory("redis://localhost:6379")
        monkeypatch.setattr(memory, "client", mock_redis_client)
        mock_redis_client.get.return_value = "retrieved_value"
        
        result = await memory.get("test_key")
        assert result == "retrieved_value"
        mock_redis_client.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_connects_if_needed(self, mock_redis_client):
        """Test get auto-connects if not connected."""
        memory = HotMemory("redis://localhost:6379")
        
        with patch.object(memory, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            memory.client = mock_redis_client
            await memory.get("key")


class TestWarmMemory:
    """Test WarmMemory (Cosmos DB) functionality."""

    def test_create_warm_memory(self):
        """Test creating warm memory instance."""
        memory = WarmMemory(
            account_uri="https://test.documents.azure.com",
            database="test_db",
            container="test_container"
        )
        assert memory.account_uri == "https://test.documents.azure.com"
        assert memory.database == "test_db"
        assert memory.container == "test_container"
        assert memory.client is None

    def test_create_with_options(self):
        """Test creating warm memory with options."""
        memory = WarmMemory(
            account_uri="https://test.documents.azure.com",
            database="test_db",
            container="test_container",
            connection_limit=100,
            client_kwargs={"timeout": 10}
        )
        assert memory.connection_limit == 100
        assert memory.client_kwargs == {"timeout": 10}

    @pytest.mark.asyncio
    async def test_connect(self, mock_cosmos_client):
        """Test connecting to Cosmos DB."""
        memory = WarmMemory(
            account_uri="https://test.documents.azure.com",
            database="test_db",
            container="test_container"
        )
        
        with patch("azure.cosmos.aio.CosmosClient") as mock_client_class:
            mock_client_class.return_value = mock_cosmos_client
            await memory.connect()
            assert memory.client is not None

    @pytest.mark.asyncio
    async def test_upsert_item(self, mock_cosmos_client, monkeypatch):
        """Test upserting an item."""
        memory = WarmMemory(
            account_uri="https://test.documents.azure.com",
            database="test_db",
            container="test_container"
        )
        monkeypatch.setattr(memory, "client", mock_cosmos_client)
        
        item = {"id": "test123", "data": "value"}
        result = await memory.upsert(item)
        assert result["id"] == "test123"

    @pytest.mark.asyncio
    async def test_upsert_connects_if_needed(self, mock_cosmos_client):
        """Test upsert auto-connects if not connected."""
        memory = WarmMemory(
            account_uri="https://test.documents.azure.com",
            database="test_db",
            container="test_container"
        )
        
        with patch.object(memory, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            memory.client = mock_cosmos_client
            await memory.upsert({"id": "test"})

    @pytest.mark.asyncio
    async def test_read_item(self, mock_cosmos_client, monkeypatch):
        """Test reading an item."""
        memory = WarmMemory(
            account_uri="https://test.documents.azure.com",
            database="test_db",
            container="test_container"
        )
        monkeypatch.setattr(memory, "client", mock_cosmos_client)
        
        result = await memory.read("test123", "partition_key")
        assert result["id"] == "test"

    @pytest.mark.asyncio
    async def test_read_connects_if_needed(self, mock_cosmos_client):
        """Test read auto-connects if not connected."""
        memory = WarmMemory(
            account_uri="https://test.documents.azure.com",
            database="test_db",
            container="test_container"
        )
        
        with patch.object(memory, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            memory.client = mock_cosmos_client
            await memory.read("test", "pk")


class TestColdMemory:
    """Test ColdMemory (Blob Storage) functionality."""

    def test_create_cold_memory(self):
        """Test creating cold memory instance."""
        memory = ColdMemory(
            account_url="https://test.blob.core.windows.net",
            container_name="test_container"
        )
        assert memory.account_url == "https://test.blob.core.windows.net"
        assert memory.container_name == "test_container"
        assert memory.client is None

    def test_create_with_options(self):
        """Test creating cold memory with options."""
        memory = ColdMemory(
            account_url="https://test.blob.core.windows.net",
            container_name="test_container",
            connection_pool_size=50,
            connection_timeout=5.0,
            read_timeout=30.0
        )
        assert memory.connection_pool_size == 50
        assert memory.connection_timeout == 5.0
        assert memory.read_timeout == 30.0

    @pytest.mark.asyncio
    async def test_connect(self, mock_blob_client):
        """Test connecting to Blob Storage."""
        memory = ColdMemory(
            account_url="https://test.blob.core.windows.net",
            container_name="test_container"
        )
        
        with patch("azure.storage.blob.aio.BlobServiceClient") as mock_client_class:
            mock_client_class.return_value = mock_blob_client
            await memory.connect()
            assert memory.client is not None

    @pytest.mark.asyncio
    async def test_upload_text(self, mock_blob_client, monkeypatch):
        """Test uploading text to blob."""
        memory = ColdMemory(
            account_url="https://test.blob.core.windows.net",
            container_name="test_container"
        )
        monkeypatch.setattr(memory, "client", mock_blob_client)
        
        await memory.upload_text("test_blob.txt", "test data content")
        # Verify container client was obtained
        mock_blob_client.get_container_client.assert_called_once_with("test_container")

    @pytest.mark.asyncio
    async def test_upload_connects_if_needed(self, mock_blob_client):
        """Test upload auto-connects if not connected."""
        memory = ColdMemory(
            account_url="https://test.blob.core.windows.net",
            container_name="test_container"
        )
        
        with patch.object(memory, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            memory.client = mock_blob_client
            await memory.upload_text("test.txt", "data")

    @pytest.mark.asyncio
    async def test_download_text(self, mock_blob_client, monkeypatch):
        """Test downloading text from blob."""
        memory = ColdMemory(
            account_url="https://test.blob.core.windows.net",
            container_name="test_container"
        )
        monkeypatch.setattr(memory, "client", mock_blob_client)
        
        result = await memory.download_text("test_blob.txt")
        assert result == b"test data"

    @pytest.mark.asyncio
    async def test_download_connects_if_needed(self, mock_blob_client):
        """Test download auto-connects if not connected."""
        memory = ColdMemory(
            account_url="https://test.blob.core.windows.net",
            container_name="test_container"
        )
        
        with patch.object(memory, "connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = None
            memory.client = mock_blob_client
            await memory.download_text("test.txt")


class TestMemoryIntegration:
    """Test memory tier integration."""

    @pytest.mark.asyncio
    async def test_three_tier_memory_setup(
        self,
        mock_redis_client,
        mock_cosmos_client,
        mock_blob_client,
        monkeypatch
    ):
        """Test setting up all three memory tiers."""
        hot = HotMemory("redis://localhost:6379")
        warm = WarmMemory("https://test.documents.azure.com", "db", "container")
        cold = ColdMemory("https://test.blob.core.windows.net", "container")
        
        monkeypatch.setattr(hot, "client", mock_redis_client)
        monkeypatch.setattr(warm, "client", mock_cosmos_client)
        monkeypatch.setattr(cold, "client", mock_blob_client)
        
        # Test operations on each tier
        await hot.set("key", "value")
        await warm.upsert({"id": "test"})
        await cold.upload_text("blob", "data")
        
        assert mock_redis_client.set.called
        assert hot.client is not None
        assert warm.client is not None
        assert cold.client is not None
