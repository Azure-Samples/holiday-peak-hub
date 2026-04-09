"""Unit tests for self-healing policy, lifecycle, and manifest loading."""

import pytest
from holiday_peak_lib.self_healing import (
    FailureSignal,
    IncidentClass,
    IncidentState,
    SelfHealingKernel,
    SurfaceManifestError,
    SurfaceType,
    default_surface_manifest,
    load_surface_manifest,
)


def test_manifest_loader_uses_default_when_env_missing(monkeypatch):
    monkeypatch.delenv("SELF_HEALING_SURFACE_MANIFEST_JSON", raising=False)

    manifest = load_surface_manifest("catalog-search")

    assert manifest.service_name == "catalog-search"
    assert "/invoke" in manifest.api_endpoints
    assert any(edge.surface == SurfaceType.APIM for edge in manifest.edge_references)


def test_manifest_loader_accepts_env_json(monkeypatch):
    monkeypatch.setenv(
        "SELF_HEALING_SURFACE_MANIFEST_JSON",
        (
            "{"
            '"service_name": "svc",'
            '"api_endpoints": ["/health", "/invoke"],'
            '"mcp_paths": ["/mcp/search"],'
            '"messaging_topics": ["jobs"],'
            '"edge_references": ['
            '{"surface": "apim", "name": "svc-apim", "target": "apim://svc"}'
            "]"
            "}"
        ),
    )

    manifest = load_surface_manifest("svc")

    assert manifest.service_name == "svc"
    assert manifest.mcp_paths == ["/mcp/search"]
    assert manifest.messaging_topics == ["jobs"]


def test_manifest_loader_validation_error_is_actionable(monkeypatch):
    monkeypatch.setenv(
        "SELF_HEALING_SURFACE_MANIFEST_JSON",
        '{"service_name":"svc","api_endpoints":["health"]}',
    )

    with pytest.raises(SurfaceManifestError) as exc:
        load_surface_manifest("svc")

    message = str(exc.value)
    assert "SELF_HEALING_SURFACE_MANIFEST_JSON" in message
    assert "must start with '/'" in message


@pytest.mark.asyncio
async def test_kernel_lifecycle_closes_recoverable_incident():
    kernel = SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=True,
        detect_only=False,
    )

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
    assert incident.incident_class == IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
    assert incident.state == IncidentState.CLOSED
    assert incident.actions
    assert any(record.event == "incident_closed" for record in incident.audit)


@pytest.mark.asyncio
async def test_kernel_detect_only_escalates_without_remediation():
    kernel = SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=True,
        detect_only=True,
    )

    incident = await kernel.handle_failure_signal(
        FailureSignal(
            service_name="svc",
            surface=SurfaceType.MCP,
            component="/mcp/tool",
            status_code=422,
            error_type="ValidationError",
            error_message="bad payload",
        )
    )

    assert incident is not None
    assert incident.state == IncidentState.ESCALATED
    assert incident.actions == []
    assert any(record.event == "incident_escalated" for record in incident.audit)


@pytest.mark.asyncio
async def test_kernel_disabled_preserves_existing_behavior():
    kernel = SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=False,
    )

    incident = await kernel.handle_failure_signal(
        FailureSignal(
            service_name="svc",
            surface=SurfaceType.MESSAGING,
            component="orders",
            status_code=503,
            error_type="Exception",
            error_message="boom",
        )
    )

    assert incident is None
    assert kernel.list_incidents() == []


def test_policy_forbids_image_redeploy_actions():
    kernel = SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=True,
    )

    async def _handler(_incident):  # noqa: ANN001
        raise AssertionError("should never execute")

    with pytest.raises(PermissionError, match="forbidden"):
        kernel.register_action("redeploy_image", _handler)


@pytest.mark.asyncio
async def test_kernel_uses_publisher_action_for_publish_failures():
    kernel = SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=True,
        reconcile_on_messaging_error=True,
    )

    incident = await kernel.handle_failure_signal(
        FailureSignal(
            service_name="svc",
            surface=SurfaceType.MESSAGING,
            component="order-events",
            status_code=503,
            error_type="TimeoutError",
            error_message="publish timeout",
            metadata={
                "failure_stage": "publish",
                "failure_category": "transient",
                "domain": "orders",
                "remediation_context": {
                    "preferred_action": "reset_messaging_publisher_bindings",
                    "workflow": "checkout_finalize",
                },
            },
        )
    )

    assert incident is not None
    assert incident.state == IncidentState.CLOSED
    assert incident.actions == ["reset_messaging_publisher_bindings"]
    action_record = next(record for record in incident.audit if record.event == "action_executed")
    assert (
        action_record.details["details"]["remediation_context"]["workflow"] == "checkout_finalize"
    )


@pytest.mark.asyncio
async def test_kernel_escalates_when_compensation_has_failed():
    kernel = SelfHealingKernel(
        service_name="svc",
        manifest=default_surface_manifest("svc"),
        enabled=True,
        reconcile_on_messaging_error=True,
    )

    incident = await kernel.handle_failure_signal(
        FailureSignal(
            service_name="svc",
            surface=SurfaceType.MESSAGING,
            component="order-events",
            status_code=503,
            error_type="TimeoutError",
            error_message="publish timeout",
            metadata={
                "failure_stage": "publish",
                "failure_category": "transient",
                "compensation": {
                    "succeeded": False,
                    "completed_actions": ["reservation_lock_rollback"],
                    "failed_action": "order_write_rollback",
                    "failed_error_type": "RuntimeError",
                    "failed_error": "rollback failed",
                },
                "remediation_context": {
                    "preferred_action": "reset_messaging_publisher_bindings",
                    "workflow": "checkout_finalize",
                },
            },
        )
    )

    assert incident is not None
    assert incident.state == IncidentState.ESCALATED
    assert incident.incident_class == IncidentClass.NON_RECOVERABLE
    assert incident.actions == []
