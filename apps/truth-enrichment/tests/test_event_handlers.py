"""Unit tests for Truth Enrichment event handlers."""

from __future__ import annotations

from truth_enrichment.event_handlers import build_event_handlers


def test_build_event_handlers_includes_enrichment_jobs() -> None:
    handlers = build_event_handlers()
    assert "enrichment-jobs" in handlers
