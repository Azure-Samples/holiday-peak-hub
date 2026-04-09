"""Shared pytest fixtures for app-level smoke tests."""

from __future__ import annotations

import os

import pytest
from holiday_peak_lib.app_factory_components.foundry_lifecycle import (
    FoundryReadinessSnapshot,
)

_FOUNDRY_ENV_KEYS = (
    "PROJECT_ENDPOINT",
    "FOUNDRY_ENDPOINT",
    "PROJECT_NAME",
    "FOUNDRY_PROJECT_NAME",
    "FOUNDRY_AGENT_ID_FAST",
    "FOUNDRY_AGENT_NAME_FAST",
    "MODEL_DEPLOYMENT_NAME_FAST",
    "FOUNDRY_AGENT_ID_RICH",
    "FOUNDRY_AGENT_NAME_RICH",
    "MODEL_DEPLOYMENT_NAME_RICH",
    "FOUNDRY_STREAM",
)
_FOUNDRY_FLAG_OVERRIDES = {
    "FOUNDRY_AUTO_ENSURE_ON_STARTUP": "false",
    "FOUNDRY_STRICT_ENFORCEMENT": "false",
}
_DOTENV_EXTERNAL_RUNTIME_ENV_KEYS = (
    "APPLICATIONINSIGHTS_CONNECTION_STRING",
    "APPINSIGHTS_CONNECTION_STRING",
    "REDIS_URL",
    "COSMOS_ACCOUNT_URI",
    "COSMOS_DATABASE",
    "COSMOS_CONTAINER",
    "BLOB_ACCOUNT_URL",
    "BLOB_CONTAINER",
)


def _scrub_ambient_foundry_environment() -> None:
    for env_name in _FOUNDRY_ENV_KEYS:
        os.environ.pop(env_name, None)

    for env_name, env_value in _FOUNDRY_FLAG_OVERRIDES.items():
        os.environ[env_name] = env_value


def _mask_ambient_dotenv_runtime_environment() -> None:
    for env_name in _DOTENV_EXTERNAL_RUNTIME_ENV_KEYS:
        os.environ[env_name] = ""


_scrub_ambient_foundry_environment()
_mask_ambient_dotenv_runtime_environment()


@pytest.fixture(autouse=True)
def isolate_dotenv_external_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    # No GoF pattern applies — fail-closed env masking keeps app smoke tests
    # hermetic against dotenv-backed external service settings.
    for env_name in _DOTENV_EXTERNAL_RUNTIME_ENV_KEYS:
        monkeypatch.setenv(env_name, "")


@pytest.fixture(autouse=True)
def mock_eventhub_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    # No GoF pattern applies — app tests should not open real Event Hubs links.
    async def _noop_start(_self) -> None:  # noqa: ANN001
        return None

    monkeypatch.setenv("EVENT_HUB_NAMESPACE", "test-retail.servicebus.windows.net")
    monkeypatch.setenv(
        "PLATFORM_JOBS_EVENT_HUB_NAMESPACE",
        "test-platform-jobs.servicebus.windows.net",
    )
    monkeypatch.delenv("EVENTHUB_NAMESPACE", raising=False)
    monkeypatch.delenv("EVENTHUB_CONNECTION_STRING", raising=False)
    monkeypatch.setattr(
        "holiday_peak_lib.utils.event_hub.EventHubSubscriber.start",
        _noop_start,
    )


@pytest.fixture(autouse=True)
def isolate_foundry_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    # No GoF pattern applies — this keeps app tests independent from workstation
    # Foundry configuration and prevents startup auto-ensure network calls.
    async def _noop_ensure(config: object, *_args: object, **kwargs: object) -> dict[str, object]:
        agent_name = str(
            kwargs.get("agent_name") or getattr(config, "agent_name", "") or "test-foundry-agent"
        )
        agent_id = str(
            getattr(config, "runtime_agent_id", None)
            or getattr(config, "agent_id", None)
            or f"{agent_name}-id"
        )
        return {
            "status": "exists",
            "agent_id": agent_id,
            "agent_name": agent_name,
            "created": False,
            "foundry_ready": True,
        }

    for env_name in _FOUNDRY_ENV_KEYS:
        monkeypatch.delenv(env_name, raising=False)

    for env_name, env_value in _FOUNDRY_FLAG_OVERRIDES.items():
        monkeypatch.setenv(env_name, env_value)

    monkeypatch.setattr("holiday_peak_lib.app_factory.ensure_foundry_agent", _noop_ensure)
    monkeypatch.setattr("holiday_peak_lib.agents.foundry.ensure_foundry_agent", _noop_ensure)


@pytest.fixture
def mock_foundry_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    # No GoF pattern applies — this pytest seam keeps app smoke tests focused on
    # service behavior once the shared Foundry readiness gate is satisfied.
    def _ready_foundry_snapshot(
        **kwargs: object,
    ) -> FoundryReadinessSnapshot:
        require_foundry_readiness = bool(kwargs.get("require_foundry_readiness", False))
        strict_foundry_mode = bool(kwargs.get("strict_foundry_mode", False))
        auto_ensure_on_startup = bool(kwargs.get("auto_ensure_on_startup", False))
        last_error = kwargs.get("last_error")
        if last_error is not None and not isinstance(last_error, dict):
            last_error = None

        return FoundryReadinessSnapshot(
            required=require_foundry_readiness,
            strict_mode=strict_foundry_mode,
            project_configured=True,
            endpoint_configured=True,
            configured_roles=("fast",),
            resolved_roles=("fast",),
            unresolved_roles=(),
            agent_targets_bound=True,
            runtime_resolution_required=False,
            auto_ensure_on_startup=auto_ensure_on_startup,
            last_error=last_error,
        )

    monkeypatch.setattr(
        "holiday_peak_lib.app_factory.build_foundry_readiness_snapshot",
        _ready_foundry_snapshot,
    )
