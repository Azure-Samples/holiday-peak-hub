"""Foundry lifecycle helpers for service app wiring."""

import os
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent, FoundryAgentConfig

DEFAULT_FOUNDRY_MODELS = {
    "fast": "gpt-5-nano",
    "rich": "gpt-5",
}

FOUNDRY_READY_STATUSES = frozenset({"exists", "found_by_name", "created"})


def _has_resolved_agent_id(agent_id: str | None) -> bool:
    value = str(agent_id or "").strip()
    return bool(value) and value != "pending" and not value.endswith("-pending")


def build_foundry_config(agent_env: str, deployment_env: str) -> FoundryAgentConfig | None:
    """Build Foundry configuration from environment variables."""
    endpoint = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
    project_name = os.getenv("PROJECT_NAME") or os.getenv("FOUNDRY_PROJECT_NAME")
    role = "fast" if agent_env.endswith("FAST") else "rich"
    agent_id = os.getenv(agent_env)
    agent_name = os.getenv(f"FOUNDRY_AGENT_NAME_{role.upper()}")
    deployment = os.getenv(deployment_env) or DEFAULT_FOUNDRY_MODELS[role]
    stream = (os.getenv("FOUNDRY_STREAM") or "").lower() in {"1", "true", "yes"}
    if not endpoint:
        return None
    return FoundryAgentConfig(
        endpoint=endpoint,
        agent_id=agent_id or f"{role}-pending",
        agent_name=agent_name,
        deployment_name=deployment,
        project_name=project_name,
        stream=stream,
        # resolved_agent_id is intentionally omitted — only set after
        # a successful ensure/lookup call confirms the ID is valid.
    )


def strict_foundry_mode_enabled() -> bool:
    """Return whether strict Foundry enforcement is enabled."""
    return (os.getenv("FOUNDRY_STRICT_ENFORCEMENT") or "").lower() in {
        "1",
        "true",
        "yes",
    }


def auto_ensure_on_startup_enabled(*, strict_foundry_mode: bool) -> bool:
    """Return whether Foundry agent ensure should run during startup."""
    auto_ensure_default = "true" if strict_foundry_mode else "false"
    return (os.getenv("FOUNDRY_AUTO_ENSURE_ON_STARTUP") or auto_ensure_default).lower() in {
        "1",
        "true",
        "yes",
    }


def build_foundry_error_state(
    *,
    status: str,
    role: str | None = None,
    error_code: str | None = None,
    detail: str | None = None,
    hint: str | None = None,
    agent_id: str | None = None,
    agent_name: str | None = None,
) -> dict[str, Any]:
    """Return a normalized Foundry error payload for readiness reporting."""
    error_state: dict[str, Any] = {
        "status": str(status),
        "role": str(role) if role is not None else None,
        "error_code": str(error_code) if error_code else None,
        "detail": str(detail) if detail else None,
        "hint": str(hint) if hint else None,
        "agent_id": str(agent_id) if agent_id else None,
        "agent_name": str(agent_name) if agent_name else None,
    }
    return error_state


def first_foundry_error_state(
    results: Mapping[str, Mapping[str, Any]] | None,
    *,
    configured_roles: Iterable[str],
) -> dict[str, Any] | None:
    """Return the first failed Foundry ensure result for configured roles."""
    if not results:
        return None

    for role in configured_roles:
        result = results.get(role)
        if result is None:
            continue
        status = str(result.get("status") or "unknown")
        if status in FOUNDRY_READY_STATUSES:
            continue
        return build_foundry_error_state(
            status=status,
            role=role,
            error_code=str(result.get("error_code")) if result.get("error_code") else None,
            detail=str(result.get("detail")) if result.get("detail") else None,
            hint=str(result.get("hint")) if result.get("hint") else None,
            agent_id=str(result.get("agent_id")) if result.get("agent_id") else None,
            agent_name=str(result.get("agent_name")) if result.get("agent_name") else None,
        )
    return None


def exception_to_foundry_error_state(
    exc: BaseException,
    *,
    status: str,
    role: str | None = None,
) -> dict[str, Any]:
    """Return a normalized error payload from an unexpected Foundry exception."""
    error_code = getattr(exc, "code", None)
    if error_code is not None:
        error_code = str(error_code)
    return build_foundry_error_state(
        status=status,
        role=role,
        error_code=error_code,
        detail=str(exc),
    )


@dataclass
class FoundryReadinessSnapshot:
    """Data-oriented snapshot of Foundry runtime readiness for a service."""

    required: bool
    strict_mode: bool
    project_configured: bool
    endpoint_configured: bool
    configured_roles: tuple[str, ...]
    resolved_roles: tuple[str, ...]
    unresolved_roles: tuple[str, ...]
    agent_targets_bound: bool
    runtime_resolution_required: bool
    auto_ensure_on_startup: bool
    last_error: dict[str, Any] | None = None

    @property
    def enforced(self) -> bool:
        return self.required or self.strict_mode

    @property
    def ready(self) -> bool:
        if not self.project_configured or not self.configured_roles:
            return False
        return not self.runtime_resolution_required

    def to_payload(self) -> dict[str, Any]:
        return {
            "required": self.required,
            "strict_mode": self.strict_mode,
            "enforced": self.enforced,
            "ready": self.ready,
            "project_configured": self.project_configured,
            "endpoint_configured": self.endpoint_configured,
            "configured_roles": list(self.configured_roles),
            "resolved_roles": list(self.resolved_roles),
            "unresolved_roles": list(self.unresolved_roles),
            "agent_targets_bound": self.agent_targets_bound,
            "runtime_resolution_required": self.runtime_resolution_required,
            "auto_ensure_on_startup": self.auto_ensure_on_startup,
            "last_error": self.last_error,
        }


def build_foundry_readiness_snapshot(
    *,
    agent: BaseRetailAgent,
    slm_config: FoundryAgentConfig | None,
    llm_config: FoundryAgentConfig | None,
    require_foundry_readiness: bool,
    strict_foundry_mode: bool,
    auto_ensure_on_startup: bool,
    last_error: dict[str, Any] | None,
) -> FoundryReadinessSnapshot:
    """Build a Foundry readiness snapshot from configured roles and bound targets."""
    configured_roles: list[str] = []
    resolved_roles: list[str] = []
    unresolved_roles: list[str] = []

    role_state = {
        "fast": (slm_config, getattr(agent, "slm", None)),
        "rich": (llm_config, getattr(agent, "llm", None)),
    }

    for role, (config, target) in role_state.items():
        if config is None:
            continue
        configured_roles.append(role)
        if _has_resolved_agent_id(config.runtime_agent_id) and target is not None:
            resolved_roles.append(role)
            continue
        unresolved_roles.append(role)

    endpoint_configured = any(
        bool(str(config.endpoint or "").strip())
        for config in (slm_config, llm_config)
        if config is not None
    )

    runtime_resolution_required = bool(unresolved_roles) and (
        not resolved_roles or require_foundry_readiness or strict_foundry_mode
    )

    return FoundryReadinessSnapshot(
        required=require_foundry_readiness,
        strict_mode=bool(strict_foundry_mode) and bool(configured_roles),
        project_configured=bool(configured_roles),
        endpoint_configured=endpoint_configured,
        configured_roles=tuple(configured_roles),
        resolved_roles=tuple(resolved_roles),
        unresolved_roles=tuple(unresolved_roles),
        agent_targets_bound=bool(resolved_roles),
        runtime_resolution_required=runtime_resolution_required,
        auto_ensure_on_startup=auto_ensure_on_startup,
        last_error=last_error,
    )


@dataclass
class FoundryLifecycleManager:
    """Encapsulates Foundry ensure and model-target wiring behavior."""

    service_name: str
    agent: BaseRetailAgent
    slm_config: FoundryAgentConfig | None
    llm_config: FoundryAgentConfig | None
    ensure_foundry_agent_fn: Callable[..., Awaitable[dict[str, Any]]]
    build_foundry_model_target_fn: Callable[[FoundryAgentConfig], Any]

    @property
    def role_to_config(self) -> dict[str, FoundryAgentConfig | None]:
        return {
            "fast": self.slm_config,
            "rich": self.llm_config,
        }

    async def ensure_role(
        self,
        *,
        selected_role: str,
        config: FoundryAgentConfig,
        instructions: str,
        create_if_missing: bool,
        name_override: str | None = None,
        model_override: str | None = None,
    ) -> dict[str, Any]:
        """Ensure a single Foundry role and wire model target when available."""
        target_name = name_override or config.agent_name or f"{self.service_name}-{selected_role}"
        target_model = (
            model_override or config.deployment_name or DEFAULT_FOUNDRY_MODELS[selected_role]
        )
        config.agent_name = str(target_name)
        config.deployment_name = str(target_model)

        ensure_result = await self.ensure_foundry_agent_fn(
            config,
            agent_name=config.agent_name,
            instructions=instructions,
            create_if_missing=create_if_missing,
            model=config.deployment_name,
        )

        ensured_id = ensure_result.get("agent_id")
        ensured_name = ensure_result.get("agent_name")
        if ensured_id:
            config.agent_id = str(ensured_id)
            config.resolved_agent_id = str(ensured_id)
        if ensured_name:
            config.agent_name = str(ensured_name)

        if _has_resolved_agent_id(config.runtime_agent_id):
            model_target = self.build_foundry_model_target_fn(config)
            if selected_role == "fast":
                self.agent.slm = model_target
            else:
                self.agent.llm = model_target

        return ensure_result

    async def ensure_startup_roles(self, instructions: str) -> dict[str, dict[str, Any]]:
        """Ensure all configured roles during app startup."""
        results: dict[str, dict[str, Any]] = {}
        for selected_role, config in self.role_to_config.items():
            if config is None:
                continue
            results[selected_role] = await self.ensure_role(
                selected_role=selected_role,
                config=config,
                instructions=instructions,
                create_if_missing=True,
            )
        return results
