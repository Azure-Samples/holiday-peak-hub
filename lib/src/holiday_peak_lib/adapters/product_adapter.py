"""Product catalog connector and canonical interfaces.

Maps upstream catalog data into agent-ready contexts for product discovery,
cross-sell, and enrichment tasks described in the business summary. Each
helper normalizes adapter payloads into validated domain models with bounded
async mapping and includes doctests for quick verification.
"""

from typing import Optional

from holiday_peak_lib.adapters.base import BaseAdapter, BaseConnector
from holiday_peak_lib.schemas.product import CatalogProduct, ProductContext


class ProductConnector(BaseConnector):
    """Connector that normalizes catalog products for agent consumption.

    Doctest using a minimal adapter::

        >>> import asyncio
        >>> class MiniAdapter(BaseAdapter):
        ...     async def _connect_impl(self, **kwargs):
        ...         return None
        ...     async def _fetch_impl(self, query):
        ...         if query.get("entity") == "product":
        ...             return [{"sku": "SKU-1", "name": "Widget", "price": 9.99}]
        ...         if query.get("entity") == "related":
        ...             return [{"sku": "SKU-2", "name": "Widget Plus", "price": 19.99}]
        ...         return []
        ...     async def _upsert_impl(self, payload):
        ...         return payload
        ...     async def _delete_impl(self, identifier):
        ...         return True
        >>> connector = ProductConnector(adapter=MiniAdapter())
        >>> asyncio.run(connector.get_product("SKU-1")).name
        'Widget'
        >>> [p.sku for p in asyncio.run(connector.get_related("SKU-1"))]
        ['SKU-2']
        >>> ctx = asyncio.run(connector.build_product_context("SKU-1"))
        >>> (ctx.product.sku, len(ctx.related))
        ('SKU-1', 1)
    """

    def __init__(self, adapter: Optional[BaseAdapter] = None, map_concurrency: int = 10) -> None:
        super().__init__(adapter=adapter, map_concurrency=map_concurrency)

    async def get_product(self, sku: str) -> Optional[CatalogProduct]:
        """Fetch and normalize a single catalog product.

        Process:
        - Query adapter for the target SKU.
        - Take first record and validate into ``CatalogProduct``.

        Doctest::

            >>> import asyncio
            >>> class OneProductAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         if query.get('sku') == 'SKU-X':
            ...             return [{'sku': 'SKU-X', 'name': 'X'}]
            ...         return []
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = ProductConnector(adapter=OneProductAdapter())
            >>> asyncio.run(connector.get_product('SKU-X')).sku
            'SKU-X'
        """
        record = await self._fetch_first(entity="product", sku=sku)
        return await self._map_single(CatalogProduct, record)

    async def get_related(self, sku: str, limit: int = 5) -> list[CatalogProduct]:
        """Fetch related products for cross-sell/upsell suggestions.

        Doctest::

            >>> import asyncio
            >>> class RelatedAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [{'sku': 'R1', 'name': 'Rel'}]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = ProductConnector(adapter=RelatedAdapter())
            >>> [p.sku for p in asyncio.run(connector.get_related('SKU', limit=1))]
            ['R1']
        """
        records = await self._fetch_many(entity="related", sku=sku, limit=limit)
        return await self._map_many(CatalogProduct, records)

    async def build_product_context(self, sku: str, related_limit: int = 5) -> Optional[ProductContext]:
        """Assemble agent-ready product context with related items.

        Doctest::

            >>> import asyncio
            >>> class ProductCtxAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         if query.get('entity') == 'product':
            ...             return [{'sku': 'P1', 'name': 'Main'}]
            ...         if query.get('entity') == 'related':
            ...             return [{'sku': 'P2', 'name': 'Rel'}]
            ...         return []
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = ProductConnector(adapter=ProductCtxAdapter())
            >>> ctx = asyncio.run(connector.build_product_context('P1'))
            >>> (ctx.product.sku, [p.sku for p in ctx.related])
            ('P1', ['P2'])
        """
        product = await self.get_product(sku)
        if product is None:
            return None
        related = await self.get_related(sku, limit=related_limit)
        return ProductContext(product=product, related=related)
