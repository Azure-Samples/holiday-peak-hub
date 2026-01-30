"""Base repository for Cosmos DB operations using Managed Identity."""

import logging
from typing import Any, Generic, TypeVar

from azure.cosmos.aio import CosmosClient, DatabaseProxy
from azure.identity.aio import DefaultAzureCredential

from crud_service.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository for Cosmos DB operations.
    
    Uses Managed Identity for authentication (no connection string).
    Provides common CRUD operations with partition key support.
    """

    def __init__(self, container_name: str):
        """
        Initialize repository.
        
        Args:
            container_name: Name of Cosmos DB container
        """
        self.container_name = container_name
        self._client: CosmosClient | None = None
        self._database: DatabaseProxy | None = None

    async def _ensure_client(self):
        """Ensure Cosmos DB client is initialized."""
        if self._client is None:
            credential = DefaultAzureCredential()
            self._client = CosmosClient(
                url=settings.cosmos_account_uri,
                credential=credential,
            )
            self._database = self._client.get_database_client(settings.cosmos_database)

    async def get_container(self):
        """Get container client."""
        await self._ensure_client()
        return self._database.get_container_client(self.container_name)

    async def create(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new item.
        
        Args:
            item: Item to create (must include 'id' and partition key)
            
        Returns:
            Created item with metadata
        """
        container = await self.get_container()
        return await container.create_item(body=item)

    async def get_by_id(
        self, item_id: str, partition_key: str | None = None
    ) -> dict[str, Any] | None:
        """
        Get item by ID.
        
        Args:
            item_id: Item ID
            partition_key: Partition key value (optional if same as ID)
            
        Returns:
            Item or None if not found
        """
        container = await self.get_container()
        try:
            return await container.read_item(
                item=item_id,
                partition_key=partition_key or item_id,
            )
        except Exception as e:
            logger.warning(f"Item not found: {item_id} - {e}")
            return None

    async def update(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Update an existing item (upsert).
        
        Args:
            item: Item to update (must include 'id' and partition key)
            
        Returns:
            Updated item with metadata
        """
        container = await self.get_container()
        return await container.upsert_item(body=item)

    async def delete(self, item_id: str, partition_key: str | None = None) -> None:
        """
        Delete an item.
        
        Args:
            item_id: Item ID
            partition_key: Partition key value (optional if same as ID)
        """
        container = await self.get_container()
        await container.delete_item(
            item=item_id,
            partition_key=partition_key or item_id,
        )

    async def query(
        self,
        query: str,
        parameters: list[dict[str, Any]] | None = None,
        partition_key: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Execute a SQL query.
        
        Args:
            query: SQL query string
            parameters: Query parameters (e.g., [{"name": "@id", "value": "123"}])
            partition_key: Partition key for query (enables single-partition query)
            
        Returns:
            List of items matching query
        """
        container = await self.get_container()
        items = []
        async for item in container.query_items(
            query=query,
            parameters=parameters,
            partition_key=partition_key,
        ):
            items.append(item)
        return items

    async def close(self):
        """Close Cosmos DB client."""
        if self._client:
            await self._client.close()
            self._client = None
            self._database = None
