"""Helpers for Azure AI Foundry (Microsoft Agent Framework) integration.

This module keeps Azure AI Projects imports lazy to avoid hard failures
when the SDK is not installed. It provides a small adapter that turns a Foundry
Agent into a ``ModelTarget`` invoker for ``BaseRetailAgent``.
"""

from __future__ import annotations

import inspect
import os
from dataclasses import dataclass
from time import perf_counter
from typing import Any
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from azure.ai.projects.aio import AIProjectClient
from azure.core.exceptions import HttpResponseError
from azure.identity.aio import DefaultAzureCredential

from .base_agent import ModelTarget

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
                "PROJECT_ENDPOINT/FOUNDRY_ENDPOINT must end with '/api/projects/<project-name>'"
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
    """Configuration required to call a Foundry Agent.

    This is designed for the Azure AI Foundry Agents v2 surface via
    :class:`azure.ai.projects.aio.AIProjectClient` and its ``agents`` subclient.

    Env vars (defaults):
        - PROJECT_ENDPOINT or FOUNDRY_ENDPOINT: Azure AI Foundry project endpoint, or
            an Azure AI Services account endpoint that can be expanded to a project
            endpoint when the project name is supplied.
        - PROJECT_NAME or FOUNDRY_PROJECT_NAME: Azure AI Foundry project name.
            Required when the endpoint is not already project-scoped.
    - FOUNDRY_AGENT_ID: Agent ID created in the project.
    - FOUNDRY_AGENT_NAME: Optional name-only lookup/provisioning reference.
    - MODEL_DEPLOYMENT_NAME: Optional model deployment associated with the agent.
    - FOUNDRY_STREAM: ``true`` to enable streaming aggregation by default.

    ``agent_id`` carries the configured or ensured identifier reference, while
    ``resolved_agent_id`` tracks when that reference is safe to bind as a live
    runtime target.
    """

    endpoint: str
    agent_id: str
    agent_name: str | None = None
    deployment_name: str | None = None
    project_name: str | None = None
    stream: bool = False
    credential: Any | None = None
    resolved_agent_id: str | None = None

    def __post_init__(self) -> None:
        self.apply_project_contract()

        configured_agent_name = _normalize_foundry_reference(self.agent_name)
        if self.resolved_agent_id is not None:
            normalized_runtime_id = _normalize_foundry_reference(self.resolved_agent_id)
            if (
                normalized_runtime_id
                and not _is_pending_agent_reference(normalized_runtime_id)
                and normalized_runtime_id != configured_agent_name
            ):
                self.resolved_agent_id = normalized_runtime_id
            else:
                self.resolved_agent_id = None
            return

        configured_agent_id = _normalize_foundry_reference(self.agent_id)
        if (
            configured_agent_id
            and not _is_pending_agent_reference(configured_agent_id)
            and configured_agent_id != configured_agent_name
        ):
            self.resolved_agent_id = configured_agent_id

    @property
    def runtime_agent_id(self) -> str | None:
        return _normalize_foundry_reference(self.resolved_agent_id)

    def apply_project_contract(self) -> None:
        """Normalize endpoint/project settings to the canonical Foundry contract."""
        resolved = _normalize_foundry_project_endpoint(self.endpoint, self.project_name)
        self.endpoint = resolved.endpoint
        self.project_name = resolved.project_name

    @classmethod
    def from_env(cls) -> "FoundryAgentConfig":
        """Create a config from environment variables.

        :raises ValueError: If the project endpoint or agent id is missing.
        :returns: A validated :class:`FoundryAgentConfig`.
        """
        endpoint = os.getenv("PROJECT_ENDPOINT") or os.getenv("FOUNDRY_ENDPOINT")
        project_name = os.getenv("PROJECT_NAME") or os.getenv("FOUNDRY_PROJECT_NAME")
        agent_id = os.getenv("FOUNDRY_AGENT_ID") or os.getenv("AGENT_ID")
        agent_name = os.getenv("FOUNDRY_AGENT_NAME")
        deployment = os.getenv("MODEL_DEPLOYMENT_NAME")
        stream = (os.getenv("FOUNDRY_STREAM") or "").lower() in {"1", "true", "yes"}
        if not endpoint:
            raise ValueError("PROJECT_ENDPOINT/FOUNDRY_ENDPOINT is required")
        if not agent_id and not agent_name:
            raise ValueError("FOUNDRY_AGENT_ID or FOUNDRY_AGENT_NAME is required")
        return cls(
            endpoint=endpoint,
            agent_id=agent_id or "pending",
            agent_name=agent_name,
            deployment_name=deployment,
            project_name=project_name,
            stream=stream,
            resolved_agent_id=agent_id or None,
        )


def _ensure_client(config: FoundryAgentConfig):
    """Create an async :class:`AIProjectClient` with Entra ID credentials.

    We load the SDK lazily so consumers without Foundry dependencies can import
    this module safely. The project client is required for Agents v2 and exposes
    an ``agents`` subclient used for threads, messages, and runs.

    :param config: Foundry configuration.
    :returns: A configured :class:`AIProjectClient`.
    :raises ImportError: If the required SDK packages are missing.
    """
    try:
        config.apply_project_contract()
        credential = config.credential or DefaultAzureCredential()
        client = AIProjectClient(endpoint=config.endpoint, credential=credential)
        if config.credential is None:
            setattr(client, "_holiday_peak_owned_credential", credential)
        return client
    except ImportError as exc:  # pragma: no cover - guard for missing SDK
        raise ImportError(
            "azure-ai-projects and azure-identity are required for Foundry integration"
        ) from exc


def _ensure_agents_client(config: FoundryAgentConfig):
    """Create an async Azure AI Agents client with Entra ID credentials.

    :param config: Foundry configuration.
    :returns: A configured ``azure.ai.agents.aio.AgentsClient``.
    :raises ImportError: If the required SDK packages are missing.
    """
    try:
        from azure.ai.agents.aio import AgentsClient

        config.apply_project_contract()
        credential = config.credential or DefaultAzureCredential()
        client = AgentsClient(endpoint=config.endpoint, credential=credential)
        if config.credential is None:
            setattr(client, "_holiday_peak_owned_credential", credential)
        return client
    except ImportError as exc:  # pragma: no cover - guard for missing SDK
        raise ImportError(
            "azure-ai-agents and azure-identity are required for Foundry runtime integration"
        ) from exc


async def _close_owned_credential(client: Any) -> None:
    credential = getattr(client, "_holiday_peak_owned_credential", None)
    if credential is None:
        return
    close_method = getattr(credential, "close", None)
    if callable(close_method):
        await _maybe_await(close_method())


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


async def _call_first_available(
    target: Any, method_names: tuple[str, ...], *args: Any, **kwargs: Any
) -> Any:
    for method_name in method_names:
        method = getattr(target, method_name, None)
        if callable(method):
            return await _maybe_await(method(*args, **kwargs))
    raise AttributeError(f"None of methods {method_names} found on {type(target).__name__}")


def _is_agents_runtime_client(client: Any) -> bool:
    return all(hasattr(client, operation) for operation in ("threads", "messages", "runs"))


def _to_string_enum(value: Any) -> str:
    if value is None:
        return ""
    enum_value = getattr(value, "value", None)
    if enum_value is not None:
        return str(enum_value)
    return str(value)


def _to_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value

    for method_name in ("model_dump", "as_dict", "to_dict"):
        method = getattr(value, method_name, None)
        if callable(method):
            payload = method()
            if isinstance(payload, dict):
                return payload

    payload = getattr(value, "__dict__", None)
    if isinstance(payload, dict):
        return dict(payload)
    return {}


def _message_text_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        text_block = value.get("text")
        if isinstance(text_block, dict):
            inner_value = text_block.get("value")
            if inner_value:
                return str(inner_value)
        raw_value = value.get("value")
        if raw_value:
            return str(raw_value)

    text_block = getattr(value, "text", None)
    text_value = getattr(text_block, "value", None) if text_block is not None else None
    if text_value:
        return str(text_value)

    raw_value = getattr(value, "value", None)
    if raw_value:
        return str(raw_value)
    return None


async def _get_last_assistant_text(messages_client: Any, thread_id: str) -> str | None:
    try:
        text_content = await _call_first_available(
            messages_client,
            ("get_last_message_text_by_role",),
            thread_id=thread_id,
            role="assistant",
        )
    except (AttributeError, HttpResponseError, TypeError, ValueError):
        return None

    return _message_text_value(text_content)


def _agent_id(agent_obj: Any) -> str | None:
    if agent_obj is None:
        return None
    if isinstance(agent_obj, dict):
        value = agent_obj.get("id")
        return str(value) if value else None
    value = getattr(agent_obj, "id", None)
    return str(value) if value else None


def _agent_name(agent_obj: Any) -> str | None:
    if agent_obj is None:
        return None
    if isinstance(agent_obj, dict):
        value = agent_obj.get("name")
        return str(value) if value else None
    value = getattr(agent_obj, "name", None)
    return str(value) if value else None


def _agent_name_from_identifier(identifier: str | None) -> str | None:
    if not identifier:
        return None
    text = str(identifier)
    if ":" in text:
        return text.split(":", 1)[0]
    return text


async def _list_agents(agents_client: Any) -> list[Any]:
    listed = await _call_first_available(agents_client, ("list", "list_agents"))
    if listed is None:
        return []
    if hasattr(listed, "__aiter__"):
        output = []
        async for item in listed:
            output.append(item)
        return output
    if isinstance(listed, list):
        return listed
    if isinstance(listed, tuple):
        return list(listed)
    items = getattr(listed, "items", None)
    if isinstance(items, list):
        return items
    return list(listed) if hasattr(listed, "__iter__") else []


def _is_service_invocation_exception(exc: BaseException) -> bool:
    if isinstance(exc, HttpResponseError):
        error_code = getattr(exc, "error", None)
        error_code = getattr(error_code, "code", None) or getattr(exc, "code", None)
        if error_code == "UserError.ServiceInvocationException":
            return True
    return "ServiceInvocationException" in str(exc)


async def ensure_foundry_agent(
    config: FoundryAgentConfig,
    *,
    agent_name: str | None = None,
    instructions: str | None = None,
    create_if_missing: bool = False,
    model: str | None = None,
) -> dict[str, Any]:
    """Ensure a Foundry agent exists for the given config.

    Lookup order:
    1) By configured ``agent_id``
    2) By ``agent_name`` when provided
    3) Create new agent when ``create_if_missing`` is true
    """

    project_client = _ensure_client(config)
    configured_agent_id = config.runtime_agent_id
    resolved_agent_name = (
        agent_name or config.agent_name or _agent_name_from_identifier(config.agent_id)
    )
    try:
        async with project_client:
            agents_client = project_client.agents

            supports_v2 = callable(getattr(agents_client, "create_version", None))
            if not supports_v2:
                return {
                    "status": "sdk_outdated",
                    "agent_id": None,
                    "agent_name": resolved_agent_name,
                    "created": False,
                    "detail": (
                        "Agents V2 requires azure-ai-projects>=2.0.0b4. "
                        "Upgrade the SDK in this environment."
                    ),
                }

            if configured_agent_id or resolved_agent_name:
                try:
                    for candidate in await _list_agents(agents_client):
                        if (
                            configured_agent_id
                            and (_agent_id(candidate) or "") == configured_agent_id
                        ):
                            return {
                                "status": "exists",
                                "agent_id": _agent_id(candidate),
                                "agent_name": _agent_name(candidate),
                                "created": False,
                                "api_version": "v2",
                            }
                        if (_agent_name(candidate) or "") == resolved_agent_name:
                            return {
                                "status": "found_by_name",
                                "agent_id": _agent_id(candidate),
                                "agent_name": _agent_name(candidate),
                                "created": False,
                                "api_version": "v2",
                            }
                except HttpResponseError as exc:
                    if _is_service_invocation_exception(exc):
                        return {
                            "status": "agents_service_unavailable",
                            "agent_id": None,
                            "agent_name": resolved_agent_name,
                            "created": False,
                            "error_code": "UserError.ServiceInvocationException",
                            "detail": str(exc),
                        }
                    if not create_if_missing:
                        return {
                            "status": "list_failed",
                            "agent_id": None,
                            "agent_name": resolved_agent_name,
                            "created": False,
                        }
                except (AttributeError, TypeError, ValueError, RuntimeError):
                    if not create_if_missing:
                        return {
                            "status": "list_failed",
                            "agent_id": None,
                            "agent_name": resolved_agent_name,
                            "created": False,
                        }

            if not create_if_missing:
                return {
                    "status": "missing",
                    "agent_id": None,
                    "agent_name": resolved_agent_name,
                    "created": False,
                }

            resolved_model = model or config.deployment_name
            if not resolved_model:
                return {
                    "status": "missing_model",
                    "agent_id": None,
                    "agent_name": resolved_agent_name or f"agent-{config.agent_id}",
                    "created": False,
                }

            try:
                try:
                    from azure.ai.projects.models import PromptAgentDefinition

                    definition: Any = PromptAgentDefinition(
                        model=resolved_model,
                        instructions=instructions or "You are a helpful retail assistant.",
                    )
                except (ImportError, AttributeError, TypeError, ValueError):
                    definition = {
                        "kind": "prompt",
                        "model": resolved_model,
                        "instructions": instructions or "You are a helpful retail assistant.",
                    }

                created = await _call_first_available(
                    agents_client,
                    ("create_version",),
                    agent_name=resolved_agent_name or f"agent-{config.agent_id}",
                    definition=definition,
                )

                return {
                    "status": "created",
                    "agent_id": _agent_id(created),
                    "agent_name": _agent_name(created) or resolved_agent_name,
                    "created": True,
                    "api_version": "v2",
                }
            except HttpResponseError as exc:
                message = str(exc)
                if _is_service_invocation_exception(exc):
                    return {
                        "status": "agents_service_unavailable",
                        "agent_id": None,
                        "agent_name": resolved_agent_name or f"agent-{config.agent_id}",
                        "created": False,
                        "error_code": "UserError.ServiceInvocationException",
                        "detail": message,
                        "hint": (
                            "Model deployment may be missing or unavailable in the Foundry project. "
                            "Verify the deployment exists, uses a GlobalStandard/global deployment SKU, "
                            "and pass its exact deployment name."
                        ),
                    }

                return {
                    "status": "create_failed",
                    "agent_id": None,
                    "agent_name": resolved_agent_name or f"agent-{config.agent_id}",
                    "created": False,
                    "error_code": str(getattr(exc, "code", None) or "HttpResponseError"),
                    "detail": message,
                }
    finally:
        await _close_owned_credential(project_client)


def _normalize_messages(messages: Any) -> list[dict[str, str]]:
    """Normalize input into a list of role/content message dictionaries.

    This keeps the call surface flexible while ensuring the Agents SDK receives
    the ``role`` and ``content`` fields it expects.

    :param messages: A string, a single message dict, or an iterable of dicts.
    :returns: A list of message dictionaries.
    """
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    if isinstance(messages, dict):
        return [messages]
    return list(messages or [])


class FoundryInvoker:
    """Callable wrapper to invoke a Foundry Agent with telemetry."""

    def __init__(self, config: FoundryAgentConfig) -> None:
        """Create a new invoker.

        :param config: Foundry configuration describing the target agent.
        """
        self.config = config

    async def __call__(self, **kwargs: Any) -> dict[str, Any]:
        """Invoke a Foundry Agent through Azure AI Agents thread/run APIs.

        :param kwargs: Invocation options such as ``messages`` and ``thread_id``.
        :returns: A dictionary containing thread/run identifiers, responses, and telemetry.
        """

        runtime_client = kwargs.pop("client", None)
        owns_client = runtime_client is None or not _is_agents_runtime_client(runtime_client)
        if owns_client:
            runtime_client = _ensure_agents_client(self.config)

        if owns_client:
            try:
                async with runtime_client:
                    return await self._invoke(runtime_client, **kwargs)
            finally:
                await _close_owned_credential(runtime_client)
        return await self._invoke(runtime_client, **kwargs)

    async def _invoke(self, client: Any, **kwargs) -> dict[str, Any]:
        # No GoF pattern applies here; this is a thin data-oriented SDK adapter.
        messages = _normalize_messages(kwargs.pop("messages", []))
        started = perf_counter()
        runtime_agent_id = self.config.runtime_agent_id
        thread_id = kwargs.pop("thread_id", None) or kwargs.pop("conversation_id", None)
        requested_model = kwargs.pop("model", None)
        temperature = kwargs.pop("temperature", None)
        top_p = kwargs.pop("top_p", None)
        kwargs.pop("tools", None)
        kwargs.pop("stream", None)

        if runtime_agent_id is None:
            raise RuntimeError("Foundry runtime target requires a resolved agent id")

        if not _is_agents_runtime_client(client):
            raise TypeError(
                "Foundry runtime client must expose threads/messages/runs operations "
                "from azure-ai-agents"
            )

        if not thread_id:
            thread = await _maybe_await(client.threads.create())
            thread_dict = _to_dict(thread)
            thread_id = thread_dict.get("id") or getattr(thread, "id", None)

        if not thread_id:
            raise RuntimeError("Unable to resolve Foundry thread identifier")

        for message in messages:
            content = str(message.get("content", "")).strip()
            if not content:
                continue
            role = str(message.get("role", "user")).lower()
            if role not in {"user", "assistant"}:
                role = "user"

            await _maybe_await(
                client.messages.create(
                    thread_id=str(thread_id),
                    role=role,
                    content=content,
                )
            )

        run_kwargs: dict[str, Any] = {
            "thread_id": str(thread_id),
            "agent_id": runtime_agent_id,
        }
        if requested_model and requested_model != runtime_agent_id:
            run_kwargs["model"] = requested_model
        if temperature is not None:
            run_kwargs["temperature"] = temperature
        if top_p is not None:
            run_kwargs["top_p"] = top_p

        run = await _maybe_await(client.runs.create_and_process(**run_kwargs))
        run_dict = _to_dict(run)
        run_id = run_dict.get("id") or getattr(run, "id", None)
        run_status = _to_string_enum(run_dict.get("status") or getattr(run, "status", None)).lower()

        if run_status != "completed":
            error_payload = run_dict.get("last_error") or getattr(run, "last_error", None)
            raise RuntimeError(
                "Foundry run did not complete "
                f"(status={run_status or 'unknown'}): {_to_dict(error_payload) or error_payload}"
            )

        assistant_text = await _get_last_assistant_text(client.messages, str(thread_id))
        output_messages = (
            [
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": assistant_text}],
                }
            ]
            if assistant_text
            else []
        )

        usage_payload = run_dict.get("usage") or getattr(run, "usage", None)
        usage = usage_payload if isinstance(usage_payload, dict) else _to_dict(usage_payload)

        reference_name = self.config.agent_name or _agent_name_from_identifier(runtime_agent_id)
        telemetry = {
            "endpoint": self.config.endpoint,
            "agent_id": runtime_agent_id,
            "agent_name": reference_name,
            "deployment_name": self.config.deployment_name
            or (requested_model if isinstance(requested_model, str) else runtime_agent_id),
            "stream": False,
            "messages_sent": len(messages),
            "duration_ms": (perf_counter() - started) * 1000,
            "run_status": run_status,
            "api_version": "v2",
        }
        if usage:
            telemetry["usage"] = usage
        return {
            "thread_id": str(thread_id),
            "conversation_id": str(thread_id),
            "run_id": str(run_id) if run_id is not None else None,
            "response_id": str(run_id) if run_id is not None else None,
            "messages": output_messages,
            "stream": False,
            "telemetry": telemetry,
        }


def build_foundry_model_target(config: FoundryAgentConfig) -> ModelTarget:
    """Create a ``ModelTarget`` backed by Azure AI Foundry Agents.

    :param config: Foundry configuration describing the target agent.
    :returns: A :class:`ModelTarget` that delegates to :class:`FoundryInvoker`.
    """
    config.apply_project_contract()
    runtime_agent_id = config.runtime_agent_id
    if runtime_agent_id is None:
        raise ValueError("Foundry runtime target requires a resolved agent id")

    return ModelTarget(
        name=config.agent_name or runtime_agent_id,
        model=config.deployment_name or runtime_agent_id,
        invoker=FoundryInvoker(config),
        stream=config.stream,
        provider="foundry",
    )


__all__ = [
    "FoundryAgentConfig",
    "FoundryInvoker",
    "build_foundry_model_target",
    "ensure_foundry_agent",
]
