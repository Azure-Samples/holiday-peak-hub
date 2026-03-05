"""Webhook routes for external connector synchronization."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from crud_service.config import get_settings
from crud_service.consumers import get_connector_sync_consumer
from fastapi import APIRouter, HTTPException, status
from holiday_peak_lib.events import parse_connector_event
from pydantic import BaseModel, Field

router = APIRouter()
settings = get_settings()
connector_sync_consumer = get_connector_sync_consumer()


class ConnectorReplayRequest(BaseModel):
    """Replay request payload for dead-letter events."""

    limit: int = Field(default=100, ge=1, le=1000)


@router.post("/webhooks/connectors/replay/{dead_letter_id}")
async def replay_dead_letter(dead_letter_id: str):
    """Replay a single dead-letter connector event by ID."""

    if not settings.connector_sync_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connector synchronization is disabled",
        )

    replayed = await connector_sync_consumer.replay_dead_letter(dead_letter_id)
    if not replayed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dead-letter event not found"
        )

    return {"status": "replayed", "dead_letter_id": dead_letter_id}


@router.post("/webhooks/connectors/replay")
async def replay_dead_letters(request: ConnectorReplayRequest):
    """Replay pending dead-letter events in ascending failure order."""

    if not settings.connector_sync_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connector synchronization is disabled",
        )

    result = await connector_sync_consumer.replay_unreplayed(limit=request.limit)
    return {"status": "completed", **result}


@router.post("/webhooks/connectors/{source_system}", status_code=status.HTTP_202_ACCEPTED)
async def connector_webhook(source_system: str, payload: dict[str, Any]):
    """Accept connector webhook payload and enqueue for Event Hub processing."""

    if not settings.connector_sync_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Connector synchronization is disabled",
        )

    event_payload = dict(payload)
    event_payload["source_system"] = source_system
    event_payload.setdefault("occurred_at", datetime.now(UTC).isoformat())

    try:
        event = parse_connector_event(event_payload)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid connector event payload: {exc}",
        ) from exc

    event_id = await connector_sync_consumer.ingest_webhook_event(event.model_dump(mode="json"))
    return {
        "status": "accepted",
        "event_id": event_id,
        "event_type": event.event_type,
    }
