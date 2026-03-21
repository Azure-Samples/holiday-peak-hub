"""Foundry lifecycle helpers for service app wiring."""

import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from holiday_peak_lib.agents import BaseRetailAgent, FoundryAgentConfig

DEFAULT_FOUNDRY_MODELS = {
    "fast": "gpt-5-nano",
    "rich": "gpt-5",
}


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
        agent_id=agent_id or agent_name or f"{role}-pending",
        agent_name=agent_name,
        deployment_name=deployment,
        project_name=project_name,
        stream=stream,
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
        if ensured_name:
            config.agent_name = str(ensured_name)

        if config.agent_id:
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
