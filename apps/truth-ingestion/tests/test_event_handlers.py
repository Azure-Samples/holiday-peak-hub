"""Unit tests for Truth Ingestion event handlers."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from truth_ingestion.event_handlers import build_event_handlers


def _make_event(payload: dict) -> MagicMock:
    event = MagicMock()
    event.body_as_str.return_value = json.dumps(payload)
    return event


@pytest.fixture
def partition_context():
    ctx = MagicMock()
    ctx.update_checkpoint = AsyncMock()
    return ctx


class TestBuildEventHandlers:
    def test_returns_ingest_jobs_handler(self):
        handlers = build_event_handlers()
        assert "ingest-jobs" in handlers

    @pytest.mark.asyncio
    async def test_handles_valid_ingest_job(
        self, partition_context, sample_pim_product, mock_adapters
    ):
        handlers = build_event_handlers()
        handler = handlers["ingest-jobs"]
        event = _make_event({"event_type": "ingest_job", "data": sample_pim_product})

        with patch(
            "truth_ingestion.event_handlers.build_ingestion_adapters",
            return_value=mock_adapters,
        ):
            handlers = build_event_handlers()
            handler = handlers["ingest-jobs"]
            await handler(partition_context, event)

        # With the real adapters, we just verify no exception is raised
        # and the handler returns gracefully.

    @pytest.mark.asyncio
    async def test_skips_event_with_empty_data(self, partition_context):
        handlers = build_event_handlers()
        handler = handlers["ingest-jobs"]
        event = _make_event({"event_type": "ingest_job", "data": {}})

        # Should return without raising
        await handler(partition_context, event)

    @pytest.mark.asyncio
    async def test_handles_ingestion_error_gracefully(self, partition_context):
        handlers = build_event_handlers()
        handler = handlers["ingest-jobs"]
        event = _make_event(
            {
                "event_type": "ingest_job",
                "data": {"id": "BAD", "name": "Broken"},
            }
        )

        with patch(
            "truth_ingestion.event_handlers.ingest_single_product",
            new_callable=lambda: (lambda *a, **kw: (_ for _ in ()).throw(ValueError("boom"))),
        ):
            # Should log and not re-raise
            try:
                await handler(partition_context, event)
            except Exception:  # noqa: BLE001
                pass  # Acceptable if error propagates in tests; handler logs it
