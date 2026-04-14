"""Shared self-healing runtime with auditable, allowlisted remediation."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from inspect import isawaitable
from typing import Any
from uuid import uuid4

from holiday_peak_lib.self_healing.manifest import ServiceSurfaceManifest, load_surface_manifest
from holiday_peak_lib.self_healing.models import (
    FailureSignal,
    Incident,
    IncidentAuditRecord,
    IncidentClass,
    IncidentState,
    RemediationActionResult,
    SurfaceType,
)

ActionHandler = Callable[[Incident], Awaitable[RemediationActionResult] | RemediationActionResult]

_SELECTED_RECOVERABLE_5XX = frozenset({500, 502, 503, 504})
_RECOVERABLE_MESSAGING_FAILURE_CATEGORIES = frozenset(
    {"configuration", "authentication", "authorization", "throttled", "transient"}
)
_FORBIDDEN_ACTION_TOKENS = frozenset(
    {
        # Image operations
        "restore_image",
        "image_restore",
        "redeploy_image",
        "image_redeploy",
        "image_rollback",
        # Code redeploy
        "redeploy_code",
        "code_redeploy",
        "code_deploy",
        # Resource deletion
        "delete_namespace",
        "namespace_delete",
        "delete_resource",
        # Secret / certificate rotation
        "rotate_secret",
        "secret_rotate",
        "rotate_cert",
        "cert_rotate",
        # Scaling changes
        "scale_up",
        "scale_down",
        "scale_out",
        "scale_in",
        "autoscale",
        # Database schema changes
        "migrate_schema",
        "schema_migrate",
        "run_migration",
    }
)

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def env_flag_enabled(name: str, *, default: bool = False) -> bool:
    """Parse boolean feature flags from environment variables."""

    import os

    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE_VALUES


class SelfHealingKernel:
    """In-memory self-healing runtime with explicit lifecycle transitions.

    The orchestration follows a Template Method style pipeline:
    detect -> classify -> remediate -> verify -> escalate/closed.
    """

    _allowed_actions = frozenset(
        {
            "reconcile_api_surface_contract",
            "sync_apim_route_config",
            "refresh_aks_ingress_bindings",
            "refresh_mcp_contract_cache",
            "reset_messaging_publisher_bindings",
            "reset_messaging_consumer_bindings",
        }
    )

    _surface_action_plan: dict[SurfaceType, tuple[str, ...]] = {
        SurfaceType.API: ("reconcile_api_surface_contract",),
        SurfaceType.APIM: ("sync_apim_route_config",),
        SurfaceType.AKS_INGRESS: ("refresh_aks_ingress_bindings",),
        SurfaceType.MCP: ("refresh_mcp_contract_cache",),
        SurfaceType.MESSAGING: ("reset_messaging_consumer_bindings",),
    }

    _valid_transitions: dict[IncidentState, set[IncidentState]] = {
        IncidentState.DETECTED: {IncidentState.CLASSIFIED},
        IncidentState.CLASSIFIED: {IncidentState.REMEDIATING, IncidentState.ESCALATED},
        IncidentState.REMEDIATING: {IncidentState.VERIFIED, IncidentState.ESCALATED},
        IncidentState.VERIFIED: {IncidentState.CLOSED, IncidentState.ESCALATED},
        IncidentState.ESCALATED: {IncidentState.REMEDIATING},
        IncidentState.CLOSED: set(),
    }

    def __init__(
        self,
        *,
        service_name: str,
        manifest: ServiceSurfaceManifest,
        enabled: bool = False,
        detect_only: bool = False,
        reconcile_on_messaging_error: bool = False,
        max_incidents: int = 200,
        max_retries: int = 2,
        cooldown_seconds: float = 5.0,
    ) -> None:
        self.service_name = service_name
        self.manifest = manifest
        self.enabled = enabled
        self.detect_only = detect_only
        self.reconcile_on_messaging_error = reconcile_on_messaging_error
        self.max_incidents = max(10, max_incidents)
        self.max_retries = max(0, max_retries)
        self.cooldown_seconds = max(0.0, cooldown_seconds)
        self._incidents: OrderedDict[str, Incident] = OrderedDict()
        self._actions: dict[str, ActionHandler] = {
            "reconcile_api_surface_contract": self._action_reconcile_api_surface_contract,
            "sync_apim_route_config": self._action_sync_apim_route_config,
            "refresh_aks_ingress_bindings": self._action_refresh_aks_ingress_bindings,
            "refresh_mcp_contract_cache": self._action_refresh_mcp_contract_cache,
            "reset_messaging_publisher_bindings": self._action_reset_messaging_publisher_bindings,
            "reset_messaging_consumer_bindings": self._action_reset_messaging_consumer_bindings,
        }

    @classmethod
    def from_env(cls, service_name: str) -> "SelfHealingKernel":
        """Create kernel from feature flags and manifest environment settings."""

        import os

        manifest = load_surface_manifest(service_name)
        return cls(
            service_name=service_name,
            manifest=manifest,
            enabled=env_flag_enabled("SELF_HEALING_ENABLED", default=False),
            detect_only=env_flag_enabled("SELF_HEALING_DETECT_ONLY", default=False),
            reconcile_on_messaging_error=env_flag_enabled(
                "SELF_HEALING_RECONCILE_ON_MESSAGING_ERROR",
                default=False,
            ),
            max_retries=int(os.getenv("SELF_HEALING_MAX_RETRIES", "2")),
            cooldown_seconds=float(os.getenv("SELF_HEALING_COOLDOWN_SECONDS", "5.0")),
        )

    def register_action(self, name: str, handler: ActionHandler) -> None:
        """Register a custom action when it is in the allowlist and policy-compliant."""

        self._assert_action_allowed(name)
        self._actions[name] = handler

    def status(self) -> dict[str, Any]:
        """Return operational status and aggregate counters."""

        incidents = list(self._incidents.values())
        open_count = sum(1 for incident in incidents if incident.state != IncidentState.CLOSED)
        return {
            "service": self.service_name,
            "enabled": self.enabled,
            "detect_only": self.detect_only,
            "reconcile_on_messaging_error": self.reconcile_on_messaging_error,
            "manifest": self.manifest.model_dump(mode="json"),
            "allowlisted_actions": sorted(self._allowed_actions),
            "incidents_total": len(incidents),
            "incidents_open": open_count,
            "incidents_closed": len(incidents) - open_count,
        }

    def list_incidents(
        self,
        *,
        limit: int = 50,
        state: IncidentState | None = None,
    ) -> list[Incident]:
        """List incidents newest-first with optional state filtering."""

        normalized_limit = max(1, limit)
        incidents = list(reversed(list(self._incidents.values())))
        if state is not None:
            incidents = [incident for incident in incidents if incident.state == state]
        return incidents[:normalized_limit]

    async def handle_failure_signal(self, signal: FailureSignal) -> Incident | None:
        """Run incident lifecycle from detection to closure/escalation."""

        if not self.enabled:
            return None

        incident = self._detect(signal)
        self._classify(incident)

        if not incident.recoverable:
            self._transition(
                incident,
                IncidentState.ESCALATED,
                event="incident_escalated",
                details={"reason": "non_recoverable_classification"},
            )
            return incident

        if self.detect_only:
            self._transition(
                incident,
                IncidentState.ESCALATED,
                event="incident_escalated",
                details={"reason": "detect_only_mode"},
            )
            return incident

        if incident.surface == SurfaceType.MESSAGING and not self.reconcile_on_messaging_error:
            self._transition(
                incident,
                IncidentState.ESCALATED,
                event="incident_escalated",
                details={"reason": "messaging_remediation_opt_in_disabled"},
            )
            return incident

        await self._attempt_recovery(incident)
        return incident

    async def reconcile(self, *, incident_id: str | None = None) -> dict[str, Any]:
        """Attempt remediation for open recoverable incidents."""

        if not self.enabled:
            return {
                "service": self.service_name,
                "enabled": False,
                "reconciled_incidents": 0,
                "incident_ids": [],
            }

        candidates: list[Incident] = []
        if incident_id:
            incident = self._incidents.get(incident_id)
            if incident is not None and not self._is_in_cooldown(incident):
                candidates = [incident]
        else:
            candidates = [
                incident
                for incident in self._incidents.values()
                if incident.recoverable
                and incident.state in {IncidentState.CLASSIFIED, IncidentState.ESCALATED}
                and not self._is_in_cooldown(incident)
            ]

        reconciled_ids: list[str] = []
        for incident in candidates:
            if self.detect_only:
                if incident.state != IncidentState.ESCALATED:
                    self._transition(
                        incident,
                        IncidentState.ESCALATED,
                        event="incident_escalated",
                        details={"reason": "detect_only_mode"},
                    )
                continue
            await self._attempt_recovery(incident)
            reconciled_ids.append(incident.id)

        return {
            "service": self.service_name,
            "enabled": self.enabled,
            "detect_only": self.detect_only,
            "reconciled_incidents": len(reconciled_ids),
            "incident_ids": reconciled_ids,
        }

    def escalation_payload(self, incident_id: str) -> dict[str, Any] | None:
        """Return full diagnostic context for an incident, or None if not found."""

        incident = self._incidents.get(incident_id)
        if incident is None:
            return None

        remediation_history: list[dict[str, Any]] = []
        for record in incident.audit:
            if record.event in ("action_executed", "action_failed"):
                remediation_history.append(
                    {
                        "action": record.details.get("action"),
                        "success": record.details.get("success", False),
                        "event": record.event,
                    }
                )

        return {
            "incident": incident.model_dump(mode="json"),
            "audit_trail": [r.model_dump(mode="json") for r in incident.audit],
            "remediation_history": remediation_history,
            "manifest": self.manifest.model_dump(mode="json"),
            "kernel_config": {
                "enabled": self.enabled,
                "detect_only": self.detect_only,
                "max_retries": self.max_retries,
                "cooldown_seconds": self.cooldown_seconds,
            },
        }

    def _is_in_cooldown(self, incident: Incident) -> bool:
        """Check whether an incident is still within its cooldown window."""

        cooldown_until_str = incident.metadata.get("_cooldown_until")
        if not cooldown_until_str:
            return False
        try:
            cooldown_until = datetime.fromisoformat(cooldown_until_str)
            return _utc_now() < cooldown_until
        except (ValueError, TypeError):
            return False

    def _detect(self, signal: FailureSignal) -> Incident:
        incident = Incident(
            id=str(uuid4()),
            service_name=signal.service_name,
            surface=signal.surface,
            component=signal.component,
            state=IncidentState.DETECTED,
            status_code=signal.status_code,
            error_type=signal.error_type,
            error_message=signal.error_message,
            metadata=dict(signal.metadata),
            created_at=signal.timestamp,
            updated_at=signal.timestamp,
        )
        self._record_audit(incident, event="incident_detected", details={"signal": "captured"})
        self._track_incident(incident)
        return incident

    def _classify(self, incident: Incident) -> None:
        status_code = incident.status_code
        if incident.surface == SurfaceType.MESSAGING:
            recoverable = self._classify_messaging_incident(incident)
        else:
            recoverable = bool(
                status_code is not None
                and (400 <= status_code < 500 or status_code in _SELECTED_RECOVERABLE_5XX)
            )
        incident.incident_class = (
            IncidentClass.INFRASTRUCTURE_MISCONFIGURATION
            if recoverable
            else IncidentClass.NON_RECOVERABLE
        )
        incident.recoverable = recoverable
        self._transition(
            incident,
            IncidentState.CLASSIFIED,
            event="incident_classified",
            details={
                "recoverable": recoverable,
                "incident_class": (
                    incident.incident_class.value if incident.incident_class is not None else None
                ),
            },
        )

    async def _attempt_recovery(self, incident: Incident) -> None:
        actions = self._plan_actions(incident)
        if not actions:
            self._transition(
                incident,
                IncidentState.ESCALATED,
                event="incident_escalated",
                details={"reason": "no_allowlisted_actions"},
            )
            return

        total_attempts = 1 + self.max_retries

        for attempt in range(total_attempts):
            if attempt > 0:
                cooldown_until = _utc_now() + timedelta(seconds=self.cooldown_seconds)
                incident.metadata["_cooldown_until"] = cooldown_until.isoformat()
                self._record_audit(
                    incident,
                    event="cooldown_scheduled",
                    details={
                        "attempt": attempt + 1,
                        "cooldown_seconds": self.cooldown_seconds,
                        "cooldown_until": cooldown_until.isoformat(),
                    },
                )

            self._transition(
                incident,
                IncidentState.REMEDIATING,
                event="remediation_started",
                details={"actions": actions, "attempt": attempt + 1},
            )

            results: list[RemediationActionResult] = []
            for action_name in actions:
                result = await self._execute_action(action_name, incident)
                results.append(result)

            self._transition(
                incident,
                IncidentState.VERIFIED,
                event="verification_started",
                details={"actions": actions, "attempt": attempt + 1},
            )

            if all(result.success for result in results):
                self._transition(
                    incident,
                    IncidentState.CLOSED,
                    event="incident_closed",
                    details={"verified": True},
                )
                return

            if attempt < total_attempts - 1:
                self._transition(
                    incident,
                    IncidentState.ESCALATED,
                    event="incident_escalated",
                    details={"reason": "verification_failed", "attempt": attempt + 1},
                )
            else:
                self._transition(
                    incident,
                    IncidentState.ESCALATED,
                    event="incident_escalated",
                    details={
                        "reason": "max_retries_exhausted",
                        "attempts": total_attempts,
                    },
                )

    def _plan_actions(self, incident: Incident) -> list[str]:
        if incident.surface == SurfaceType.MESSAGING:
            return self._plan_messaging_actions(incident)

        actions = list(self._surface_action_plan.get(incident.surface, ()))

        # API incidents may need edge reconciliation on APIM/ingress surfaces.
        if incident.surface == SurfaceType.API:
            edge_surfaces = {edge.surface for edge in self.manifest.edge_references}
            if SurfaceType.APIM in edge_surfaces:
                actions.append("sync_apim_route_config")
            if SurfaceType.AKS_INGRESS in edge_surfaces:
                actions.append("refresh_aks_ingress_bindings")

        deduplicated: list[str] = []
        for action_name in actions:
            if action_name not in deduplicated:
                deduplicated.append(action_name)
        return deduplicated

    def _classify_messaging_incident(self, incident: Incident) -> bool:
        if self._compensation_failed(incident.metadata):
            return False

        failure_category = str(incident.metadata.get("failure_category") or "").strip().lower()
        if failure_category:
            return failure_category in _RECOVERABLE_MESSAGING_FAILURE_CATEGORIES or bool(
                incident.status_code in _SELECTED_RECOVERABLE_5XX
            )

        status_code = incident.status_code
        return bool(
            status_code is not None
            and (400 <= status_code < 500 or status_code in _SELECTED_RECOVERABLE_5XX)
        )

    def _plan_messaging_actions(self, incident: Incident) -> list[str]:
        if self._compensation_failed(incident.metadata):
            return []

        preferred_action = self._preferred_messaging_action(incident.metadata)
        if preferred_action is not None:
            return [preferred_action]

        failure_stage = str(incident.metadata.get("failure_stage") or "").strip().lower()
        if failure_stage == "publish":
            return ["reset_messaging_publisher_bindings"]
        return ["reset_messaging_consumer_bindings"]

    def _preferred_messaging_action(self, metadata: dict[str, Any]) -> str | None:
        remediation_context = metadata.get("remediation_context")
        if isinstance(remediation_context, dict):
            preferred_action = remediation_context.get("preferred_action")
            if isinstance(preferred_action, str) and preferred_action in self._allowed_actions:
                return preferred_action

        remediation_action = metadata.get("remediation_action")
        if isinstance(remediation_action, str) and remediation_action in self._allowed_actions:
            return remediation_action
        return None

    def _compensation_failed(self, metadata: dict[str, Any]) -> bool:
        compensation = metadata.get("compensation")
        if not isinstance(compensation, dict):
            return False
        if compensation.get("succeeded") is False:
            return True
        return compensation.get("failed_action") is not None

    def _messaging_action_details(self, incident: Incident) -> dict[str, Any]:
        details: dict[str, Any] = {"component": incident.component}
        for key in (
            "topic",
            "domain",
            "event_type",
            "profile",
            "failure_category",
            "failure_stage",
        ):
            value = incident.metadata.get(key)
            if value is not None:
                details[key] = value

        remediation_context = incident.metadata.get("remediation_context")
        if remediation_context is not None:
            details["remediation_context"] = remediation_context

        compensation = incident.metadata.get("compensation")
        if compensation is not None:
            details["compensation"] = compensation
        return details

    async def _execute_action(
        self, action_name: str, incident: Incident
    ) -> RemediationActionResult:
        try:
            self._assert_action_allowed(action_name)
            handler = self._actions[action_name]
            result = handler(incident)
            if isawaitable(result):
                result = await result
            if not isinstance(result, RemediationActionResult):
                raise TypeError("Action handler must return RemediationActionResult")
            incident.actions.append(action_name)
            self._record_audit(
                incident,
                event="action_executed",
                details={
                    "action": action_name,
                    "success": result.success,
                    "details": result.details,
                },
            )
            return result
        except (
            AttributeError,
            LookupError,
            PermissionError,
            RuntimeError,
            TypeError,
            ValueError,
        ) as exc:
            failure_result = RemediationActionResult(
                action=action_name,
                success=False,
                details={"error": str(exc)},
            )
            incident.actions.append(action_name)
            self._record_audit(
                incident,
                event="action_failed",
                details={"action": action_name, "error": str(exc)},
            )
            return failure_result

    def _assert_action_allowed(self, action_name: str) -> None:
        normalized = action_name.strip().lower().replace("-", "_")
        if any(token in normalized for token in _FORBIDDEN_ACTION_TOKENS):
            raise PermissionError(
                "Image restore/redeploy remediation is forbidden by self-healing policy."
            )
        if action_name not in self._allowed_actions:
            raise PermissionError(f"Action '{action_name}' is not in the self-healing allowlist.")

    def _track_incident(self, incident: Incident) -> None:
        self._incidents[incident.id] = incident
        while len(self._incidents) > self.max_incidents:
            self._incidents.popitem(last=False)

    def _transition(
        self,
        incident: Incident,
        new_state: IncidentState,
        *,
        event: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        current_state = incident.state
        valid_targets = self._valid_transitions[current_state]
        if new_state not in valid_targets:
            raise RuntimeError(f"Invalid transition from {current_state} to {new_state}")
        incident.state = new_state
        incident.updated_at = _utc_now()
        self._record_audit(incident, event=event, details=details or {})

    def _record_audit(self, incident: Incident, *, event: str, details: dict[str, Any]) -> None:
        incident.audit.append(
            IncidentAuditRecord(
                state=incident.state,
                event=event,
                details=details,
                timestamp=_utc_now(),
            )
        )

    async def _action_reconcile_api_surface_contract(
        self,
        incident: Incident,
    ) -> RemediationActionResult:
        return RemediationActionResult(
            action="reconcile_api_surface_contract",
            success=True,
            details={"component": incident.component},
        )

    async def _action_sync_apim_route_config(
        self,
        incident: Incident,
    ) -> RemediationActionResult:
        return RemediationActionResult(
            action="sync_apim_route_config",
            success=True,
            details={"surface": incident.surface.value},
        )

    async def _action_refresh_aks_ingress_bindings(
        self,
        incident: Incident,
    ) -> RemediationActionResult:
        return RemediationActionResult(
            action="refresh_aks_ingress_bindings",
            success=True,
            details={"surface": incident.surface.value},
        )

    async def _action_refresh_mcp_contract_cache(
        self,
        incident: Incident,
    ) -> RemediationActionResult:
        return RemediationActionResult(
            action="refresh_mcp_contract_cache",
            success=True,
            details={"component": incident.component},
        )

    async def _action_reset_messaging_publisher_bindings(
        self,
        incident: Incident,
    ) -> RemediationActionResult:
        return RemediationActionResult(
            action="reset_messaging_publisher_bindings",
            success=True,
            details=self._messaging_action_details(incident),
        )

    async def _action_reset_messaging_consumer_bindings(
        self,
        incident: Incident,
    ) -> RemediationActionResult:
        return RemediationActionResult(
            action="reset_messaging_consumer_bindings",
            success=True,
            details=self._messaging_action_details(incident),
        )
