"""Funnel/marketing connector and canonical interfaces.

Builds agent-ready funnel metrics to support campaign effectiveness and journey
analysis scenarios referenced in the business summary. Doctests illustrate how
adapter payloads become validated funnel contexts.
"""

from typing import Optional

from holiday_peak_lib.adapters.base import BaseAdapter, BaseConnector
from holiday_peak_lib.schemas.funnel import FunnelContext, FunnelMetric


class FunnelConnector(BaseConnector):
    """Connector that normalizes funnel/marketing metrics for agents.

    Doctest with a minimal adapter::

        >>> import asyncio
        >>> class MiniFunnelAdapter(BaseAdapter):
        ...     async def _connect_impl(self, **kwargs):
        ...         return None
        ...     async def _fetch_impl(self, query):
        ...         return [{"stage": "view", "count": 100}]
        ...     async def _upsert_impl(self, payload):
        ...         return payload
        ...     async def _delete_impl(self, identifier):
        ...         return True
        >>> connector = FunnelConnector(adapter=MiniFunnelAdapter())
        >>> asyncio.run(connector.get_metrics(campaign_id="cmp-1"))[0].count
        100
        >>> asyncio.run(connector.build_funnel_context(campaign_id="cmp-1")).metrics[0].stage
        'view'
    """

    def __init__(self, adapter: Optional[BaseAdapter] = None, map_concurrency: int = 10) -> None:
        super().__init__(adapter=adapter, map_concurrency=map_concurrency)

    async def get_metrics(
        self, campaign_id: Optional[str] = None, account_id: Optional[str] = None, limit: int = 20
    ) -> list[FunnelMetric]:
        """Fetch and normalize funnel metrics for a campaign or account.

        Doctest::

            >>> import asyncio
            >>> class FunnelMetricsAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [{'stage': 'click', 'count': 10}]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = FunnelConnector(adapter=FunnelMetricsAdapter())
            >>> asyncio.run(connector.get_metrics(account_id='acct'))[0].stage
            'click'
        """
        records = await self._fetch_many(
            entity="funnel",
            campaign_id=campaign_id,
            account_id=account_id,
            limit=limit,
        )
        return await self._map_many(FunnelMetric, records)

    async def build_funnel_context(
        self, campaign_id: Optional[str] = None, account_id: Optional[str] = None, limit: int = 20
    ) -> FunnelContext:
        """Assemble funnel metrics into agent-ready context.

        Doctest::

            >>> import asyncio
            >>> class FunnelCtxAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [{'stage': 'view', 'count': 50}]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = FunnelConnector(adapter=FunnelCtxAdapter())
            >>> ctx = asyncio.run(connector.build_funnel_context(account_id='acct-1'))
            >>> (ctx.account_id, ctx.metrics[0].count)
            ('acct-1', 50)
        """
        metrics = await self.get_metrics(campaign_id=campaign_id, account_id=account_id, limit=limit)
        return FunnelContext(campaign_id=campaign_id, account_id=account_id, metrics=metrics)
