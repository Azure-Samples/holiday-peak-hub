"""Service surface manifest contract for self-healing coverage."""

from __future__ import annotations

import json
import os
import re

from pydantic import BaseModel, Field, ValidationError, field_validator

from holiday_peak_lib.self_healing.models import SurfaceType

SURFACE_MANIFEST_ENV_VAR = "SELF_HEALING_SURFACE_MANIFEST_JSON"


class SurfaceManifestError(ValueError):
    """Raised when surface manifest loading or validation fails."""


class SurfaceEdgeReference(BaseModel):
    """Reference to a managed edge surface related to the service."""

    surface: SurfaceType
    name: str = Field(min_length=1)
    target: str = Field(min_length=1)


class ServiceSurfaceManifest(BaseModel):
    """Expected service surfaces consumed by the self-healing runtime."""

    service_name: str = Field(min_length=1)
    api_endpoints: list[str] = Field(default_factory=list)
    mcp_paths: list[str] = Field(default_factory=list)
    messaging_topics: list[str] = Field(default_factory=list)
    edge_references: list[SurfaceEdgeReference] = Field(default_factory=list)

    @field_validator("api_endpoints", "mcp_paths")
    @classmethod
    def _validate_paths(cls, value: list[str]) -> list[str]:
        for path in value:
            if not path.startswith("/"):
                raise ValueError("must start with '/'")
        return value

    @field_validator("messaging_topics")
    @classmethod
    def _validate_topics(cls, value: list[str]) -> list[str]:
        for topic in value:
            if not topic.strip():
                raise ValueError("must not be empty")
        return value


def _normalize_service_key(service_name: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9-]+", "-", service_name.strip()).strip("-")
    return slug.lower() or "service"


def default_surface_manifest(service_name: str) -> ServiceSurfaceManifest:
    """Build a default manifest when no explicit JSON contract is provided."""

    normalized = _normalize_service_key(service_name)
    return ServiceSurfaceManifest(
        service_name=service_name,
        api_endpoints=[
            "/health",
            "/ready",
            "/invoke",
            "/self-healing/status",
            "/self-healing/incidents",
            "/self-healing/reconcile",
        ],
        mcp_paths=["/mcp"],
        messaging_topics=[f"{normalized}-events"],
        edge_references=[
            SurfaceEdgeReference(
                surface=SurfaceType.APIM,
                name=f"{normalized}-apim",
                target=f"apim://{normalized}",
            ),
            SurfaceEdgeReference(
                surface=SurfaceType.AKS_INGRESS,
                name=f"{normalized}-ingress",
                target=f"ingress://{normalized}",
            ),
        ],
    )


def _format_validation_errors(exc: ValidationError) -> str:
    details: list[str] = []
    for issue in exc.errors():
        location = ".".join(str(part) for part in issue.get("loc", ())) or "root"
        message = issue.get("msg", "invalid value")
        details.append(f"{location}: {message}")
    return "; ".join(details)


def load_surface_manifest(
    service_name: str,
    *,
    env_var: str = SURFACE_MANIFEST_ENV_VAR,
) -> ServiceSurfaceManifest:
    """Load a manifest from env JSON with safe fallback defaults.

    Raises:
        SurfaceManifestError: When JSON exists but is malformed or invalid.
    """

    raw_manifest = os.getenv(env_var)
    if raw_manifest is None or not raw_manifest.strip():
        return default_surface_manifest(service_name)

    try:
        payload = json.loads(raw_manifest)
    except json.JSONDecodeError as exc:
        raise SurfaceManifestError(
            f"{env_var} contains invalid JSON. Provide a JSON object with service_name, "
            "api_endpoints, mcp_paths, messaging_topics, and edge_references."
        ) from exc

    if not isinstance(payload, dict):
        raise SurfaceManifestError(
            f"{env_var} must be a JSON object. Received type: {type(payload).__name__}."
        )

    payload.setdefault("service_name", service_name)

    try:
        return ServiceSurfaceManifest.model_validate(payload)
    except ValidationError as exc:
        raise SurfaceManifestError(
            f"{env_var} failed validation for service '{service_name}'. "
            f"Fix these fields: {_format_validation_errors(exc)}"
        ) from exc
