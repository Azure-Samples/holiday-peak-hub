"""Contract tests for AKS self-healing strategy pack (#666)."""

import pytest
from holiday_peak_lib.self_healing import (
    FailureSignal,
    IncidentClass,
    IncidentState,
    SelfHealingKernel,
    SurfaceType,
    default_surface_manifest,
)


def _make_kernel(**overrides) -> SelfHealingKernel:
    defaults = {
        "service_name": "svc",
        "manifest": default_surface_manifest("svc"),
        "enabled": True,
        "detect_only": False,
    }
    defaults.update(overrides)
    return SelfHealingKernel(**defaults)


def _aks_signal(
    status_code: int,
    *,
    error_message: str = "ingress failure",
    component: str = "/invoke",
) -> FailureSignal:
    return FailureSignal(
        service_name="svc",
        surface=SurfaceType.AKS_INGRESS,
        component=component,
        status_code=status_code,
        error_type="IngressError",
        error_message=error_message,
    )


@pytest.mark.asyncio
async def test_aks_ingress_503_misconfiguration_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _aks_signal(503, error_message="ingress misconfiguration")
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED
    assert "refresh_aks_ingress_bindings" in incident.actions


@pytest.mark.asyncio
async def test_aks_ingress_502_bad_gateway_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(_aks_signal(502, error_message="bad gateway"))

    assert incident is not None
    assert incident.incident_class == IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED
    assert "refresh_aks_ingress_bindings" in incident.actions


@pytest.mark.asyncio
async def test_aks_ingress_404_selector_mismatch_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _aks_signal(404, error_message="service selector mismatch")
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED
    assert "refresh_aks_ingress_bindings" in incident.actions


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [200, 201, 204, 301, 302])
async def test_aks_ingress_non_recoverable_status_codes(status_code: int):
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _aks_signal(status_code, error_message="not an error")
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.NON_RECOVERABLE
    assert incident.recoverable is False
    assert incident.state == IncidentState.ESCALATED


@pytest.mark.asyncio
async def test_api_surface_failure_triggers_aks_edge_action():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        FailureSignal(
            service_name="svc",
            surface=SurfaceType.API,
            component="/invoke",
            status_code=503,
            error_type="RuntimeError",
            error_message="upstream unavailable",
        )
    )

    assert incident is not None
    assert incident.state == IncidentState.CLOSED
    assert "reconcile_api_surface_contract" in incident.actions
    assert "refresh_aks_ingress_bindings" in incident.actions


@pytest.mark.asyncio
async def test_aks_incident_reconcile_reattempts_classified_incident():
    kernel = _make_kernel(detect_only=True)

    incident = await kernel.handle_failure_signal(
        _aks_signal(502, error_message="ingress bad gateway")
    )

    assert incident is not None
    assert incident.state == IncidentState.ESCALATED
    assert incident.recoverable is True
    assert incident.actions == []

    kernel.detect_only = False
    result = await kernel.reconcile(incident_id=incident.id)

    assert result["reconciled_incidents"] == 1
    assert incident.id in result["incident_ids"]
    assert incident.state == IncidentState.CLOSED
    assert "refresh_aks_ingress_bindings" in incident.actions
