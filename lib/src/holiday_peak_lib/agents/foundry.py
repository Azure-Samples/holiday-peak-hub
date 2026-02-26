"""Helpers for Azure AI Foundry (Microsoft Agent Framework) integration.

This module keeps Azure AI Projects imports lazy to avoid hard failures
when the SDK is not installed. It provides a small adapter that turns a Foundry
Agent into a ``ModelTarget`` invoker for ``BaseRetailAgent``.
"""
from __future__ import annotations

import os
import inspect
from dataclasses import dataclass
from typing import Any
from time import perf_counter

from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.core.exceptions import HttpResponseError

from .base_agent import ModelTarget


@dataclass
class FoundryAgentConfig:
    """Configuration required to call a Foundry Agent.

    This is designed for the Azure AI Foundry Agents v2 surface via
    :class:`azure.ai.projects.aio.AIProjectClient` and its ``agents`` subclient.

    Env vars (defaults):
    - PROJECT_ENDPOINT or FOUNDRY_ENDPOINT: Azure AI Foundry project endpoint.
    - PROJECT_NAME or FOUNDRY_PROJECT_NAME: Azure AI Foundry project name (optional).
    - FOUNDRY_AGENT_ID: Agent ID created in the project.
    - MODEL_DEPLOYMENT_NAME: Optional model deployment associated with the agent.
    - FOUNDRY_STREAM: ``true`` to enable streaming aggregation by default.
    """

    endpoint: str
    agent_id: str
    agent_name: str | None = None
    deployment_name: str | None = None
    project_name: str | None = None
    stream: bool = False
    credential: Any | None = None

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
            agent_id=agent_id or agent_name,
            agent_name=agent_name,
            deployment_name=deployment,
            project_name=project_name,
            stream=stream,
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
        credential = config.credential or DefaultAzureCredential()
        client = AIProjectClient(endpoint=config.endpoint, credential=credential)
        if config.credential is None:
            setattr(client, "_holiday_peak_owned_credential", credential)
        return client
    except ImportError as exc:  # pragma: no cover - guard for missing SDK
        raise ImportError(
            "azure-ai-projects and azure-identity are required for Foundry integration"
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


async def _call_first_available(target: Any, method_names: tuple[str, ...], *args: Any, **kwargs: Any) -> Any:
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
    resolved_agent_name = (
        agent_name
        or config.agent_name
        or _agent_name_from_identifier(config.agent_id)
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

            if resolved_agent_name:
                try:
                    for candidate in await _list_agents(agents_client):
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
                except Exception:
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
                except Exception:
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
        """Invoke a Foundry Agent, optionally streaming tokens.

        This method:
        - Ensures an async Project client is available and uses its ``agents`` subclient.
        - Creates a thread if one is not supplied.
        - Sends user messages to the thread.
        - Executes the run either as a stream or as a blocking create-and-process.
        - Returns telemetry with timing and basic usage metadata.

        We return messages in ascending order when possible to preserve
        conversational flow.

        :param kwargs: Invocation options such as ``messages``, ``stream`` or ``thread``.
        :returns: A dictionary containing thread/run identifiers, responses, and telemetry.
        """

        project_client: AIProjectClient | None = kwargs.pop("client", None)
        owns_client = project_client is None
        if project_client is None:
            project_client = _ensure_client(self.config)

        if owns_client:
            try:
                async with project_client:
                    return await self._invoke(project_client, **kwargs)
            finally:
                await _close_owned_credential(project_client)
        return await self._invoke(project_client, **kwargs)

    async def _invoke(self, client: AIProjectClient, **kwargs) -> dict[str, Any]:
        messages = _normalize_messages(kwargs.pop("messages", []))
        started = perf_counter()
        openai_client = client.get_openai_client()
        conversation_id = kwargs.pop("conversation_id", None)
        input_text = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "user")
        if not input_text:
            input_text = "\n".join(str(m.get("content", "")) for m in messages)

        reference_name = self.config.agent_name or _agent_name_from_identifier(self.config.agent_id)
        if not reference_name:
            raise ValueError("Foundry agent reference name is required for Agents V2 responses API")

        try:
            if conversation_id:
                response = await _maybe_await(
                    openai_client.responses.create(
                        input=input_text,
                        conversation=conversation_id,
                        extra_body={"agent_reference": {"name": reference_name, "type": "agent_reference"}},
                    )
                )
            else:
                conversation = await _maybe_await(
                    openai_client.conversations.create(
                        items=[
                            {
                                "type": "message",
                                "role": "user",
                                "content": input_text,
                            }
                        ]
                    )
                )
                conversation_id = getattr(conversation, "id", None) or conversation.get("id")
                response = await _maybe_await(
                    openai_client.responses.create(
                        conversation=conversation_id,
                        input=input_text,
                        extra_body={"agent_reference": {"name": reference_name, "type": "agent_reference"}},
                    )
                )
        finally:
            close_method = getattr(openai_client, "close", None)
            if callable(close_method):
                await _maybe_await(close_method())

        response_dict = response.model_dump() if hasattr(response, "model_dump") else (
            response.to_dict() if hasattr(response, "to_dict") else dict(getattr(response, "__dict__", {}))
        )

        output = response_dict.get("output") or []
        output_messages = [
            item for item in output
            if isinstance(item, dict) and item.get("type") == "message"
        ]

        telemetry = {
            "endpoint": self.config.endpoint,
            "agent_id": self.config.agent_id,
            "agent_name": reference_name,
            "deployment_name": self.config.deployment_name or self.config.agent_id,
            "stream": False,
            "messages_sent": len(messages),
            "duration_ms": (perf_counter() - started) * 1000,
            "api_version": "v2",
        }
        usage = response_dict.get("usage")
        if usage:
            telemetry["usage"] = usage
        return {
            "conversation_id": conversation_id,
            "response_id": response_dict.get("id"),
            "messages": output_messages,
            "stream": False,
            "telemetry": telemetry,
        }


def build_foundry_model_target(config: FoundryAgentConfig) -> ModelTarget:
    """Create a ``ModelTarget`` backed by Azure AI Foundry Agents.

    :param config: Foundry configuration describing the target agent.
    :returns: A :class:`ModelTarget` that delegates to :class:`FoundryInvoker`.
    """

    return ModelTarget(
        name=config.agent_name or config.agent_id,
        model=config.deployment_name or config.agent_id,
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
