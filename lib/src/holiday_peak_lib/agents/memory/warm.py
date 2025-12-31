"""Warm memory layer using Azure Cosmos DB."""
from typing import Any, Dict, Optional

from azure.cosmos.aio import CosmosClient
from azure.identity import DefaultAzureCredential

from holiday_peak_lib.utils.logging import configure_logging, log_async_operation


logger = configure_logging()


class WarmMemory:
    """Cosmos-backed warm memory for conversation threads."""

    def __init__(self, account_uri: str, database: str, container: str) -> None:
        self.account_uri = account_uri
        self.database = database
        self.container = container
        self.client: Optional[CosmosClient] = None

    async def connect(self) -> None:
        async def _connect():
            credential = DefaultAzureCredential()
            self.client = CosmosClient(self.account_uri, credential)

        await log_async_operation(
            logger,
            name="warm_memory.connect",
            intent=self.account_uri,
            func=_connect,
            metadata={"account_uri": self.account_uri},
        )

    async def upsert(self, item: Dict[str, Any]) -> Dict[str, Any]:
        if not self.client:
            await self.connect()
        database = self.client.get_database_client(self.database)
        container = database.get_container_client(self.container)
        await log_async_operation(
            logger,
            name="warm_memory.upsert",
            intent=item.get("id"),
            func=lambda: container.upsert_item(item),
            token_count=None,
            metadata={"db": self.database, "container": self.container},
        )
        return item

    async def read(self, item_id: str, partition_key: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            await self.connect()
        database = self.client.get_database_client(self.database)
        container = database.get_container_client(self.container)
        return await log_async_operation(
            logger,
            name="warm_memory.read",
            intent=item_id,
            func=lambda: container.read_item(item_id, partition_key=partition_key),
            token_count=None,
            metadata={"db": self.database, "container": self.container},
        )
