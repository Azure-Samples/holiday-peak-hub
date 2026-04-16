"""Helpers for Azure AI Foundry (Microsoft Agent Framework) integration."""

import asyncio
import inspect
import json
import os
from dataclasses import dataclass
from time import perf_counter
from typing import Any, AsyncGenerator, NamedTuple
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from agent_framework import AgentSession
from agent_framework import Message as MAFMessage
from agent_framework_foundry import FoundryAgent
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition
from azure.core.exceptions import HttpResponseError
from azure.identity.aio import DefaultAzureCredential
from opentelemetry.trace import NonRecordingSpan as _NRS

from .base_agent import ModelTarget

# Workaround: azure-ai-projects <=2.0.1 NonRecordingSpan bug.
# The SDK instrumentor reads span.span_instance.attributes, but the OTel
# no-op span lacks the property. Adding a falsy .attributes is safe.
if not hasattr(_NRS, "attributes"):
    _NRS.attributes = None  # type: ignore[attr-defined]

_FOUNDRY_PROJECT_HOST_SUFFIX = ".services.ai.azure.com"

_DEFAULT_FOUNDRY_INVOKE_TIMEOUT = float(os.getenv("AGENT_FOUNDRY_INVOKE_TIMEOUT_SECONDS", "55"))


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
    stream: bool = True
    credential: Any | None = None
    resolved_agent_id: str | None = None

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
        stream_raw = os.getenv("FOUNDRY_STREAM", "true").lower()
        stream = stream_raw not in {"0", "false", "no"}
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
            # resolved_agent_id is intentionally omitted — only set after
            # a successful ensure/lookup call confirms the ID is valid.
        )


def _ensure_client(config: FoundryAgentConfig) -> AIProjectClient:
    """Create an async :class:`AIProjectClient` with Entra ID credentials."""
    config.apply_project_contract()
    credential = config.credential or DefaultAzureCredential()
    client = AIProjectClient(endpoint=config.endpoint, credential=credential)
    if config.credential is None:
        setattr(client, "_holiday_peak_owned_credential", credential)
    return client


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


async def _lookup_existing_agent(
    agents_client: Any,
    *,
    configured_agent_id: str | None,
    resolved_agent_name: str | None,
    create_if_missing: bool,
) -> dict[str, Any] | None:
    """Search for an existing agent by ID or name. Return result dict or ``None``."""
    if not configured_agent_id and not resolved_agent_name:
        return None
    try:
        for candidate in await _list_agents(agents_client):
            if configured_agent_id and (_agent_id(candidate) or "") == configured_agent_id:
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
    return None


async def _create_agent_version(
    agents_client: Any,
    *,
    config: FoundryAgentConfig,
    resolved_agent_name: str | None,
    instructions: str | None,
    model: str | None,
) -> dict[str, Any]:
    """Create a new Foundry agent version and return a result dict."""
    resolved_model = model or config.deployment_name
    fallback_name = resolved_agent_name or f"agent-{config.agent_id}"

    if not resolved_model:
        return {
            "status": "missing_model",
            "agent_id": None,
            "agent_name": fallback_name,
            "created": False,
        }

    try:
        definition = PromptAgentDefinition(
            model=resolved_model,
            instructions=instructions or "You are a helpful retail assistant.",
        )
        created = await _call_first_available(
            agents_client,
            ("create_version",),
            agent_name=fallback_name,
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
                "agent_name": fallback_name,
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
            "agent_name": fallback_name,
            "created": False,
            "error_code": str(getattr(exc, "code", None) or "HttpResponseError"),
            "detail": message,
        }


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

            found = await _lookup_existing_agent(
                agents_client,
                configured_agent_id=configured_agent_id,
                resolved_agent_name=resolved_agent_name,
                create_if_missing=create_if_missing,
            )
            if found is not None:
                return found

            if not create_if_missing:
                return {
                    "status": "missing",
                    "agent_id": None,
                    "agent_name": resolved_agent_name,
                    "created": False,
                }

            return await _create_agent_version(
                agents_client,
                config=config,
                resolved_agent_name=resolved_agent_name,
                instructions=instructions,
                model=model,
            )
    finally:
        await _close_owned_credential(project_client)


# Re-export from canonical module — avoids duplicated logic.
from holiday_peak_lib.agents.provider_policy import (  # noqa: E402
    normalize_messages as _normalize_messages,
)


class _PreparedInvocation(NamedTuple):
    """Extracted payload shared by streaming and non-streaming paths."""

    maf_messages: list[Any]
    tool_callables: list[Any] | None
    normalized: list[dict[str, str]]
    session: AgentSession | None


class FoundryAgentInvoker:
    """Invoke a Foundry Agent through the MAF pipeline (Responses API).

    Implements the Strategy pattern for model invocation: ``__call__`` handles
    the non-streaming path, ``invoke_stream`` handles the streaming path.
    Both delegate message preparation to ``_prepare_invocation`` (Extract
    Method) to eliminate duplication.
    """

    def __init__(self, config: FoundryAgentConfig, *, timeout: float | None = None) -> None:
        self.config = config
        self._agent: Any = None
        self._credential: Any = None
        self._timeout = timeout if timeout is not None else _DEFAULT_FOUNDRY_INVOKE_TIMEOUT

    def _ensure_agent(self) -> FoundryAgent:
        """Create or return the cached FoundryAgent instance."""
        if self._agent is None:
            self._credential = self.config.credential or DefaultAzureCredential()
            self._agent = FoundryAgent(
                project_endpoint=self.config.endpoint,
                agent_name=self.config.agent_name,
                credential=self._credential,
            )
        return self._agent

    def _prepare_invocation(self, **kwargs: Any) -> _PreparedInvocation:
        """Extract and normalize messages/tools from kwargs.

        Shared by ``__call__`` and ``invoke_stream`` to avoid
        duplicating message serialization and tool extraction.
        """
        messages_raw = kwargs.pop("messages", [])
        kwargs.pop("stream", None)
        tools_raw = kwargs.pop("tools", None)
        # Extract session data before discarding transport-only kwargs
        session_id = kwargs.pop("session_id", None)
        session_state = kwargs.pop("_foundry_session_state", None)
        # Discard transport-only kwargs not consumed by MAF
        for _discard_key in (
            "model",
            "temperature",
            "top_p",
            "client",
            "thread_id",
            "conversation_id",
        ):
            kwargs.pop(_discard_key, None)

        # Restore AgentSession from prior state or create new one
        session: AgentSession | None = None
        if isinstance(session_state, dict):
            try:
                session = AgentSession.from_dict(session_state)
            except (KeyError, TypeError, ValueError):
                pass
        if session is None and session_id:
            session = AgentSession(session_id=str(session_id))

        # MAF Message expects string content; dict/list payloads from agent
        # handlers must be serialized to JSON first to avoid
        # ``ValueError: Content mapping requires 'type'``.
        normalized = _normalize_messages(messages_raw)
        maf_messages = []
        for msg in normalized:
            raw_content = msg.get("content", "")
            if isinstance(raw_content, (dict, list)):
                raw_content = json.dumps(raw_content, default=str)
            maf_messages.append(MAFMessage(role=msg.get("role", "user"), contents=[raw_content]))

        # Normalize tool callables from dict, list, or tuple
        tool_callables = None
        if isinstance(tools_raw, dict) and tools_raw:
            tool_callables = list(tools_raw.values())
        elif isinstance(tools_raw, (list, tuple)) and tools_raw:
            tool_callables = list(tools_raw)

        return _PreparedInvocation(
            maf_messages=maf_messages,
            tool_callables=tool_callables,
            normalized=normalized,
            session=session,
        )

    async def __call__(self, **kwargs: Any) -> dict[str, Any] | AsyncGenerator[str, None]:
        """Invoke the Foundry Agent.

        Strategy dispatch lives here:
        - ``stream=False`` (default) → awaits ``agent.run()`` and returns a dict.
        - ``stream=True`` → returns an ``AsyncGenerator[str, None]`` that
          yields text-token deltas.  Callers iterate with ``async for``.

        The dunder method remains the single public entry point so that
        ``invoker(**payload)`` always works regardless of streaming mode.
        """
        stream = kwargs.pop("stream", False)
        prep = self._prepare_invocation(**kwargs)

        if stream:
            return self._stream_impl(prep)

        return await self._request_response_impl(prep)

    async def _request_response_impl(
        self,
        prep: _PreparedInvocation,
    ) -> dict[str, Any]:
        """Non-streaming path: await a single AgentResponse."""
        started = perf_counter()
        agent = self._ensure_agent()

        run_kwargs: dict[str, Any] = {
            "stream": False,
            "tools": prep.tool_callables,
        }
        if prep.session is not None:
            run_kwargs["session"] = prep.session

        try:
            response = await asyncio.wait_for(
                agent.run(
                    prep.maf_messages,
                    **run_kwargs,
                ),
                timeout=self._timeout,
            )
        except asyncio.TimeoutError:
            return {
                "messages": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [
                            {
                                "type": "output_text",
                                "text": (
                                    "The request could not be completed within"
                                    " the allowed time. Please try a simpler"
                                    " query or retry shortly."
                                ),
                            }
                        ],
                    }
                ],
                "stream": False,
                "error": "timeout",
                "telemetry": self._build_telemetry(
                    started,
                    prep.normalized,
                    stream=False,
                    outcome="timeout",
                ),
            }

        # Extract updated session state from response for thread reuse.
        # AgentResponse.session carries the service_session_id assigned by
        # Foundry on the first call and must be returned to the caller so
        # subsequent requests in the same page-level thread can resume.
        updated_session_state: dict[str, Any] | None = None
        resp_session = getattr(response, "session", None)
        if resp_session is not None and hasattr(resp_session, "to_dict"):
            updated_session_state = resp_session.to_dict()
        elif prep.session is not None:
            updated_session_state = prep.session.to_dict()

        assistant_text = response.text if hasattr(response, "text") else str(response)
        output_messages = []
        if assistant_text:
            output_messages.append(
                {
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "output_text", "text": assistant_text}],
                }
            )

        result: dict[str, Any] = {
            "messages": output_messages,
            "stream": False,
            "telemetry": self._build_telemetry(started, prep.normalized, stream=False),
        }
        if updated_session_state is not None:
            result["_foundry_session_state"] = updated_session_state
        return result

    def _build_telemetry(
        self,
        started: float,
        normalized: list[dict[str, str]],
        *,
        stream: bool,
        outcome: str = "success",
    ) -> dict[str, Any]:
        """Build a standard telemetry dict (Extract Method)."""
        reference_name = self.config.agent_name or self.config.agent_id
        telemetry: dict[str, Any] = {
            "endpoint": self.config.endpoint,
            "agent_name": reference_name,
            "deployment_name": self.config.deployment_name or reference_name,
            "stream": stream,
            "messages_sent": len(normalized),
            "duration_ms": (perf_counter() - started) * 1000,
            "api_version": "responses",
            "runtime": "maf",
        }
        if outcome != "success":
            telemetry["timeout_seconds"] = self._timeout
            telemetry["outcome"] = outcome
        return telemetry

    async def _stream_impl(
        self,
        prep: _PreparedInvocation,
    ) -> AsyncGenerator[str, None]:
        """Streaming path: yield text-token deltas.

        ``agent.run(stream=True)`` returns a ``ResponseStream`` (AsyncIterable),
        NOT a coroutine, so we guard with ``asyncio.timeout`` instead of
        ``asyncio.wait_for``.

        MAF ``AgentResponseUpdate.text`` is *cumulative* — each update contains
        the full text assembled so far.  We track ``prev_len`` and yield only
        the new portion (the delta).
        """
        agent = self._ensure_agent()

        run_kwargs: dict[str, Any] = {
            "stream": True,
            "tools": prep.tool_callables,
        }
        if prep.session is not None:
            run_kwargs["session"] = prep.session

        stream_response = agent.run(
            prep.maf_messages,
            **run_kwargs,
        )

        prev_len = 0
        async with asyncio.timeout(self._timeout):
            async for update in stream_response:
                text = update.text if hasattr(update, "text") else str(update)
                if len(text) > prev_len:
                    yield text[prev_len:]
                    prev_len = len(text)

    async def close(self) -> None:
        """Clean up credential resources."""
        if self._credential is not None and self.config.credential is None:
            close_method = getattr(self._credential, "close", None)
            if callable(close_method):
                await _maybe_await(close_method())  # pylint: disable=not-callable
            self._credential = None
        self._agent = None


def build_foundry_model_target(config: FoundryAgentConfig) -> ModelTarget:
    """Create a ``ModelTarget`` backed by Azure AI Foundry Agents.

    :param config: Foundry configuration describing the target agent.
    :returns: A :class:`ModelTarget` that delegates to :class:`FoundryAgentInvoker`.
    """
    config.apply_project_contract()
    runtime_agent_id = config.runtime_agent_id
    if runtime_agent_id is None:
        raise ValueError("Foundry runtime target requires a resolved agent id")

    return ModelTarget(
        name=config.agent_name or runtime_agent_id,
        model=config.deployment_name or runtime_agent_id,
        invoker=FoundryAgentInvoker(config),
        stream=config.stream,
        provider="foundry",
    )


__all__ = [
    "FoundryAgentConfig",
    "FoundryAgentInvoker",
    "build_foundry_model_target",
    "ensure_foundry_agent",
]
