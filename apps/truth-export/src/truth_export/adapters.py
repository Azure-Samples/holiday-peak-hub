"""Adapters for the truth-export service."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from .schemas_compat import ProductStyle, TruthAttribute


@dataclass
class MockTruthStoreAdapter:
    """In-memory stub that simulates the Cosmos DB truth store.

    Replace with a real Cosmos DB adapter in production environments.
    """

    _styles: dict[str, ProductStyle] = field(default_factory=dict)
    _attributes: dict[str, list[TruthAttribute]] = field(default_factory=dict)
    _results: list[dict[str, Any]] = field(default_factory=list)

    async def get_product_style(self, style_id: str) -> Optional[ProductStyle]:
        return self._styles.get(style_id)

    async def get_truth_attributes(self, style_id: str) -> list[TruthAttribute]:
        return self._attributes.get(style_id, [])

    async def get_protocol_mapping(self, _protocol: str) -> dict[str, Any]:
        """Return a stub field-mapping config for *protocol*."""
        return {"protocol_version": "1.0"}

    async def save_export_result(self, result: dict[str, Any]) -> None:
        self._results.append(result)

    async def save_audit_event(self, event: dict[str, Any]) -> None:
        pass  # No-op in mock

    # ------------------------------------------------------------------
    # Seeding helpers (useful in tests)
    # ------------------------------------------------------------------

    def seed_style(self, style: ProductStyle) -> None:
        self._styles[style.id] = style

    def seed_attributes(self, style_id: str, attributes: list[TruthAttribute]) -> None:
        self._attributes[style_id] = attributes


@dataclass
class ExportJobTracker:
    """In-memory export job status tracker."""

    _jobs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create(self, entity_id: str, protocol: str, partner_id: Optional[str] = None) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "entity_id": entity_id,
            "protocol": protocol,
            "partner_id": partner_id,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return job_id

    def update(self, job_id: str, status: str, **extra: Any) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            self._jobs[job_id].update(extra)

    def get(self, job_id: str) -> Optional[dict[str, Any]]:
        return self._jobs.get(job_id)

    def all_jobs(self) -> list[dict[str, Any]]:
        return list(self._jobs.values())


@dataclass
class TruthExportAdapters:
    """Container for truth-export adapters."""

    truth_store: MockTruthStoreAdapter
    job_tracker: ExportJobTracker


def build_truth_export_adapters() -> TruthExportAdapters:
    """Create the default adapter bundle for the truth-export service."""
    return TruthExportAdapters(
        truth_store=MockTruthStoreAdapter(),
        job_tracker=ExportJobTracker(),
    )
