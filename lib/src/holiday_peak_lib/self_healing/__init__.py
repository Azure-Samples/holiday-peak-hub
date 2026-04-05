"""Self-healing runtime for shared service resilience."""

from .kernel import SelfHealingKernel, env_flag_enabled
from .manifest import (
    SURFACE_MANIFEST_ENV_VAR,
    ServiceSurfaceManifest,
    SurfaceEdgeReference,
    SurfaceManifestError,
    default_surface_manifest,
    load_surface_manifest,
)
from .models import (
    FailureSignal,
    Incident,
    IncidentAuditRecord,
    IncidentClass,
    IncidentState,
    RemediationActionResult,
    SurfaceType,
)

__all__ = [
    "SelfHealingKernel",
    "env_flag_enabled",
    "SURFACE_MANIFEST_ENV_VAR",
    "ServiceSurfaceManifest",
    "SurfaceEdgeReference",
    "SurfaceManifestError",
    "default_surface_manifest",
    "load_surface_manifest",
    "FailureSignal",
    "Incident",
    "IncidentAuditRecord",
    "IncidentClass",
    "IncidentState",
    "RemediationActionResult",
    "SurfaceType",
]
