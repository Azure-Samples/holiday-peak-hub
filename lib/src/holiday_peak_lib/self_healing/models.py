"""Domain models for the shared self-healing runtime."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(timezone.utc)


class IncidentState(StrEnum):
    """Lifecycle states for self-healing incidents."""

    DETECTED = "detected"
    CLASSIFIED = "classified"
    REMEDIATING = "remediating"
    VERIFIED = "verified"
    ESCALATED = "escalated"
    CLOSED = "closed"


class SurfaceType(StrEnum):
    """Supported service surfaces for failure signals and remediation planning."""

    API = "api"
    APIM = "apim"
    AKS_INGRESS = "aks_ingress"
    MCP = "mcp"
    MESSAGING = "messaging"


class IncidentClass(StrEnum):
    """Classifications assigned during the classify phase."""

    INFRASTRUCTURE_MISCONFIGURATION = "infrastructure_misconfiguration"
    NON_RECOVERABLE = "non_recoverable"


class FailureSignal(BaseModel):
    """Normalized failure input consumed by the self-healing kernel."""

    service_name: str
    surface: SurfaceType
    component: str
    status_code: int | None = None
    error_type: str
    error_message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=utc_now)


class IncidentAuditRecord(BaseModel):
    """Immutable audit item for each state transition and action."""

    timestamp: datetime = Field(default_factory=utc_now)
    state: IncidentState
    event: str
    details: dict[str, Any] = Field(default_factory=dict)


class RemediationActionResult(BaseModel):
    """Outcome produced by a remediation action execution."""

    action: str
    success: bool
    details: dict[str, Any] = Field(default_factory=dict)


class Incident(BaseModel):
    """Tracked incident with lifecycle status and audit records."""

    id: str
    service_name: str
    surface: SurfaceType
    component: str
    state: IncidentState
    incident_class: IncidentClass | None = None
    recoverable: bool = False
    status_code: int | None = None
    error_type: str
    error_message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)
    audit: list[IncidentAuditRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
