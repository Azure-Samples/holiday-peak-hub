"""Configuration helpers for Azure AI Foundry model deployments."""

import inspect
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

# NOTE: NonRecordingSpan.attributes patch is applied in holiday_peak_lib/__init__.py
# to guarantee it executes before any SDK instrumentation regardless of import order.

_FOUNDRY_PROJECT_HOST_SUFFIX = ".services.ai.azure.com"
_FOUNDRY_RESOURCE_HOST_SUFFIX = ".cognitiveservices.azure.com"
_FOUNDRY_PROJECT_PATH_PREFIX = "/api/projects/"


class FoundryConfigurationError(ValueError):
    """Raised when Foundry settings do not resolve to a valid project endpoint."""


@dataclass(frozen=True)
class _FoundryProjectEndpoint:
    endpoint: str
    project_name: str


def _normalize_foundry_project_endpoint(
    endpoint: str, project_name: str | None
) -> _FoundryProjectEndpoint:
    """Return a canonical project-scoped Foundry endpoint.

    Accepts either a full project endpoint or an Azure AI Services account
    endpoint that can be deterministically expanded when the project name is
    available.
    """

    # No GoF pattern applies here; this is a simple configuration boundary normalizer.
    raw_endpoint = str(endpoint or "").strip()
    raw_project_name = str(project_name or "").strip() or None
    if not raw_endpoint:
        raise FoundryConfigurationError("PROJECT_ENDPOINT/FOUNDRY_ENDPOINT is required")

    parsed = urlsplit(raw_endpoint)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise FoundryConfigurationError(
            "PROJECT_ENDPOINT/FOUNDRY_ENDPOINT must be an absolute https URL"
        )
    if parsed.query or parsed.fragment:
        raise FoundryConfigurationError(
            "PROJECT_ENDPOINT/FOUNDRY_ENDPOINT must not include query parameters or fragments"
        )

    hostname = parsed.hostname.lower()
    if hostname.endswith(_FOUNDRY_RESOURCE_HOST_SUFFIX):
        resource_name = hostname[: -len(_FOUNDRY_RESOURCE_HOST_SUFFIX)]
        normalized_host = f"{resource_name}{_FOUNDRY_PROJECT_HOST_SUFFIX}"
    elif hostname.endswith(_FOUNDRY_PROJECT_HOST_SUFFIX):
        normalized_host = hostname
    else:
        raise FoundryConfigurationError(
            "PROJECT_ENDPOINT/FOUNDRY_ENDPOINT must use a '.services.ai.azure.com' "
            "project host or a '.cognitiveservices.azure.com' resource host"
        )

    if parsed.port is not None:
        normalized_host = f"{normalized_host}:{parsed.port}"

    resolved_project_name: str | None = None
    path = parsed.path or ""
    if path not in {"", "/"}:
        if not path.startswith(_FOUNDRY_PROJECT_PATH_PREFIX):
            raise FoundryConfigurationError(
                "PROJECT_ENDPOINT/FOUNDRY_ENDPOINT must be either a Foundry account "
                "host or a project endpoint ending with '/api/projects/<project-name>'"
            )

        project_segment = path[len(_FOUNDRY_PROJECT_PATH_PREFIX) :].strip("/")
        if not project_segment or "/" in project_segment:
            raise FoundryConfigurationError(
                "PROJECT_ENDPOINT/FOUNDRY_ENDPOINT must end with " "'/api/projects/<project-name>'"
            )
        resolved_project_name = unquote(project_segment)

    if raw_project_name and resolved_project_name and raw_project_name != resolved_project_name:
        raise FoundryConfigurationError(
            "PROJECT_NAME/FOUNDRY_PROJECT_NAME must match the project encoded in "
            "PROJECT_ENDPOINT/FOUNDRY_ENDPOINT"
        )

    resolved_project_name = resolved_project_name or raw_project_name
    if not resolved_project_name:
        raise FoundryConfigurationError(
            "PROJECT_NAME/FOUNDRY_PROJECT_NAME is required when "
            "PROJECT_ENDPOINT/FOUNDRY_ENDPOINT is not already project-scoped"
        )

    normalized_path = f"{_FOUNDRY_PROJECT_PATH_PREFIX}{quote(resolved_project_name, safe='')}"
    normalized_endpoint = urlunsplit(("https", normalized_host, normalized_path, "", ""))
    return _FoundryProjectEndpoint(
        endpoint=normalized_endpoint,
        project_name=resolved_project_name,
    )


def _normalize_foundry_reference(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _is_pending_agent_reference(value: str | None) -> bool:
    normalized = _normalize_foundry_reference(value)
    return normalized in {None, "pending"} or str(normalized).endswith("-pending")


@dataclass
class FoundryAgentConfig:
    """Configuration for direct model invocation against a Foundry project.

    The active runtime path uses Foundry as a model deployment plane through
    ``DirectModelInvoker``. Agent identifier/name fields are retained as
    compatibility metadata for existing callers, but readiness and invocation
    depend on ``endpoint`` and ``deployment_name``.
    """

    endpoint: str
    agent_id: str = "pending"
    agent_name: str | None = None
    deployment_name: str | None = None
    project_name: str | None = None
    stream: bool = True
    credential: Any | None = None
    resolved_agent_id: str | None = None
    max_output_tokens: int | None = None

    def __post_init__(self) -> None:
        self.apply_project_contract()

        if self.resolved_agent_id is not None:
            configured_agent_name = _normalize_foundry_reference(self.agent_name)
            normalized_runtime_id = _normalize_foundry_reference(self.resolved_agent_id)
            if (
                normalized_runtime_id
                and not _is_pending_agent_reference(normalized_runtime_id)
                and normalized_runtime_id != configured_agent_name
            ):
                self.resolved_agent_id = normalized_runtime_id
            else:
                self.resolved_agent_id = None

    @property
    def runtime_agent_id(self) -> str | None:
        """Return an explicitly confirmed legacy agent id, when one exists."""
        return _normalize_foundry_reference(self.resolved_agent_id)

    def apply_project_contract(self) -> None:
        """Normalize endpoint/project settings to the canonical Foundry contract."""
        resolved = _normalize_foundry_project_endpoint(self.endpoint, self.project_name)
        self.endpoint = resolved.endpoint
        self.project_name = resolved.project_name

    @classmethod
    def from_env(cls) -> "FoundryAgentConfig":
        """Create a config from environment variables.

        :raises ValueError: If the project endpoint is missing or invalid.
        :returns: A validated :class:`FoundryAgentConfig`.
        """
        endpoint = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
        project_name = os.getenv("PROJECT_NAME") or os.getenv("FOUNDRY_PROJECT_NAME")
        agent_id = os.getenv("FOUNDRY_AGENT_ID") or os.getenv("AGENT_ID") or "pending"
        agent_name = os.getenv("FOUNDRY_AGENT_NAME")
        deployment = os.getenv("MODEL_DEPLOYMENT_NAME")
        stream_raw = os.getenv("FOUNDRY_STREAM", "true").lower()
        stream = stream_raw not in {"0", "false", "no"}
        if not endpoint:
            raise ValueError("PROJECT_ENDPOINT/FOUNDRY_ENDPOINT is required")
        return cls(
            endpoint=endpoint,
            agent_id=agent_id,
            agent_name=agent_name,
            deployment_name=deployment,
            project_name=project_name,
            stream=stream,
        )


async def _maybe_await(value: Any) -> Any:
    """Await *value* when it is awaitable; otherwise return it as-is."""
    if inspect.isawaitable(value):
        return await value
    return value


__all__ = ("FoundryAgentConfig", "FoundryConfigurationError")
