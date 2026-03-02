"""Event Hub helpers for truth-layer job queues (Issue #94).

Provides:
- ``TRUTH_LAYER_TOPICS`` — canonical names for the five job queues.
- :class:`TruthJobPublisher` — thin async publisher that sends JSON events
  to a truth-layer Event Hub topic.
- :func:`build_truth_layer_subscriptions` — convenience factory that
  returns :class:`~holiday_peak_lib.utils.event_hub.EventHubSubscription`
  objects for all (or a subset of) truth-layer topics.
"""

from __future__ import annotations

import json
from typing import Any, Iterable

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient

from holiday_peak_lib.utils.event_hub import EventHubSubscription

# ---------------------------------------------------------------------------
# Canonical topic names
# ---------------------------------------------------------------------------

TRUTH_LAYER_TOPICS: dict[str, str] = {
    "ingest": "ingest-jobs",
    "gap": "gap-jobs",
    "enrichment": "enrichment-jobs",
    "writeback": "writeback-jobs",
    "export": "export-jobs",
}


# ---------------------------------------------------------------------------
# Publisher
# ---------------------------------------------------------------------------


class TruthJobPublisher:
    """Async publisher for truth-layer job events.

    Parameters
    ----------
    connection_string:
        Azure Event Hubs namespace connection string.
    eventhub_name:
        Target Event Hub topic (one of :data:`TRUTH_LAYER_TOPICS` values).
    producer_factory:
        Optional factory override for testing — receives ``connection_string``
        and ``eventhub_name`` and must return an
        :class:`azure.eventhub.aio.EventHubProducerClient`.

    Example
    -------
    >>> from unittest.mock import AsyncMock, MagicMock
    >>> producer = MagicMock()
    >>> pub = TruthJobPublisher(
    ...     connection_string="Endpoint=sb://t/;SharedAccessKeyName=k;SharedAccessKey=v",
    ...     eventhub_name="ingest-jobs",
    ...     producer_factory=lambda cs, eh: producer,
    ... )
    >>> pub._eventhub_name
    'ingest-jobs'
    """

    def __init__(
        self,
        *,
        connection_string: str,
        eventhub_name: str,
        producer_factory: Any = None,
    ) -> None:
        self._connection_string = connection_string
        self._eventhub_name = eventhub_name
        self._producer_factory = producer_factory or self._default_producer_factory

    async def publish(self, event_type: str, data: dict[str, Any]) -> None:
        """Send a single event to the configured Event Hub topic.

        Parameters
        ----------
        event_type:
            Logical event type string (e.g. ``"ingest_requested"``).
        data:
            Arbitrary dict payload that will be serialised to JSON.
        """
        payload = json.dumps({"event_type": event_type, "data": data})
        producer: EventHubProducerClient = self._producer_factory(
            self._connection_string, self._eventhub_name
        )
        async with producer:
            batch = await producer.create_batch()
            batch.add(EventData(payload))
            await producer.send_batch(batch)

    @staticmethod
    def _default_producer_factory(
        connection_string: str, eventhub_name: str
    ) -> EventHubProducerClient:
        return EventHubProducerClient.from_connection_string(
            conn_str=connection_string, eventhub_name=eventhub_name
        )


# ---------------------------------------------------------------------------
# Subscription builder
# ---------------------------------------------------------------------------


def build_truth_layer_subscriptions(
    *,
    topics: Iterable[str] | None = None,
    consumer_group: str = "$Default",
) -> list[EventHubSubscription]:
    """Return :class:`~holiday_peak_lib.utils.event_hub.EventHubSubscription`
    objects for truth-layer job topics.

    Parameters
    ----------
    topics:
        Iterable of logical topic keys (``"ingest"``, ``"gap"``, etc.) or
        raw Event Hub names. Pass ``None`` to subscribe to **all** five topics.
    consumer_group:
        Azure Event Hubs consumer group (default ``"$Default"``).
    """
    if topics is None:
        selected_names = list(TRUTH_LAYER_TOPICS.values())
    else:
        selected_names = [
            TRUTH_LAYER_TOPICS.get(t, t) for t in topics
        ]

    return [
        EventHubSubscription(eventhub_name=name, consumer_group=consumer_group)
        for name in selected_names
    ]
