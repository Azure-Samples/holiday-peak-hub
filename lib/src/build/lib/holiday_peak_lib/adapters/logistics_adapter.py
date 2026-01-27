"""Logistics connector and canonical interfaces.

Transforms shipment status and event streams into agent-ready context for post-
purchase and delivery experiences described in the business summary. Every
helper includes doctests to demonstrate normalization.
"""

from typing import Optional

from holiday_peak_lib.adapters.base import BaseAdapter, BaseConnector
from holiday_peak_lib.schemas.logistics import LogisticsContext, Shipment, ShipmentEvent


class LogisticsConnector(BaseConnector):
    """Connector that normalizes shipment data for agents.

    Doctest with a minimal adapter::

        >>> import asyncio, datetime as _dt
        >>> class MiniLogAdapter(BaseAdapter):
        ...     async def _connect_impl(self, **kwargs):
        ...         return None
        ...     async def _fetch_impl(self, query):
        ...         if query.get("entity") == "shipment":
        ...             return [{"tracking_id": "T1", "status": "in_transit"}]
        ...         if query.get("entity") == "events":
        ...             return [{"code": "PU", "occurred_at": _dt.datetime(2024, 1, 1)}]
        ...         return []
        ...     async def _upsert_impl(self, payload):
        ...         return payload
        ...     async def _delete_impl(self, identifier):
        ...         return True
        >>> connector = LogisticsConnector(adapter=MiniLogAdapter())
        >>> asyncio.run(connector.get_shipment("T1")).status
        'in_transit'
        >>> [e.code for e in asyncio.run(connector.get_events("T1"))]
        ['PU']
        >>> ctx = asyncio.run(connector.build_logistics_context("T1"))
        >>> (ctx.shipment.tracking_id, len(ctx.events))
        ('T1', 1)
    """

    def __init__(self, adapter: Optional[BaseAdapter] = None, map_concurrency: int = 10) -> None:
        super().__init__(adapter=adapter, map_concurrency=map_concurrency)

    async def get_shipment(self, tracking_id: str) -> Optional[Shipment]:
        """Fetch and normalize a shipment by tracking id.

        Doctest::

            >>> import asyncio
            >>> class OneShipAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [{'tracking_id': query.get('tracking_id'), 'status': 'created'}]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = LogisticsConnector(adapter=OneShipAdapter())
            >>> asyncio.run(connector.get_shipment('T-9')).tracking_id
            'T-9'
        """
        record = await self._fetch_first(entity="shipment", tracking_id=tracking_id)
        return await self._map_single(Shipment, record)

    async def get_events(self, tracking_id: str, limit: int = 50) -> list[ShipmentEvent]:
        """Fetch and normalize shipment events.

        Doctest::

            >>> import asyncio, datetime as _dt
            >>> class EventsAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [{'code': 'DLV', 'occurred_at': _dt.datetime(2024, 1, 2)}]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = LogisticsConnector(adapter=EventsAdapter())
            >>> asyncio.run(connector.get_events('T-1'))[0].code
            'DLV'
        """
        records = await self._fetch_many(entity="events", tracking_id=tracking_id, limit=limit)
        return await self._map_many(ShipmentEvent, records)

    async def build_logistics_context(
        self, tracking_id: str, event_limit: int = 50
    ) -> Optional[LogisticsContext]:
        """Assemble shipment and timeline for agent consumption.

        Doctest::

            >>> import asyncio, datetime as _dt
            >>> class LogCtxAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         if query.get('entity') == 'shipment':
            ...             return [{'tracking_id': 'CTX', 'status': 'out_for_delivery'}]
            ...         if query.get('entity') == 'events':
            ...             return [{'code': 'OFD', 'occurred_at': _dt.datetime(2024, 3, 1)}]
            ...         return []
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = LogisticsConnector(adapter=LogCtxAdapter())
            >>> ctx = asyncio.run(connector.build_logistics_context('CTX'))
            >>> (ctx.shipment.status, [e.code for e in ctx.events])
            ('out_for_delivery', ['OFD'])
        """
        shipment = await self.get_shipment(tracking_id)
        if shipment is None:
            return None
        events = await self.get_events(tracking_id, limit=event_limit)
        return LogisticsContext(shipment=shipment, events=events)
