"""Opt-in PIM writeback module.

Pushes approved/enriched attributes back to the source PIM system.
Writeback is gated by ``TenantConfig.writeback_enabled`` AND the
per-field ``writeback_eligible`` flag, providing double-opt-in safety.

Circuit-breaker pattern: after ``circuit_breaker_threshold`` consecutive
PIM API failures the manager opens the breaker and rejects further calls
until ``circuit_breaker_reset_seconds`` have elapsed.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------


class WritebackStatus(str, Enum):
    """Outcome of a single writeback operation."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    CONFLICT = "conflict"
    ERROR = "error"
    DRY_RUN = "dry_run"


class WritebackResult(BaseModel):
    """Result of a single field writeback."""

    entity_id: str
    field: str
    status: WritebackStatus
    pim_version: str | None = None
    truth_version: str | None = None
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProductWritebackResult(BaseModel):
    """Aggregate result of writing back all fields for a product."""

    entity_id: str
    results: list[WritebackResult] = Field(default_factory=list)
    total: int = 0
    succeeded: int = 0
    skipped: int = 0
    conflicts: int = 0
    errors: int = 0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TenantConfig(BaseModel):
    """Tenant-level configuration governing writeback behaviour."""

    tenant_id: str
    writeback_enabled: bool = False
    dry_run: bool = False
    rate_limit_per_minute: int = 60
    writeback_fields: list[str] = Field(default_factory=list)
    """Explicit allow-list of field names eligible for writeback.

    An empty list means *all* fields marked ``writeback_eligible=True``
    on the source record are eligible.
    """


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"


# ---------------------------------------------------------------------------
# Circuit breaker
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Lightweight async circuit breaker for PIM API calls."""

    def __init__(
        self,
        threshold: int = 5,
        reset_seconds: float = 60.0,
    ) -> None:
        self._threshold = threshold
        self._reset_seconds = reset_seconds
        self._failures = 0
        self._state = CircuitBreakerState.CLOSED
        self._opened_at: datetime | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    async def record_success(self) -> None:
        async with self._lock:
            self._failures = 0
            self._state = CircuitBreakerState.CLOSED
            self._opened_at = None

    async def record_failure(self) -> None:
        async with self._lock:
            self._failures += 1
            if self._failures >= self._threshold:
                self._state = CircuitBreakerState.OPEN
                self._opened_at = datetime.now(timezone.utc)
                logger.warning(
                    "PIM circuit breaker opened after %d consecutive failures",
                    self._failures,
                )

    async def is_open(self) -> bool:
        async with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return False
            assert self._opened_at is not None
            elapsed = (datetime.now(timezone.utc) - self._opened_at).total_seconds()
            if elapsed >= self._reset_seconds:
                self._state = CircuitBreakerState.CLOSED
                self._failures = 0
                self._opened_at = None
                logger.info("PIM circuit breaker reset after %.0f seconds", elapsed)
                return False
            return True


# ---------------------------------------------------------------------------
# PIM writeback manager
# ---------------------------------------------------------------------------


class PIMWritebackManager:
    """Manages opt-in writeback of enriched attributes to a PIM system.

    Args:
        pim_connector: Object exposing ``push_enrichment(sku, field, value)``
            and ``get_product(sku)`` coroutines (duck-typed, no strict ABC
            required so that mocks are simple).
        truth_store: Object exposing ``get_attributes(entity_id)`` coroutine
            returning a list of attribute dicts with keys ``field``,
            ``value``, ``version``, ``writeback_eligible``.
        audit_store: Object exposing ``record(entry: dict)`` coroutine used
            to persist audit log entries.
        tenant_config: Active tenant configuration.
        circuit_breaker: Optional pre-configured circuit breaker; a default
            one is created when ``None``.
    """

    def __init__(
        self,
        pim_connector: Any,
        truth_store: Any,
        audit_store: Any,
        tenant_config: TenantConfig,
        circuit_breaker: CircuitBreaker | None = None,
    ) -> None:
        self._pim = pim_connector
        self._truth = truth_store
        self._audit = audit_store
        self._config = tenant_config
        self._cb = circuit_breaker or CircuitBreaker()
        self._rate_semaphore = asyncio.Semaphore(self._config.rate_limit_per_minute)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def writeback_attribute(
        self,
        entity_id: str,
        field: str,
        value: Any,
        *,
        truth_version: str | None = None,
    ) -> WritebackResult:
        """Push a single enriched field back to PIM.

        Returns a :class:`WritebackResult` describing the outcome.
        """
        if not self._config.writeback_enabled:
            return WritebackResult(
                entity_id=entity_id,
                field=field,
                status=WritebackStatus.SKIPPED,
                message="Writeback disabled for this tenant",
            )

        if not self._is_field_eligible(field):
            return WritebackResult(
                entity_id=entity_id,
                field=field,
                status=WritebackStatus.SKIPPED,
                message=f"Field '{field}' not in writeback allow-list",
            )

        if self._config.dry_run:
            result = WritebackResult(
                entity_id=entity_id,
                field=field,
                status=WritebackStatus.DRY_RUN,
                truth_version=truth_version,
                message="Dry-run: no write performed",
            )
            await self._record_audit(result, value)
            return result

        # Conflict detection
        conflict = await self._detect_conflict(entity_id, field, truth_version)
        if conflict:
            result = WritebackResult(
                entity_id=entity_id,
                field=field,
                status=WritebackStatus.CONFLICT,
                truth_version=truth_version,
                message=conflict,
            )
            await self._record_audit(result, value)
            return result

        return await self._execute_write(entity_id, field, value, truth_version)

    async def writeback_product(self, entity_id: str) -> ProductWritebackResult:
        """Push all eligible truth attributes for a product to PIM."""
        summary = ProductWritebackResult(entity_id=entity_id)

        attributes = await self._truth.get_attributes(entity_id)
        summary.total = len(attributes)

        tasks = [
            self._writeback_one_attr(entity_id, attr)
            for attr in attributes
            if attr.get("writeback_eligible", False)
        ]
        results: list[WritebackResult] = await asyncio.gather(*tasks)

        for r in results:
            summary.results.append(r)
            if r.status == WritebackStatus.SUCCESS:
                summary.succeeded += 1
            elif r.status in (WritebackStatus.SKIPPED, WritebackStatus.DRY_RUN):
                summary.skipped += 1
            elif r.status == WritebackStatus.CONFLICT:
                summary.conflicts += 1
            else:
                summary.errors += 1

        return summary

    async def batch_writeback(self, entity_ids: list[str]) -> list[ProductWritebackResult]:
        """Bulk writeback for multiple products."""
        tasks = [self.writeback_product(eid) for eid in entity_ids]
        return list(await asyncio.gather(*tasks))

    async def dry_run(self, entity_id: str) -> ProductWritebackResult:
        """Preview what would be written back without performing any writes.

        Temporarily forces dry-run mode for the duration of the preview.
        The tenant config is *not* mutated; a shadow copy is used instead.
        """
        original_dry_run = self._config.dry_run
        original_enabled = self._config.writeback_enabled
        self._config = TenantConfig(
            **{
                **self._config.model_dump(),
                "dry_run": True,
                "writeback_enabled": True,
            }
        )
        try:
            return await self.writeback_product(entity_id)
        finally:
            self._config = TenantConfig(
                **{
                    **self._config.model_dump(),
                    "dry_run": original_dry_run,
                    "writeback_enabled": original_enabled,
                }
            )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_field_eligible(self, field: str) -> bool:
        """Return True when the field passes the tenant allow-list check."""
        if not self._config.writeback_fields:
            return True
        return field in self._config.writeback_fields

    async def _detect_conflict(
        self,
        entity_id: str,
        field: str,
        truth_version: str | None,
    ) -> str | None:
        """Return a conflict message if PIM version is ahead of truth version."""
        if truth_version is None:
            return None
        try:
            product = await self._pim.get_product(entity_id)
            if product is None:
                return None
            pim_version = getattr(product, "last_modified", None)
            if pim_version is None:
                return None
            pim_ts = pim_version.isoformat() if isinstance(pim_version, datetime) else str(pim_version)
            truth_ts = truth_version
            if pim_ts > truth_ts:
                return (
                    f"PIM version ({pim_ts}) is newer than truth version ({truth_ts}); "
                    "manual review required"
                )
        except Exception as exc:
            logger.warning("Conflict detection failed for %s/%s: %s", entity_id, field, exc)
        return None

    async def _execute_write(
        self,
        entity_id: str,
        field: str,
        value: Any,
        truth_version: str | None,
    ) -> WritebackResult:
        """Call PIM connector with circuit-breaker and rate-limiting guards."""
        if await self._cb.is_open():
            result = WritebackResult(
                entity_id=entity_id,
                field=field,
                status=WritebackStatus.ERROR,
                truth_version=truth_version,
                message="Circuit breaker is open; PIM API unavailable",
            )
            await self._record_audit(result, value)
            return result

        async with self._rate_semaphore:
            try:
                await self._pim.push_enrichment(entity_id, field, value)
                await self._cb.record_success()
                result = WritebackResult(
                    entity_id=entity_id,
                    field=field,
                    status=WritebackStatus.SUCCESS,
                    truth_version=truth_version,
                    message="Writeback succeeded",
                )
            except Exception as exc:
                await self._cb.record_failure()
                logger.error(
                    "PIM writeback failed for %s/%s: %s", entity_id, field, exc
                )
                result = WritebackResult(
                    entity_id=entity_id,
                    field=field,
                    status=WritebackStatus.ERROR,
                    truth_version=truth_version,
                    message=str(exc),
                )

        await self._record_audit(result, value)
        return result

    async def _writeback_one_attr(
        self, entity_id: str, attr: dict
    ) -> WritebackResult:
        return await self.writeback_attribute(
            entity_id,
            field=attr["field"],
            value=attr["value"],
            truth_version=attr.get("version"),
        )

    async def _record_audit(self, result: WritebackResult, value: Any) -> None:
        """Persist an audit log entry for the writeback operation."""
        entry = {
            "entity_id": result.entity_id,
            "field": result.field,
            "value": value,
            "status": result.status.value,
            "message": result.message,
            "pim_version": result.pim_version,
            "truth_version": result.truth_version,
            "tenant_id": self._config.tenant_id,
            "timestamp": result.timestamp.isoformat(),
        }
        try:
            await self._audit.record(entry)
        except Exception as exc:
            logger.error("Failed to record writeback audit entry: %s", exc)
