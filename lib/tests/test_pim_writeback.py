"""Unit tests for the PIM writeback module."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from holiday_peak_lib.integrations.pim_writeback import (
    CircuitBreaker,
    CircuitBreakerState,
    PIMWritebackManager,
    TenantConfig,
    WritebackStatus,
)

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_config(**kwargs) -> TenantConfig:
    defaults = dict(
        tenant_id="tenant-1",
        writeback_enabled=True,
        dry_run=False,
        rate_limit_per_minute=10,
    )
    defaults.update(kwargs)
    return TenantConfig(**defaults)


def _make_manager(
    pim=None,
    truth=None,
    audit=None,
    config=None,
    circuit_breaker=None,
) -> PIMWritebackManager:
    pim = pim or AsyncMock()
    truth = truth or AsyncMock()
    audit = audit or AsyncMock()
    config = config or _make_config()
    return PIMWritebackManager(
        pim_connector=pim,
        truth_store=truth,
        audit_store=audit,
        tenant_config=config,
        circuit_breaker=circuit_breaker,
    )


def _sample_attributes(fields=("color", "size")) -> list[dict]:
    return [
        {
            "field": f,
            "value": f"val-{f}",
            "version": "2024-01-01T00:00:00",
            "writeback_eligible": True,
        }
        for f in fields
    ]


# ---------------------------------------------------------------------------
# TenantConfig tests
# ---------------------------------------------------------------------------


class TestTenantConfig:
    def test_defaults_writeback_disabled(self):
        cfg = TenantConfig(tenant_id="t1")
        assert cfg.writeback_enabled is False
        assert cfg.dry_run is False

    def test_explicit_enable(self):
        cfg = TenantConfig(tenant_id="t1", writeback_enabled=True)
        assert cfg.writeback_enabled is True

    def test_writeback_fields_empty_by_default(self):
        cfg = TenantConfig(tenant_id="t1")
        assert cfg.writeback_fields == []


# ---------------------------------------------------------------------------
# CircuitBreaker tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCircuitBreaker:
    async def test_starts_closed(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitBreakerState.CLOSED
        assert await cb.is_open() is False

    async def test_opens_after_threshold(self):
        cb = CircuitBreaker(threshold=3)
        for _ in range(3):
            await cb.record_failure()
        assert cb.state == CircuitBreakerState.OPEN
        assert await cb.is_open() is True

    async def test_does_not_open_below_threshold(self):
        cb = CircuitBreaker(threshold=3)
        for _ in range(2):
            await cb.record_failure()
        assert cb.state == CircuitBreakerState.CLOSED
        assert await cb.is_open() is False

    async def test_success_resets_failures(self):
        cb = CircuitBreaker(threshold=3)
        await cb.record_failure()
        await cb.record_failure()
        await cb.record_success()
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb._failures == 0

    async def test_resets_after_timeout(self):
        cb = CircuitBreaker(threshold=1, reset_seconds=0.0)
        await cb.record_failure()
        assert await cb.is_open() is False  # reset_seconds=0 means instant reset


# ---------------------------------------------------------------------------
# writeback_attribute tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestWritebackAttribute:
    async def test_skips_when_disabled(self):
        mgr = _make_manager(config=_make_config(writeback_enabled=False))
        result = await mgr.writeback_attribute("sku-1", "color", "red")
        assert result.status == WritebackStatus.SKIPPED
        assert "disabled" in result.message.lower()

    async def test_skips_field_not_in_allow_list(self):
        cfg = _make_config(writeback_fields=["size"])
        mgr = _make_manager(config=cfg)
        result = await mgr.writeback_attribute("sku-1", "color", "red")
        assert result.status == WritebackStatus.SKIPPED
        assert "allow-list" in result.message

    async def test_all_fields_eligible_when_allow_list_empty(self):
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        mgr = _make_manager(pim=pim, config=_make_config(writeback_fields=[]))
        result = await mgr.writeback_attribute("sku-1", "color", "red")
        assert result.status == WritebackStatus.SUCCESS

    async def test_dry_run_returns_dry_run_status(self):
        cfg = _make_config(dry_run=True)
        audit = AsyncMock()
        mgr = _make_manager(config=cfg, audit=audit)
        result = await mgr.writeback_attribute("sku-1", "color", "red")
        assert result.status == WritebackStatus.DRY_RUN
        audit.record.assert_awaited_once()

    async def test_successful_write(self):
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        pim.push_enrichment = AsyncMock()
        audit = AsyncMock()
        mgr = _make_manager(pim=pim, audit=audit)
        result = await mgr.writeback_attribute("sku-1", "color", "red")
        assert result.status == WritebackStatus.SUCCESS
        pim.push_enrichment.assert_awaited_once_with("sku-1", "color", "red")
        audit.record.assert_awaited_once()

    async def test_conflict_detected_when_pim_version_newer(self):
        product_mock = MagicMock()
        product_mock.last_modified = datetime(2025, 1, 2, tzinfo=timezone.utc)
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=product_mock)
        mgr = _make_manager(pim=pim)
        result = await mgr.writeback_attribute(
            "sku-1", "color", "red", truth_version="2025-01-01T00:00:00"
        )
        assert result.status == WritebackStatus.CONFLICT
        assert "newer" in result.message

    async def test_no_conflict_when_truth_version_none(self):
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        mgr = _make_manager(pim=pim)
        result = await mgr.writeback_attribute("sku-1", "color", "red", truth_version=None)
        assert result.status == WritebackStatus.SUCCESS

    async def test_pim_error_records_failure(self):
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        pim.push_enrichment = AsyncMock(side_effect=RuntimeError("PIM down"))
        audit = AsyncMock()
        mgr = _make_manager(pim=pim, audit=audit)
        result = await mgr.writeback_attribute("sku-1", "color", "red")
        assert result.status == WritebackStatus.ERROR
        assert "PIM down" in result.message
        audit.record.assert_awaited_once()

    async def test_circuit_breaker_open_returns_error(self):
        cb = CircuitBreaker(threshold=1)
        await cb.record_failure()
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        mgr = _make_manager(pim=pim, circuit_breaker=cb)
        result = await mgr.writeback_attribute("sku-1", "color", "red")
        assert result.status == WritebackStatus.ERROR
        assert "circuit breaker" in result.message.lower()

    async def test_audit_failure_does_not_propagate(self):
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        pim.push_enrichment = AsyncMock()
        audit = AsyncMock()
        audit.record = AsyncMock(side_effect=Exception("audit store unavailable"))
        mgr = _make_manager(pim=pim, audit=audit)
        # Should not raise even if audit store is broken
        result = await mgr.writeback_attribute("sku-1", "color", "red")
        assert result.status == WritebackStatus.SUCCESS


# ---------------------------------------------------------------------------
# writeback_product tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestWritebackProduct:
    async def test_returns_summary_for_all_eligible_attrs(self):
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        pim.push_enrichment = AsyncMock()
        truth = AsyncMock()
        truth.get_attributes = AsyncMock(return_value=_sample_attributes(["color", "size"]))
        mgr = _make_manager(pim=pim, truth=truth)
        summary = await mgr.writeback_product("sku-1")
        assert summary.entity_id == "sku-1"
        assert summary.total == 2
        assert summary.succeeded == 2
        assert len(summary.results) == 2

    async def test_skips_non_eligible_attrs(self):
        attrs = [
            {"field": "color", "value": "red", "version": None, "writeback_eligible": False},
            {"field": "size", "value": "M", "version": None, "writeback_eligible": True},
        ]
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        pim.push_enrichment = AsyncMock()
        truth = AsyncMock()
        truth.get_attributes = AsyncMock(return_value=attrs)
        mgr = _make_manager(pim=pim, truth=truth)
        summary = await mgr.writeback_product("sku-1")
        assert summary.total == 2
        assert summary.succeeded == 1
        assert len(summary.results) == 1

    async def test_counts_errors_correctly(self):
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        pim.push_enrichment = AsyncMock(side_effect=RuntimeError("fail"))
        truth = AsyncMock()
        truth.get_attributes = AsyncMock(return_value=_sample_attributes(["color"]))
        mgr = _make_manager(pim=pim, truth=truth)
        summary = await mgr.writeback_product("sku-1")
        assert summary.errors == 1


# ---------------------------------------------------------------------------
# batch_writeback tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestBatchWriteback:
    async def test_returns_result_per_entity(self):
        pim = AsyncMock()
        pim.get_product = AsyncMock(return_value=None)
        pim.push_enrichment = AsyncMock()
        truth = AsyncMock()
        truth.get_attributes = AsyncMock(return_value=_sample_attributes(["color"]))
        mgr = _make_manager(pim=pim, truth=truth)
        results = await mgr.batch_writeback(["sku-1", "sku-2"])
        assert len(results) == 2
        entity_ids = {r.entity_id for r in results}
        assert entity_ids == {"sku-1", "sku-2"}

    async def test_empty_list_returns_empty(self):
        mgr = _make_manager()
        results = await mgr.batch_writeback([])
        assert results == []


# ---------------------------------------------------------------------------
# dry_run tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDryRun:
    async def test_dry_run_uses_dry_run_status(self):
        truth = AsyncMock()
        truth.get_attributes = AsyncMock(return_value=_sample_attributes(["color"]))
        audit = AsyncMock()
        # writeback_enabled=False but dry_run() overrides it internally
        mgr = _make_manager(
            truth=truth,
            audit=audit,
            config=_make_config(writeback_enabled=False, dry_run=False),
        )
        summary = await mgr.dry_run("sku-1")
        assert all(r.status == WritebackStatus.DRY_RUN for r in summary.results)

    async def test_dry_run_does_not_mutate_original_config(self):
        truth = AsyncMock()
        truth.get_attributes = AsyncMock(return_value=[])
        cfg = _make_config(writeback_enabled=False, dry_run=False)
        mgr = _make_manager(truth=truth, config=cfg)
        await mgr.dry_run("sku-1")
        # After dry_run completes, enabled/dry_run should be restored
        assert mgr._config.writeback_enabled is False
        assert mgr._config.dry_run is False
