"""Foundry model-deployment readiness helpers for service app wiring."""

import os
from dataclasses import dataclass
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent, FoundryAgentConfig

DEFAULT_FOUNDRY_MODELS = {
    "fast": "gpt-5-nano",
    "rich": "gpt-5",
}


def build_foundry_config(agent_env: str, deployment_env: str) -> FoundryAgentConfig | None:
    """Build direct-model Foundry configuration from environment variables."""
    endpoint = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
    project_name = os.getenv("PROJECT_NAME") or os.getenv("FOUNDRY_PROJECT_NAME")
    role = "fast" if agent_env.endswith("FAST") else "rich"
    agent_id = os.getenv(agent_env) or f"{role}-pending"
    agent_name = os.getenv(f"FOUNDRY_AGENT_NAME_{role.upper()}")
    deployment = os.getenv(deployment_env)
    if not endpoint:
        return None
    return FoundryAgentConfig(
        endpoint=endpoint,
        agent_id=agent_id,
        agent_name=agent_name,
        deployment_name=deployment,
        project_name=project_name,
    )


def strict_foundry_mode_enabled() -> bool:
    """Return whether direct-model Foundry readiness enforcement is enabled."""
    return (os.getenv("FOUNDRY_STRICT_ENFORCEMENT") or "").lower() in {
        "1",
        "true",
        "yes",
    }


@dataclass
class FoundryReadinessSnapshot:
    """Data-oriented snapshot of direct-model target readiness for a service."""

    required: bool
    strict_mode: bool
    project_configured: bool
    endpoint_configured: bool
    configured_roles: tuple[str, ...]
    bound_roles: tuple[str, ...]
    unbound_roles: tuple[str, ...]
    agent_targets_bound: bool
    runtime_resolution_required: bool
    auto_ensure_on_startup: bool = False
    last_error: dict[str, Any] | None = None

    @property
    def enforced(self) -> bool:
        return self.required or self.strict_mode

    @property
    def ready(self) -> bool:
        if not self.project_configured or not self.endpoint_configured:
            return False
        if self.enforced:
            return not self.runtime_resolution_required
        return self.agent_targets_bound

    @property
    def resolved_roles(self) -> tuple[str, ...]:
        """Compatibility alias for callers that still read resolved role names."""
        return self.bound_roles

    @property
    def unresolved_roles(self) -> tuple[str, ...]:
        """Compatibility alias for callers that still read unresolved role names."""
        return self.unbound_roles

    def to_payload(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "strict_mode": self.strict_mode,
            "enforced": self.enforced,
            "ready": self.ready,
            "project_configured": self.project_configured,
            "endpoint_configured": self.endpoint_configured,
            "configured_roles": list(self.configured_roles),
            "bound_roles": list(self.bound_roles),
            "unbound_roles": list(self.unbound_roles),
            "resolved_roles": list(self.bound_roles),
            "unresolved_roles": list(self.unbound_roles),
            "agent_targets_bound": self.agent_targets_bound,
            "runtime_resolution_required": self.runtime_resolution_required,
            "auto_ensure_on_startup": self.auto_ensure_on_startup,
            "last_error": self.last_error,
        }


def _is_bound_direct_target(target: Any) -> bool:
    return target is not None and getattr(target, "provider", None) == "maf-direct"


def build_foundry_readiness_snapshot(
    *,
    agent: BaseRetailAgent,
    slm_config: FoundryAgentConfig | None,
    llm_config: FoundryAgentConfig | None,
    require_foundry_readiness: bool,
    strict_foundry_mode: bool,
    auto_ensure_on_startup: bool = False,
    last_error: dict[str, Any] | None = None,
) -> FoundryReadinessSnapshot:
    """Build direct-model readiness from configured roles and bound targets."""
    configured_roles: list[str] = []
    bound_roles: list[str] = []
    unbound_roles: list[str] = []

    role_state = {
        "fast": (slm_config, getattr(agent, "slm", None)),
        "rich": (llm_config, getattr(agent, "llm", None)),
    }

    for role, (config, target) in role_state.items():
        if config is None:
            continue
        configured_roles.append(role)
        if config.deployment_name and _is_bound_direct_target(target):
            bound_roles.append(role)
            continue
        unbound_roles.append(role)

    endpoint_configured = any(
        bool(str(config.endpoint or "").strip())
        for config in (slm_config, llm_config)
        if config is not None
    )
    enforced = bool(require_foundry_readiness or strict_foundry_mode)
    agent_targets_bound = bool(configured_roles) and not unbound_roles
    runtime_resolution_required = enforced and bool(unbound_roles)

    snapshot = FoundryReadinessSnapshot(
        required=require_foundry_readiness,
        strict_mode=bool(strict_foundry_mode) and bool(configured_roles),
        project_configured=bool(configured_roles),
        endpoint_configured=endpoint_configured,
        configured_roles=tuple(configured_roles),
        bound_roles=tuple(bound_roles),
        unbound_roles=tuple(unbound_roles),
        agent_targets_bound=agent_targets_bound,
        runtime_resolution_required=runtime_resolution_required,
        auto_ensure_on_startup=auto_ensure_on_startup,
        last_error=last_error,
    )
    return snapshot
