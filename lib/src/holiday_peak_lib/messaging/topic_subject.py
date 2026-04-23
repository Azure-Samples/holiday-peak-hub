"""Observer pattern wrapper for Event Hub topic publish/subscribe.

Agents register as observers on named topics. Publishing and subscribing
are delegated to the existing EventPublisher and EventHubSubscriber from
holiday_peak_lib.utils.event_hub. This module adds:
  - Named topic registration with type-safe handler binding
  - Observer lifecycle management (attach/detach/notify)
  - Integration with the AgentAsyncContract for self-description
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

ObserverHandler = Callable[[dict[str, Any]], Awaitable[None]]


class TopicSubject:
    """Observable subject for a single Event Hub topic.

    Each instance represents one named topic. Handlers (observers) can be
    attached and detached. ``notify`` fans out to all observers locally,
    while ``publish`` delegates to an ``EventPublisher`` for Event Hub delivery.
    """

    _registry: dict[str, TopicSubject] = {}

    def __init__(
        self,
        topic_name: str,
        *,
        event_hub_name: str | None = None,
    ) -> None:
        self.topic_name = topic_name
        self.event_hub_name = event_hub_name or topic_name
        self.observers: list[ObserverHandler] = []
        TopicSubject._registry[topic_name] = self

    def attach(self, handler: ObserverHandler) -> None:
        """Register an observer handler (idempotent)."""
        if handler not in self.observers:
            self.observers.append(handler)

    def detach(self, handler: ObserverHandler) -> None:
        """Remove an observer handler if present."""
        try:
            self.observers.remove(handler)
        except ValueError:
            return  # Handler not attached — idempotent detach

    async def notify(self, event_data: dict[str, Any]) -> None:
        """Fan out *event_data* to every attached observer."""
        for handler in list(self.observers):
            await handler(event_data)

    async def publish(
        self,
        event_data: dict[str, Any],
        *,
        publisher: Any | None = None,
    ) -> None:
        """Publish *event_data* to Event Hub via the given publisher.

        Parameters
        ----------
        event_data:
            The event payload to publish.
        publisher:
            An ``EventPublisher``-compatible object exposing an async
            ``send(event_hub_name, data)`` method.  Imported lazily to
            avoid requiring Azure SDK credentials at module-load time.
        """
        if publisher is not None:
            await publisher.send(self.event_hub_name, event_data)
        await self.notify(event_data)

    @classmethod
    def get_all_topics(cls) -> dict[str, TopicSubject]:
        """Return the class-level registry of all instantiated topics."""
        return dict(cls._registry)

    @classmethod
    def clear_registry(cls) -> None:
        """Reset the topic registry (primarily for testing)."""
        cls._registry.clear()
