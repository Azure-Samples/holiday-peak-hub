"""Model abstractions used by :class:`~.base_agent.BaseRetailAgent`.

This module defines what a *model* is from the agent's point of view:

* :data:`ModelInvoker` — the async-callable contract every model adapter
  satisfies (Azure AI Agents, Chat Completions, Foundry hosted, …).
* :class:`StreamingModelInvoker` — Strategy-pattern marker for invokers
  that additionally support token streaming via ``stream=True``.
* :class:`ModelTarget` — a deployable model bound to a concrete invoker
  plus its sampling defaults.
* :func:`supports_streaming` / :func:`extract_text_from_response` — small
  helpers for working with invoker results.
* :func:`extract_logprobs` / :func:`summarize_logprobs` — shape-agnostic
  capture of per-token logprobs and their aggregate statistics.

Keeping these in a dedicated module separates "what a model is" from
"what an agent is" (:mod:`.base_agent`).
"""

import math
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Awaitable, Callable

ModelInvoker = Callable[..., Awaitable[dict[str, Any]]]


class StreamingModelInvoker:
    """Protocol-style interface for invokers that support streaming.

    Pattern: Strategy — invokers implement ``__call__`` as the single entry
    point. When ``stream=True`` is passed, ``__call__`` dispatches to the
    private ``_stream_impl`` method and returns an ``AsyncGenerator``.
    :func:`supports_streaming` checks for this method's presence.
    """

    def _stream_impl(  # noqa: ARG002
        self,
        prep: Any,
    ) -> AsyncGenerator[str, None]:
        """Yield text token deltas from a streaming model call."""
        raise NotImplementedError  # pragma: no cover


def supports_streaming(invoker: Any) -> bool:
    """Check whether an invoker's ``__call__`` supports ``stream=True``.

    Convention: invokers that support streaming implement a ``_stream_impl``
    method. ``__call__`` dispatches to it when ``stream=True``.
    """
    return callable(getattr(invoker, "_stream_impl", None))


def extract_text_from_response(result: dict[str, Any]) -> str:
    """Extract concatenated assistant text from a model response dict."""
    parts: list[str] = []
    for msg in result.get("messages", []):
        for content in msg.get("content", []):
            if isinstance(content, dict):
                text = content.get("text", "")
                if text:
                    parts.append(text)
    return "".join(parts)


def extract_logprobs(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Return per-token logprob entries from a model response.

    Different providers shape logprobs differently — OpenAI Chat
    Completions nests them under ``choices[0].logprobs.content``, the
    OpenAI Responses API hangs them off each ``output[].content[]``
    entry, and simpler adapters (and test mocks) put a flat list at
    ``result["logprobs"]``. This helper probes all three shapes and
    returns whatever it finds, so callers can capture logprobs without
    knowing which transport produced them.

    Each returned entry is left untouched (typically
    ``{"token": str, "logprob": float, "top_logprobs": [...]}``) so
    downstream code keeps access to the per-token detail.
    """
    if not isinstance(result, dict):
        return []

    # OpenAI Chat Completions: ``choices[0].logprobs.content``.
    choices = result.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, dict):
            lp = first.get("logprobs")
            if isinstance(lp, dict):
                content = lp.get("content")
                if isinstance(content, list):
                    collected = [item for item in content if isinstance(item, dict)]
                    if collected:
                        return collected

    # OpenAI Responses API: each output item carries its own logprobs.
    output = result.get("output")
    if isinstance(output, list):
        collected_resp: list[dict[str, Any]] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []) or []:
                if not isinstance(content, dict):
                    continue
                lp = content.get("logprobs")
                if isinstance(lp, list):
                    collected_resp.extend(c for c in lp if isinstance(c, dict))
        if collected_resp:
            return collected_resp

    # Flat shape used by simpler adapters and test mocks.
    flat = result.get("logprobs")
    if isinstance(flat, list):
        return [item for item in flat if isinstance(item, dict)]

    return []


def summarize_logprobs(logprobs: list[dict[str, Any]]) -> dict[str, Any]:
    """Reduce per-token logprobs to a compact aggregate.

    Returns ``count`` always; when at least one numeric ``logprob`` is
    present also returns ``mean`` / ``min`` / ``max`` plus
    ``perplexity`` (``exp(-mean_logprob)``). Perplexity is the headline
    confidence number: lower is more confident, ``1.0`` means the model
    placed full probability on every chosen token.
    """
    if not logprobs:
        return {"count": 0}
    values = [item["logprob"] for item in logprobs if isinstance(item.get("logprob"), (int, float))]
    if not values:
        return {"count": len(logprobs)}
    mean = sum(values) / len(values)
    return {
        "count": len(values),
        "mean": mean,
        "min": min(values),
        "max": max(values),
        "perplexity": math.exp(-mean),
    }


# Responses API ``include`` token that toggles per-token logprobs on
# assistant messages. Exposed as a module constant so adapters and
# tests can refer to the same string without hard-coding it.
RESPONSES_LOGPROBS_INCLUDE = "message.output_text.logprobs"


def build_logprobs_payload(target: "ModelTarget") -> dict[str, Any]:
    """Provider-aware request keys for per-token logprobs.

    Different OpenAI surfaces toggle logprobs differently:

    * **Chat Completions** (and Azure OpenAI / generic adapters):
      ``{"logprobs": True, "top_logprobs": <int>?}``.
    * **Responses API** (Foundry hosted agents, OpenAI Responses):
      ``{"include": ["message.output_text.logprobs"], "top_logprobs": <int>?}`` —
      Responses API does not accept a boolean ``logprobs`` field;
      presence of the token in the ``include`` array is the toggle.

    Both shapes accept ``top_logprobs`` in the range ``0..20`` for the
    per-token alternative distribution. When ``target.logprobs`` is
    ``False`` this returns an empty dict so callers can ``.update()``
    unconditionally without leaking enabled state.

    Provider routing rule: ``"foundry"`` selects the Responses API
    shape; everything else (including ``None``) falls back to Chat
    Completions. The ``include`` array returned here is owned by the
    framework — callers that pre-populate ``include`` should *extend*
    the result rather than overwrite, to avoid dropping unrelated
    include tokens such as ``web_search_call.results``.
    """
    if not target.logprobs:
        return {}
    provider = (target.provider or "").lower()
    if provider == "foundry":
        payload: dict[str, Any] = {"include": [RESPONSES_LOGPROBS_INCLUDE]}
        if target.top_logprobs is not None:
            payload["top_logprobs"] = target.top_logprobs
        return payload
    payload = {"logprobs": True}
    if target.top_logprobs is not None:
        payload["top_logprobs"] = target.top_logprobs
    return payload


@dataclass
class ModelTarget:
    """Represents a specific model deployment plus its invoker.

    The ``invoker`` is an async callable that receives ``messages`` (list or
    str), optional ``tools``, and any extra kwargs. This keeps the agent
    base class agnostic of the concrete SDK (Azure AI Agents, Chat
    Completions, Foundry hosted, …).

    ``logprobs`` defaults to ``True`` so every new configuration emits
    per-token confidence into the telemetry channel out-of-the-box.
    Services can disable it per tier when bandwidth or provider limits
    require, and ``top_logprobs`` (when set) requests the per-token
    alternative-token distribution — useful for routing-quality audits
    and as a cheap proxy for model self-uncertainty.
    """

    name: str
    model: str
    invoker: ModelInvoker
    temperature: float = 0.2
    top_p: float = 0.9
    provider: str | None = None
    logprobs: bool = True
    top_logprobs: int | None = None
