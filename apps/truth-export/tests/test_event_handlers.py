"""Tests for truth-export event handlers."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from holiday_peak_lib.integrations import (
    ProductWritebackResult,
    WritebackResult,
    WritebackStatus,
)
from truth_export.adapters import build_truth_export_adapters
from truth_export.event_handlers import build_event_handlers
from truth_export.schemas_compat import ProductStyle


class _StubWritebackManager:
    async def dry_run(self, entity_id: str) -> ProductWritebackResult:
        return await self.writeback_product(entity_id)

    async def writeback_product(self, entity_id: str) -> ProductWritebackResult:
        return ProductWritebackResult(
            entity_id=entity_id,
            total=1,
            succeeded=1,
            results=[
                WritebackResult(
                    entity_id=entity_id,
                    field="title",
                    status=WritebackStatus.SUCCESS,
                    message="Writeback succeeded",
                )
            ],
        )


@pytest.mark.asyncio
async def test_build_event_handlers_includes_export_jobs() -> None:
    handlers = build_event_handlers()
    assert "export-jobs" in handlers


@pytest.mark.asyncio
async def test_export_jobs_hitl_approval_triggers_writeback_path() -> None:
    adapters = build_truth_export_adapters()
    adapters.writeback_manager = _StubWritebackManager()

    handlers = build_event_handlers(adapters=adapters)
    handler = handlers["export-jobs"]

    event = MagicMock()
    event.body_as_str.return_value = json.dumps(
        {
            "event_type": "hitl.approved",
            "source": "truth-hitl",
            "data": {
                "entity_id": "STYLE-001",
                "protocol": "pim",
                "status": "approved",
            },
        }
    )

    await handler(MagicMock(), event)

    assert adapters.truth_store._results  # pylint: disable=protected-access
    assert adapters.truth_store._audit_events  # pylint: disable=protected-access
    assert (
        adapters.truth_store._audit_events[-1]["details"]["writeback_status"]
        == "completed"  # pylint: disable=protected-access
    )


@pytest.mark.asyncio
async def test_export_jobs_protocol_export_uses_existing_path() -> None:
    adapters = build_truth_export_adapters()

    style = ProductStyle(
        id="STYLE-100",
        brand="Contoso",
        modelName="Explorer",
        categoryId="footwear",
    )
    adapters.truth_store.seed_style(style)

    handlers = build_event_handlers(adapters=adapters)
    handler = handlers["export-jobs"]

    event = MagicMock()
    event.body_as_str.return_value = json.dumps(
        {
            "event_type": "export.requested",
            "data": {
                "entity_id": "STYLE-100",
                "protocol": "ucp",
            },
        }
    )

    await handler(MagicMock(), event)

    assert adapters.truth_store._results  # pylint: disable=protected-access
    assert (
        adapters.truth_store._results[-1]["protocol"] == "ucp"
    )  # pylint: disable=protected-access
