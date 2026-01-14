"""Inventory connector and canonical interfaces.

Provides agent-ready inventory context (item + warehouse stock) for supply and
fulfillment scenarios covered in the business summary. Each helper includes a
doctest to demonstrate normalization.
"""

from typing import Optional

from holiday_peak_lib.adapters.base import BaseAdapter, BaseConnector
from holiday_peak_lib.schemas.inventory import InventoryContext, InventoryItem, WarehouseStock


class InventoryConnector(BaseConnector):
    """Connector that normalizes inventory responses for agents.

    Doctest using a minimal adapter::

        >>> import asyncio
        >>> class MiniInventoryAdapter(BaseAdapter):
        ...     async def _connect_impl(self, **kwargs):
        ...         return None
        ...     async def _fetch_impl(self, query):
        ...         if query.get("entity") == "inventory":
        ...             return [{"sku": "SKU-1", "available": 5}]
        ...         if query.get("entity") == "warehouse_stock":
        ...             return [{"sku": "SKU-1", "warehouse_id": "W1", "available": 2}]
        ...         return []
        ...     async def _upsert_impl(self, payload):
        ...         return payload
        ...     async def _delete_impl(self, identifier):
        ...         return True
        >>> connector = InventoryConnector(adapter=MiniInventoryAdapter())
        >>> asyncio.run(connector.get_item("SKU-1")).available
        5
        >>> [w.warehouse_id for w in asyncio.run(connector.get_warehouses("SKU-1"))]
        ['W1']
        >>> ctx = asyncio.run(connector.build_inventory_context("SKU-1"))
        >>> (ctx.item.sku, len(ctx.warehouses))
        ('SKU-1', 1)
    """

    def __init__(self, adapter: Optional[BaseAdapter] = None, map_concurrency: int = 10) -> None:
        super().__init__(adapter=adapter, map_concurrency=map_concurrency)

    async def get_item(self, sku: str) -> Optional[InventoryItem]:
        """Fetch and normalize a single inventory item.

        Doctest::

            >>> import asyncio
            >>> class ItemAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [{'sku': query.get('sku'), 'available': 3}]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = InventoryConnector(adapter=ItemAdapter())
            >>> asyncio.run(connector.get_item('SKU-I')).available
            3
        """
        record = await self._fetch_first(entity="inventory", sku=sku)
        return await self._map_single(InventoryItem, record)

    async def get_warehouses(self, sku: str) -> list[WarehouseStock]:
        """Fetch warehouse-level stock for the SKU.

        Doctest::

            >>> import asyncio
            >>> class WarehousesAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [{'sku': query.get('sku'), 'warehouse_id': 'W9', 'available': 7}]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = InventoryConnector(adapter=WarehousesAdapter())
            >>> asyncio.run(connector.get_warehouses('SKU-W'))[0].warehouse_id
            'W9'
        """
        records = await self._fetch_many(entity="warehouse_stock", sku=sku)
        return await self._map_many(WarehouseStock, records)

    async def build_inventory_context(self, sku: str) -> Optional[InventoryContext]:
        """Assemble item and per-warehouse stock into agent-ready context.

        Doctest::

            >>> import asyncio
            >>> class InventoryCtxAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         if query.get('entity') == 'inventory':
            ...             return [{'sku': 'CTX', 'available': 1}]
            ...         if query.get('entity') == 'warehouse_stock':
            ...             return [{'sku': 'CTX', 'warehouse_id': 'W1', 'available': 1}]
            ...         return []
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = InventoryConnector(adapter=InventoryCtxAdapter())
            >>> ctx = asyncio.run(connector.build_inventory_context('CTX'))
            >>> (ctx.item.sku, [w.warehouse_id for w in ctx.warehouses])
            ('CTX', ['W1'])
        """
        item = await self.get_item(sku)
        if item is None:
            return None
        warehouses = await self.get_warehouses(sku)
        return InventoryContext(item=item, warehouses=warehouses)
