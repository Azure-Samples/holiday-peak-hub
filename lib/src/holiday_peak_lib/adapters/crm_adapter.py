"""CRM connector and canonical CRM interfaces.

Transforms upstream CRM entities into agent-ready context to power customer
support, engagement, and revenue motions described in the business summary.
All helpers include doctests to demonstrate normalization and concurrency-safe
mapping.
"""

from typing import Optional

from holiday_peak_lib.adapters.base import BaseAdapter, BaseConnector
from holiday_peak_lib.schemas.crm import CRMAccount, CRMContact, CRMContext, CRMInteraction


class CRMConnector(BaseConnector):
    """Connector for CRM platforms that normalizes adapter data.

    The connector consumes any ``BaseAdapter`` implementation and exposes
    canonical, agent-ready models. All mapping is async and bounded by a
    semaphore so multiple payloads can be normalized concurrently without
    overwhelming the event loop.

    Doctest example using a trivial in-memory adapter::

        >>> import asyncio
        >>> from typing import Iterable
        >>> from holiday_peak_lib.adapters.base import BaseAdapter
        >>> class FakeAdapter(BaseAdapter):
        ...     async def _connect_impl(self, **kwargs):
        ...         return None
        ...     async def _fetch_impl(self, query: dict[str, object]) -> Iterable[dict[str, object]]:
        ...         if query.get("entity") == "contact":
        ...             return [{"id": "c1", "contact_id": "c1", "email": "a@example.com"}]
        ...         return []
        ...     async def _upsert_impl(self, payload: dict[str, object]):
        ...         return payload
        ...     async def _delete_impl(self, identifier: str) -> bool:
        ...         return True
        >>> connector = CRMConnector(adapter=FakeAdapter())
        >>> asyncio.run(connector.get_contact("c1")).email
        'a@example.com'
    """

    def __init__(self, adapter: Optional[BaseAdapter] = None, map_concurrency: int = 10) -> None:
        super().__init__(adapter=adapter, map_concurrency=map_concurrency)

    async def get_contact(self, contact_id: str) -> Optional[CRMContact]:
        """Fetch and normalize a single contact by identifier.

        :param contact_id: External CRM contact identifier.
        :returns: Canonical ``CRMContact`` or ``None`` if not found.

        Doctest::

            >>> import asyncio
            >>> class OneContactAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         if query.get('id') == 'c-42':
            ...             return [{'contact_id': 'c-42', 'email': 'u@example.com'}]
            ...         return []
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = CRMConnector(adapter=OneContactAdapter())
            >>> asyncio.run(connector.get_contact('c-42')).contact_id
            'c-42'
        """
        record = await self._fetch_first(entity="contact", id=contact_id)
        return await self._map_single(CRMContact, record)

    async def get_account(self, account_id: str) -> Optional[CRMAccount]:
        """Fetch and normalize a single account by identifier.

        Process:
        - Call adapter ``fetch`` with the account query.
        - Take the first record, if present.
        - Validate and coerce into ``CRMAccount``.

        Doctest::

            >>> import asyncio
            >>> class OneAccountAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         if query.get('id') == 'a-1':
            ...             return [{'account_id': 'a-1', 'name': 'Acme'}]
            ...         return []
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = CRMConnector(adapter=OneAccountAdapter())
            >>> asyncio.run(connector.get_account('a-1')).name
            'Acme'
        """
        record = await self._fetch_first(entity="account", id=account_id)
        return await self._map_single(CRMAccount, record)

    async def get_interactions(
        self, contact_id: str, limit: int = 20
    ) -> list[CRMInteraction]:
        """Fetch and normalize recent interactions for a contact.

        Process:
        - Query adapter for interaction records by contact.
        - Stream results through bounded async mapping.
        - Return a list of validated ``CRMInteraction`` objects.

        Doctest::

            >>> import asyncio, datetime as _dt
            >>> class InteractionAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         return [{
            ...             'interaction_id': 'i1',
            ...             'contact_id': query.get('contact_id'),
            ...             'channel': 'email',
            ...             'occurred_at': _dt.datetime(2024, 1, 1)
            ...         }]
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = CRMConnector(adapter=InteractionAdapter())
            >>> interactions = asyncio.run(connector.get_interactions('c-9', limit=5))
            >>> len(interactions)
            1
        """
        records = await self._fetch_many(
            entity="interaction", contact_id=contact_id, limit=limit
        )
        return await self._map_many(CRMInteraction, records)

    async def build_contact_context(
        self, contact_id: str, interaction_limit: int = 20
    ) -> Optional[CRMContext]:
        """Assemble an agent-ready context containing contact, account, and interactions.

        Process:
        - Resolve the contact; bail out if missing.
        - Resolve the linked account when available.
        - Retrieve and normalize recent interactions.
        - Return aggregated ``CRMContext`` suitable for agent prompts.

        Doctest::

            >>> import asyncio, datetime as _dt
            >>> class ContextAdapter(BaseAdapter):
            ...     async def _connect_impl(self, **kwargs):
            ...         return None
            ...     async def _fetch_impl(self, query):
            ...         if query.get('entity') == 'contact':
            ...             return [{'contact_id': 'c-1', 'account_id': 'a-1'}]
            ...         if query.get('entity') == 'account':
            ...             return [{'account_id': 'a-1', 'name': 'Acme'}]
            ...         if query.get('entity') == 'interaction':
            ...             return [{
            ...                 'interaction_id': 'i-1',
            ...                 'contact_id': query.get('contact_id'),
            ...                 'channel': 'phone',
            ...                 'occurred_at': _dt.datetime(2024, 2, 1)
            ...             }]
            ...         return []
            ...     async def _upsert_impl(self, payload):
            ...         return payload
            ...     async def _delete_impl(self, identifier):
            ...         return True
            >>> connector = CRMConnector(adapter=ContextAdapter())
            >>> ctx = asyncio.run(connector.build_contact_context('c-1'))
            >>> (ctx.contact.contact_id, ctx.account.name, len(ctx.interactions))
            ('c-1', 'Acme', 1)
        """
        contact = await self.get_contact(contact_id)
        if contact is None:
            return None

        account = (
            await self.get_account(contact.account_id)
            if contact.account_id is not None
            else None
        )
        interactions = await self.get_interactions(
            contact_id=contact.contact_id, limit=interaction_limit
        )
        return CRMContext(contact=contact, account=account, interactions=interactions)
