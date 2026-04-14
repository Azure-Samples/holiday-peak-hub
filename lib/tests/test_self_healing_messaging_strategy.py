"""Contract tests for Messaging self-healing strategy pack (#667)."""

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
        "reconcile_on_messaging_error": True,
    }
    defaults.update(overrides)
    return SelfHealingKernel(**defaults)


def _messaging_signal(
    *,
    failure_category: str | None = None,
    failure_stage: str | None = None,
    status_code: int = 503,
    error_message: str = "messaging error",
    metadata: dict | None = None,
) -> FailureSignal:
    meta = metadata if metadata is not None else {}
    if failure_category is not None:
        meta.setdefault("failure_category", failure_category)
    if failure_stage is not None:
        meta.setdefault("failure_stage", failure_stage)
    return FailureSignal(
        service_name="svc",
        surface=SurfaceType.MESSAGING,
        component="order-events",
        status_code=status_code,
        error_type="MessagingError",
        error_message=error_message,
        metadata=meta,
    )


@pytest.mark.asyncio
async def test_messaging_authentication_failure_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(failure_category="authentication")
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED
    assert "reset_messaging_consumer_bindings" in incident.actions


@pytest.mark.asyncio
async def test_messaging_configuration_failure_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(failure_category="configuration")
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED
    assert "reset_messaging_consumer_bindings" in incident.actions


@pytest.mark.asyncio
async def test_messaging_authorization_failure_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(failure_category="authorization")
    )

    assert incident is not None
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED


@pytest.mark.asyncio
async def test_messaging_throttled_failure_recoverable_and_closes():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(_messaging_signal(failure_category="throttled"))

    assert incident is not None
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED


@pytest.mark.asyncio
async def test_messaging_unknown_category_with_recoverable_status_is_recoverable():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(failure_category="hardware", status_code=503)
    )

    assert incident is not None
    assert incident.recoverable is True
    assert incident.state == IncidentState.CLOSED


@pytest.mark.asyncio
async def test_messaging_unknown_category_with_non_recoverable_status_escalates():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(failure_category="hardware", status_code=200)
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.NON_RECOVERABLE
    assert incident.recoverable is False
    assert incident.state == IncidentState.ESCALATED


@pytest.mark.asyncio
async def test_messaging_publish_stage_uses_publisher_action():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(
            failure_category="transient",
            failure_stage="publish",
        )
    )

    assert incident is not None
    assert incident.state == IncidentState.CLOSED
    assert incident.actions == ["reset_messaging_publisher_bindings"]


@pytest.mark.asyncio
async def test_messaging_consumer_stage_uses_consumer_action():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(
            failure_category="transient",
            failure_stage="consume",
        )
    )

    assert incident is not None
    assert incident.state == IncidentState.CLOSED
    assert incident.actions == ["reset_messaging_consumer_bindings"]


@pytest.mark.asyncio
async def test_messaging_preferred_action_overrides_default():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(
            failure_category="transient",
            failure_stage="consume",
            metadata={
                "failure_category": "transient",
                "failure_stage": "consume",
                "remediation_context": {
                    "preferred_action": "reset_messaging_publisher_bindings",
                },
            },
        )
    )

    assert incident is not None
    assert incident.state == IncidentState.CLOSED
    assert incident.actions == ["reset_messaging_publisher_bindings"]


@pytest.mark.asyncio
async def test_messaging_compensation_failed_succeeded_false_is_non_recoverable():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(
            failure_category="transient",
            metadata={
                "failure_category": "transient",
                "compensation": {
                    "succeeded": False,
                    "completed_actions": ["rollback_a"],
                    "failed_action": None,
                    "failed_error_type": "RuntimeError",
                    "failed_error": "rollback failed",
                },
            },
        )
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.NON_RECOVERABLE
    assert incident.recoverable is False
    assert incident.state == IncidentState.ESCALATED
    assert incident.actions == []


@pytest.mark.asyncio
async def test_messaging_compensation_failed_action_set_is_non_recoverable():
    kernel = _make_kernel()

    incident = await kernel.handle_failure_signal(
        _messaging_signal(
            failure_category="configuration",
            metadata={
                "failure_category": "configuration",
                "compensation": {
                    "succeeded": True,
                    "completed_actions": [],
                    "failed_action": "order_write_rollback",
                    "failed_error_type": "RuntimeError",
                    "failed_error": "compensating action failed",
                },
            },
        )
    )

    assert incident is not None
    assert incident.incident_class == IncidentClass.NON_RECOVERABLE
    assert incident.recoverable is False
    assert incident.state == IncidentState.ESCALATED
    assert incident.actions == []


@pytest.mark.asyncio
async def test_messaging_opt_in_disabled_escalates_without_remediation():
    """When reconcile_on_messaging_error is False, messaging incidents escalate immediately."""
    kernel = _make_kernel(reconcile_on_messaging_error=False)

    incident = await kernel.handle_failure_signal(
        _messaging_signal(failure_category="authentication")
    )

    assert incident is not None
    assert incident.recoverable is True
    assert incident.state == IncidentState.ESCALATED
    assert incident.actions == []
    escalation = [r for r in incident.audit if r.event == "incident_escalated"]
    assert escalation[-1].details["reason"] == "messaging_remediation_opt_in_disabled"
