"""Tests for self-healing retry, cooldown, and escalation diagnostics (#669)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from holiday_peak_lib.self_healing import (
    FailureSignal,
    IncidentState,
    RemediationActionResult,
    SelfHealingKernel,
    SurfaceType,
    default_surface_manifest,
)


def _make_kernel(**overrides: object) -> SelfHealingKernel:
    defaults: dict[str, object] = {
        "service_name": "svc",
        "manifest": default_surface_manifest("svc"),
        "enabled": True,
        "detect_only": False,
    }
    defaults.update(overrides)
    return SelfHealingKernel(**defaults)  # type: ignore[arg-type]


def _api_signal() -> FailureSignal:
    return FailureSignal(
        service_name="svc",
        surface=SurfaceType.API,
        component="/invoke",
        status_code=503,
        error_type="RuntimeError",
        error_message="upstream unavailable",
    )


@pytest.mark.asyncio
async def test_recovery_succeeds_on_first_attempt():
    kernel = _make_kernel(max_retries=2)
    incident = await kernel.handle_failure_signal(_api_signal())

    assert incident is not None
    assert incident.state == IncidentState.CLOSED

    remediation_events = [r for r in incident.audit if r.event == "remediation_started"]
    assert len(remediation_events) == 1
    assert remediation_events[0].details.get("attempt") == 1


@pytest.mark.asyncio
async def test_recovery_retries_on_failure_and_escalates():
    kernel = _make_kernel(max_retries=2)

    async def always_fail(incident):  # noqa: ANN001
        return RemediationActionResult(
            action="reconcile_api_surface_contract",
            success=False,
            details={"error": "simulated"},
        )

    kernel.register_action("reconcile_api_surface_contract", always_fail)

    incident = await kernel.handle_failure_signal(_api_signal())

    assert incident is not None
    assert incident.state == IncidentState.ESCALATED

    # 1 initial + 2 retries = 3 attempts
    remediation_events = [r for r in incident.audit if r.event == "remediation_started"]
    assert len(remediation_events) == 3

    # Final escalation reason
    escalation_events = [r for r in incident.audit if r.event == "incident_escalated"]
    last_escalation = escalation_events[-1]
    assert last_escalation.details["reason"] == "max_retries_exhausted"
    assert last_escalation.details["attempts"] == 3


@pytest.mark.asyncio
async def test_recovery_succeeds_on_retry():
    kernel = _make_kernel(max_retries=2)
    call_count = 0

    async def flaky_handler(incident):  # noqa: ANN001
        nonlocal call_count
        call_count += 1
        return RemediationActionResult(
            action="reconcile_api_surface_contract",
            success=call_count > 1,
            details={"attempt": call_count},
        )

    kernel.register_action("reconcile_api_surface_contract", flaky_handler)

    incident = await kernel.handle_failure_signal(_api_signal())

    assert incident is not None
    assert incident.state == IncidentState.CLOSED

    # First attempt failed, second succeeded
    remediation_events = [r for r in incident.audit if r.event == "remediation_started"]
    assert len(remediation_events) == 2

    # Verify audit trail shows fail then success for the specific action
    reconcile_events = [
        r
        for r in incident.audit
        if r.event in ("action_executed", "action_failed")
        and r.details.get("action") == "reconcile_api_surface_contract"
    ]
    assert len(reconcile_events) == 2
    assert not reconcile_events[0].details.get("success", True)
    assert reconcile_events[1].details.get("success", False)


@pytest.mark.asyncio
async def test_cooldown_blocks_reconcile_before_expiry():
    kernel = _make_kernel(max_retries=0)

    async def always_fail(incident):  # noqa: ANN001
        return RemediationActionResult(
            action="reconcile_api_surface_contract",
            success=False,
            details={"error": "simulated"},
        )

    kernel.register_action("reconcile_api_surface_contract", always_fail)

    incident = await kernel.handle_failure_signal(_api_signal())
    assert incident is not None
    assert incident.state == IncidentState.ESCALATED

    # Set cooldown far in the future
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    incident.metadata["_cooldown_until"] = future

    result = await kernel.reconcile(incident_id=incident.id)
    assert result["reconciled_incidents"] == 0
    assert incident.state == IncidentState.ESCALATED  # unchanged


@pytest.mark.asyncio
async def test_escalation_payload_contains_full_diagnostic_context():
    kernel = _make_kernel(max_retries=0)

    async def always_fail(incident):  # noqa: ANN001
        return RemediationActionResult(
            action="reconcile_api_surface_contract",
            success=False,
            details={"error": "simulated"},
        )

    kernel.register_action("reconcile_api_surface_contract", always_fail)

    incident = await kernel.handle_failure_signal(_api_signal())
    assert incident is not None
    assert incident.state == IncidentState.ESCALATED

    payload = kernel.escalation_payload(incident.id)
    assert payload is not None
    assert "incident" in payload
    assert "audit_trail" in payload
    assert "remediation_history" in payload
    assert "manifest" in payload
    assert "kernel_config" in payload

    config = payload["kernel_config"]
    assert config["enabled"] is True
    assert config["detect_only"] is False
    assert config["max_retries"] == 0
    assert config["cooldown_seconds"] == 5.0

    assert len(payload["remediation_history"]) > 0
    assert payload["remediation_history"][0]["action"] == "reconcile_api_surface_contract"


def test_escalation_payload_returns_none_for_missing_incident():
    kernel = _make_kernel()
    assert kernel.escalation_payload("nonexistent-id") is None


def test_from_env_reads_retry_and_cooldown_settings(monkeypatch):
    monkeypatch.setenv("SELF_HEALING_ENABLED", "true")
    monkeypatch.setenv("SELF_HEALING_MAX_RETRIES", "5")
    monkeypatch.setenv("SELF_HEALING_COOLDOWN_SECONDS", "10.5")
    monkeypatch.delenv("SELF_HEALING_SURFACE_MANIFEST_JSON", raising=False)

    kernel = SelfHealingKernel.from_env("test-svc")
    assert kernel.max_retries == 5
    assert kernel.cooldown_seconds == 10.5
    assert kernel.enabled is True
