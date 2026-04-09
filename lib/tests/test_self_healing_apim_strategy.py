"""Contract tests for APIM self-healing strategy pack (#665)."""

import pytest
from holiday_peak_lib.self_healing import (
    FailureSignal,
    IncidentClass,
    IncidentState,
    RemediationActionResult,
    SelfHealingKernel,
    SurfaceType,
    default_surface_manifest,
)


def _make_kernel() -> SelfHealingKernel:
    return SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=True,
        detect_only=False,
    )


def _apim_signal(
    status_code: int,
    *,
    error_message: str = "apim failure",
    component: str = "/api/products",
) -> FailureSignal:
    return FailureSignal(
        service_name="svc",
        surface=SurfaceType.APIM,
        component=component,
        status_code=status_code,
        error_type="APIMError",
        error_message=error_message,
    )


@pytest.mark.asyncio
async def test_apim_404_misroute_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _apim_signal(404, error_message="route not found")
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED
    assert "sync_apim_route_config" in incident.actions


@pytest.mark.asyncio
async def test_apim_502_backend_drift_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _apim_signal(502, error_message="backend mapping drift")
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED
    assert "sync_apim_route_config" in incident.actions


@pytest.mark.asyncio
async def test_apim_403_auth_policy_mismatch_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _apim_signal(403, error_message="auth policy mismatch")
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED
    assert "sync_apim_route_config" in incident.actions


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [200, 201, 204, 301, 302])
async def test_apim_non_recoverable_status_codes(status_code: int):
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _apim_signal(status_code, error_message="not an error")
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.NON_RECOVERABLE
    assert incident.recoverable is False
    assert incident.state == IncidentState.ESCALATED


@pytest.mark.asyncio
async def test_apim_custom_action_handler_gets_called():
    kernel = _make_kernel()
    handler_called = False

    async def _custom_handler(incident):
        nonlocal handler_called
        handler_called = True
        return RemediationActionResult(
            action="sync_apim_route_config",
            success=True,
            details={"custom": True},
        )

    kernel.register_action("sync_apim_route_config", _custom_handler)

    incident = await kernel.handle_failure_signal(
        _apim_signal(502, error_message="custom scenario")
    )

    assert handler_called is True
    assert incident is not None
    assert incident.state == IncidentState.CLOSED
    assert "sync_apim_route_config" in incident.actions


@pytest.mark.asyncio
async def test_apim_incident_audit_trail_contains_all_lifecycle_events():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _apim_signal(503, error_message="backend unavailable")
    )

    assert incident is not None
    audit_events = [record.event for record in incident.audit]
    assert "incident_detected" in audit_events
    assert "incident_classified" in audit_events
    assert "remediation_started" in audit_events
    assert "action_executed" in audit_events
    assert "verification_started" in audit_events
    assert "incident_closed" in audit_events
