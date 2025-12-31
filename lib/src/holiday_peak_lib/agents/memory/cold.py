"""Cold memory layer using Azure Blob Storage."""
from typing import Optional

from azure.identity import DefaultAzureCredential
from azure.storage.blob.aio import BlobServiceClient

from holiday_peak_lib.utils.logging import configure_logging, log_async_operation


logger = configure_logging()


class ColdMemory:
    """Blob-backed cold memory for long-term state."""

    def __init__(self, account_url: str, container_name: str) -> None:
        self.account_url = account_url
        self.container_name = container_name
        self.client: Optional[BlobServiceClient] = None

    async def connect(self) -> None:
        async def _connect():
            credential = DefaultAzureCredential()
            self.client = BlobServiceClient(self.account_url, credential=credential)

        await log_async_operation(
            logger,
            name="cold_memory.connect",
            intent=self.account_url,
            func=_connect,
            metadata={"account_url": self.account_url},
        )

    async def upload_text(self, blob_name: str, data: str) -> None:
        if not self.client:
            await self.connect()
        container = self.client.get_container_client(self.container_name)
        await log_async_operation(
            logger,
            name="cold_memory.upload_text",
            intent=blob_name,
            func=lambda: container.upload_blob(name=blob_name, data=data, overwrite=True),
            metadata={"container": self.container_name},
        )

    async def download_text(self, blob_name: str) -> str:
        if not self.client:
            await self.connect()
        container = self.client.get_container_client(self.container_name)

        async def _download():
            stream = await container.download_blob(blob_name)
            return await stream.readall()

        return await log_async_operation(
            logger,
            name="cold_memory.download_text",
            intent=blob_name,
            func=_download,
            metadata={"container": self.container_name},
        )
