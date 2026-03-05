"""Repositories for connector synchronization state."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from crud_service.repositories.base import BaseRepository


class ProcessedConnectorEventRepository(BaseRepository):
    """Stores processed connector event fingerprints for idempotency."""

    def __init__(self) -> None:
        super().__init__(container_name="connector_processed_events")

    @staticmethod
    def _event_key(event_id: str, source_system: str) -> str:
        return f"{source_system}:{event_id}"

    async def is_processed(self, event_id: str, source_system: str) -> bool:
        """Check whether an event has already been processed."""

        return await self.get_by_id(self._event_key(event_id, source_system)) is not None

    async def mark_processed(self, *, event_id: str, source_system: str, event_type: str) -> None:
        """Persist a processed event marker."""

        await self.update(
            {
                "id": self._event_key(event_id, source_system),
                "event_id": event_id,
                "source_system": source_system,
                "event_type": event_type,
                "processed_at": datetime.now(UTC).isoformat(),
            }
        )


class DeadLetterConnectorEventRepository(BaseRepository):
    """Stores connector events that failed processing."""

    def __init__(self) -> None:
        super().__init__(container_name="connector_dead_letter_events")

    async def add_failed_event(
        self,
        *,
        event_payload: dict,
        error: str,
    ) -> dict:
        """Store a failed event for triage and replay."""

        failed = {
            "id": str(uuid4()),
            "event_payload": event_payload,
            "error": error,
            "failed_at": datetime.now(UTC).isoformat(),
            "replayed": False,
        }
        await self.create(failed)
        return failed

    async def mark_replayed(self, dead_letter_id: str) -> None:
        """Mark a dead-letter record as replayed."""

        item = await self.get_by_id(dead_letter_id)
        if not item:
            return
        item["replayed"] = True
        item["replayed_at"] = datetime.now(UTC).isoformat()
        await self.update(item)

    async def list_unreplayed(self, limit: int = 100) -> list[dict]:
        """List dead-letter records pending replay."""

        return await self.query(
            query=(
                "SELECT * FROM c "
                "WHERE c.replayed = @replayed OR NOT IS_DEFINED(c.replayed) "
                "ORDER BY c.failed_at ASC OFFSET 0 LIMIT @limit"
            ),
            parameters=[
                {"name": "@replayed", "value": False},
                {"name": "@limit", "value": limit},
            ],
        )
