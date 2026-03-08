"""Truth Store Cosmos DB adapter (Issue #91).

Extends :class:`~holiday_peak_lib.adapters.base.BaseAdapter` to provide
CRUD operations against the Product Truth Layer Cosmos DB containers.

Key design decisions:
- Reuses a singleton ``CosmosClient`` — callers supply it at construction time.
- Partition-key-aware queries to avoid cross-partition scans.
- Idempotent upserts via the Cosmos SDK ``upsert_item`` method.
- Handles HTTP 429 (rate limit) via the built-in resilience in BaseAdapter.
"""

from __future__ import annotations

from typing import Any, Iterable, Optional

from holiday_peak_lib.adapters.base import BaseAdapter


class TruthStoreAdapter(BaseAdapter):
    """Cosmos DB adapter for the Product Truth Layer containers.

    Parameters
    ----------
    cosmos_client:
        An ``azure.cosmos.aio.CosmosClient`` instance (injected for
        singleton reuse and testability).
    database_name:
        Name of the Cosmos DB SQL database that holds the truth containers.
    container_name:
        The specific container this adapter instance targets (e.g.
        ``"products"``, ``"attributes_truth"``).

    Example
    -------
    >>> from unittest.mock import AsyncMock, MagicMock
    >>> client = MagicMock()
    >>> adapter = TruthStoreAdapter(
    ...     cosmos_client=client,
    ...     database_name="holiday-peak-db",
    ...     container_name="products",
    ... )
    >>> adapter._container_name
    'products'
    """

    def __init__(
        self,
        *,
        cosmos_client: Any,
        database_name: str,
        container_name: str,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._cosmos_client = cosmos_client
        self._database_name = database_name
        self._container_name = container_name
        self._container_proxy: Any = None

    # ------------------------------------------------------------------
    # BaseAdapter hooks
    # ------------------------------------------------------------------

    async def _connect_impl(self, **kwargs: Any) -> None:
        """Resolve the Cosmos container proxy."""
        db = self._cosmos_client.get_database_client(self._database_name)
        self._container_proxy = db.get_container_client(self._container_name)

    async def _fetch_impl(self, query: dict[str, Any]) -> Iterable[dict[str, Any]]:
        """Execute a point-read (by ``id`` + partition key) or a parametrised query.

        If the query dict contains ``"id"`` and ``"partition_key"`` the adapter
        performs a cheap point-read. Otherwise it constructs a SQL query from
        the key/value pairs supplied.
        """
        self._assert_connected()
        container = self._container_proxy

        item_id = query.get("id")
        partition_key = query.get("partition_key")

        if item_id and partition_key:
            try:
                item = await container.read_item(item=item_id, partition_key=partition_key)
                return [item]
            except Exception:  # noqa: BLE001
                return []

        # Build a simple equality filter from remaining keys.
        conditions = [f"c.{k} = @{k}" for k in query if k not in ("id", "partition_key")]
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM c WHERE {where_clause}"  # noqa: S608
        parameters = [
            {"name": f"@{k}", "value": v}
            for k, v in query.items()
            if k not in ("id", "partition_key")
        ]

        items = []
        async for item in container.query_items(
            query=sql,
            parameters=parameters or None,
        ):
            items.append(item)
        return items

    async def _upsert_impl(self, payload: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Idempotent upsert of a document into the target container."""
        self._assert_connected()
        return await self._container_proxy.upsert_item(body=payload)

    async def _delete_impl(self, identifier: str) -> bool:
        """Delete a document by ``id:partition_key`` string.

        The ``identifier`` is expected in the form ``"<id>:<partition_key>"``.
        """
        self._assert_connected()
        parts = identifier.split(":", 1)
        item_id = parts[0]
        partition_key = parts[1] if len(parts) > 1 else parts[0]
        await self._container_proxy.delete_item(item=item_id, partition_key=partition_key)
        return True

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    async def get_by_id(self, item_id: str, partition_key: str) -> Optional[dict[str, Any]]:
        """Return a single document by id and partition key, or ``None``."""
        results = await self.fetch({"id": item_id, "partition_key": partition_key})
        items = list(results)
        return items[0] if items else None

    async def upsert_document(self, document: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Convenience wrapper around :meth:`upsert`."""
        return await self.upsert(document)

    async def delete_by_id(self, item_id: str, partition_key: str) -> bool:
        """Convenience wrapper around :meth:`delete`."""
        return await self.delete(f"{item_id}:{partition_key}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _assert_connected(self) -> None:
        if self._container_proxy is None:
            raise RuntimeError(
                "TruthStoreAdapter is not connected. Call `await adapter.connect()` first."
            )
