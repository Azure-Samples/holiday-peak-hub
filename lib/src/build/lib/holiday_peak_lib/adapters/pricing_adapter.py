"""Pricing connector and canonical interfaces.

Normalizes upstream pricing feeds into agent-ready offers to support checkout
and revenue optimization scenarios highlighted in the business summary.
Includes doctests for every helper to validate mapping and aggregation.
"""

from typing import Optional

from holiday_peak_lib.adapters.base import BaseAdapter, BaseConnector
from holiday_peak_lib.schemas.pricing import PriceContext, PriceEntry


class PricingConnector(BaseConnector):
    """Connector that normalizes pricing data for agents.

    Doctest with a minimal adapter::

        >>> import asyncio
        >>> class MiniPricingAdapter(BaseAdapter):
        ...     async def _connect_impl(self, **kwargs):
        ...         return None
        ...     async def _fetch_impl(self, query):
        ...         if query.get('entity') == 'price':
        ...             return [{"sku": "SKU-1", "currency": "USD", "amount": 10.0}]
        ...         return []
        ...     async def _upsert_impl(self, payload):
        ...         return payload
        ...     async def _delete_impl(self, identifier):
        ...         return True
        >>> connector = PricingConnector(adapter=MiniPricingAdapter())
        >>> asyncio.run(connector.get_active_price('SKU-1')).amount
        10.0
        >>> ctx = asyncio.run(connector.build_price_context('SKU-1'))
        >>> (ctx.sku, ctx.active.amount)
        ('SKU-1', 10.0)
    """

    def __init__(self, adapter: Optional[BaseAdapter] = None, map_concurrency: int = 10) -> None:
        super().__init__(adapter=adapter, map_concurrency=map_concurrency)

    async def get_prices(self, sku: str, limit: int = 10) -> list[PriceEntry]:
        """Fetch and normalize available price entries for a SKU.

        Doctest::

            >>> import asyncio
            >>> class PriceListAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [
            ...             {'sku': query['sku'], 'currency': 'USD', 'amount': 9.0},
            ...             {'sku': query['sku'], 'currency': 'USD', 'amount': 10.0},
            ...         ]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = PricingConnector(adapter=PriceListAdapter())
            >>> [p.amount for p in asyncio.run(connector.get_prices('SKU-2'))]
            [9.0, 10.0]
        """
        records = await self._fetch_many(entity="price", sku=sku, limit=limit)
        return await self._map_many(PriceEntry, records)

    async def get_active_price(self, sku: str) -> Optional[PriceEntry]:
        """Return the first active price for the SKU if available.

        Doctest::

            >>> import asyncio
            >>> class FirstPriceAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [{'sku': 'SKU-A', 'currency': 'USD', 'amount': 5.5}]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = PricingConnector(adapter=FirstPriceAdapter())
            >>> asyncio.run(connector.get_active_price('SKU-A')).amount
            5.5
        """
        records = await self.get_prices(sku, limit=1)
        return records[0] if records else None

    async def build_price_context(self, sku: str, limit: int = 10) -> PriceContext:
        """Build an aggregate pricing context for an agent prompt.

        Doctest::

            >>> import asyncio
            >>> class PriceCtxAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [
            ...             {'sku': 'SKU-C', 'currency': 'USD', 'amount': 11.0},
            ...             {'sku': 'SKU-C', 'currency': 'USD', 'amount': 12.0},
            ...         ]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = PricingConnector(adapter=PriceCtxAdapter())
            >>> ctx = asyncio.run(connector.build_price_context('SKU-C', limit=2))
            >>> (ctx.sku, ctx.active.amount, len(ctx.offers))
            ('SKU-C', 11.0, 2)
        """
        offers = await self.get_prices(sku, limit=limit)
        active = offers[0] if offers else None
        return PriceContext(sku=sku, active=active, offers=offers)
