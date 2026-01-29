"""Helpers for Azure AI Foundry (Microsoft Agent Framework) integration.

This module keeps Azure AI Projects imports lazy to avoid hard failures
when the SDK is not installed. It provides a small adapter that turns a Foundry
Agent into a ``ModelTarget`` invoker for ``BaseRetailAgent``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any
from time import perf_counter

from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient

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
        deployment = os.getenv("MODEL_DEPLOYMENT_NAME")
        stream = (os.getenv("FOUNDRY_STREAM") or "").lower() in {"1", "true", "yes"}
        if not endpoint or not agent_id:
            raise ValueError("PROJECT_ENDPOINT/FOUNDRY_ENDPOINT and FOUNDRY_AGENT_ID are required")
        return cls(
            endpoint=endpoint,
            agent_id=agent_id,
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
        return AIProjectClient(endpoint=config.endpoint, credential=credential)    
    except ImportError as exc:  # pragma: no cover - guard for missing SDK
        raise ImportError(
            "azure-ai-projects and azure-identity are required for Foundry integration"
        ) from exc


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
            async with project_client:
                return await self._invoke(project_client)
        return await self._invoke(project_client)

    async def _invoke(self, client: AIProjectClient, **kwargs) -> dict[str, Any]:
        agents_client = client.agents
        messages = _normalize_messages(kwargs.pop("messages", []))
        stream_requested = kwargs.pop("stream", self.config.stream)
        started = perf_counter()

        thread = kwargs.pop("thread", None) or await agents_client.threads.create()
        for msg in messages:
            await agents_client.messages.create(
                thread_id=thread.id,
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
            )

        if stream_requested:
            text_chunks: list[str] = []
            stream = await agents_client.runs.stream(thread_id=thread.id, agent_id=self.config.agent_id)
            async for event_type, event_data, _ in stream:
                if getattr(event_data, "text", None):
                    text_chunks.append(event_data.text)
                if getattr(event_type, "name", None) == "DONE":
                    break
            telemetry = {
                "endpoint": self.config.endpoint,
                "agent_id": self.config.agent_id,
                "deployment_name": self.config.deployment_name or self.config.agent_id,
                "stream": True,
                "messages_sent": len(messages),
                "duration_ms": (perf_counter() - started) * 1000,
            }
            return {"thread_id": thread.id, "text": "".join(text_chunks), "stream": True, "telemetry": telemetry}

        run = await agents_client.runs.create_and_process(thread_id=thread.id, agent_id=self.config.agent_id)
        history = await agents_client.messages.list(thread_id=thread.id)
        try:
            history = sorted(
                history,
                key=lambda message: getattr(message, "created_at", None)
                or (message.get("created_at") if isinstance(message, dict) else None)
                or 0,
            )
        except TypeError:
            # Some history entries may not be comparable / lack a usable created_at;
            # if sorting fails, fall back to the original order.
            pass
        telemetry = {
            "endpoint": self.config.endpoint,
            "agent_id": self.config.agent_id,
            "deployment_name": self.config.deployment_name or self.config.agent_id,
            "stream": False,
            "messages_sent": len(messages),
            "duration_ms": (perf_counter() - started) * 1000,
        }
        usage = getattr(run, "usage", None)
        if usage:
            to_dict = getattr(usage, "to_dict", None)
            telemetry["usage"] = to_dict() if callable(to_dict) else dict(getattr(usage, "__dict__", {}))
        return {
            "thread_id": thread.id,
            "run_id": run.id,
            "messages": [m.to_dict() if hasattr(m, "to_dict") else m for m in history],
            "stream": False,
            "telemetry": telemetry,
        }


def build_foundry_model_target(config: FoundryAgentConfig) -> ModelTarget:
    """Create a ``ModelTarget`` backed by Azure AI Foundry Agents.

    :param config: Foundry configuration describing the target agent.
    :returns: A :class:`ModelTarget` that delegates to :class:`FoundryInvoker`.
    """

    return ModelTarget(
        name=config.agent_id,
        model=config.deployment_name or config.agent_id,
        invoker=FoundryInvoker(config),
        stream=config.stream,
    )


__all__ = ["FoundryAgentConfig", "FoundryInvoker", "build_foundry_model_target"]
