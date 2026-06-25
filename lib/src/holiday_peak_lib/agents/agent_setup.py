"""App-side adapter for the asb-v1 *setup-as-code* contract.

This module is the holiday-peak-hub half of the agent-stress-benchmark (asb-v1)
contract declared by the companion optimizer (``setup-space.yaml`` in the
agent-stress-suite). It maps each asb-v1 search coordinate to a runtime knob and
normalizes emitted token usage to the shape the optimizer's cost axis reads.

Two directions:

* **setup-in** -- :func:`resolve_agent_setup` reads the six ``HPH_*`` environment
  variables (cluster-level defaults) and merges a per-request ``_setup_override``
  body value (single-call shadow, no redeploy). :func:`apply_invocation_overrides`
  injects the two coordinates that are honored at the model-call boundary today
  (``L`` -> ``max_output_tokens``, ``E`` -> ``reasoning_effort``) into the invoker
  kwargs consumed by :class:`holiday_peak_lib.agents.direct.DirectModelInvoker`.
* **usage-out** -- :func:`normalize_usage` converts a model usage mapping (Agent
  Framework ``UsageDetails`` *or* OpenAI-style) into the
  ``prompt_tokens`` / ``completion_tokens`` / ``total_tokens`` shape the
  optimizer's ``cost_basis='tokens'`` objective consumes from ``_telemetry.usage``.

asb-v1 coordinate map (mirror of ``setup-space.yaml`` ``agent_config_key``):

==========  =============================  =======================================
Coordinate  Env var                        Runtime honor-point
==========  =============================  =======================================
``D``       ``HPH_MAX_AGENT_STEPS``        agent control loop (degenerate: ``/invoke``
                                           is a single completion, no iterative loop)
``H``       ``HPH_MEMORY_WINDOW_TURNS``    history retrieval (memory/session layer)
``B``       ``HPH_TOOL_BREADTH_TIER``      tool assembly (agent build time)
``L``       ``HPH_MAX_OUTPUT_TOKENS``      direct.py ``_build_chat_options`` (live)
``topology````HPH_ORCHESTRATION_MODE``     router / graph (architectural)
``E``       ``HPH_REASONING_EFFORT``       direct.py ``_build_chat_options`` (live;
                                           inert on non-reasoning deployments)
==========  =============================  =======================================

``L`` and ``E`` are honored end-to-end here because their plumbing already exists
in :mod:`holiday_peak_lib.agents.direct`. The remaining coordinates are resolved
and observable (telemetry can record the setup a request ran under) but their
behavioral honor-points live in the orchestration / memory / tool-assembly layers
and are out of scope for the model-call seam.

Backward compatibility: with no ``HPH_*`` env vars and no ``_setup_override``,
:func:`resolve_agent_setup` returns an all-``None`` setup,
:func:`apply_invocation_overrides` is a no-op, and :func:`normalize_usage`
returns ``None`` for empty/absent usage -- the runtime behaves exactly as before
the seam was introduced.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

# asb-v1 coordinate -> HPH_* env var (mirror of setup-space.yaml agent_config_key).
ENV_MAX_AGENT_STEPS = "HPH_MAX_AGENT_STEPS"  # D
ENV_MEMORY_WINDOW_TURNS = "HPH_MEMORY_WINDOW_TURNS"  # H
ENV_TOOL_BREADTH_TIER = "HPH_TOOL_BREADTH_TIER"  # B
ENV_MAX_OUTPUT_TOKENS = "HPH_MAX_OUTPUT_TOKENS"  # L
ENV_ORCHESTRATION_MODE = "HPH_ORCHESTRATION_MODE"  # topology
ENV_REASONING_EFFORT = "HPH_REASONING_EFFORT"  # E

# Per-request override body key (mirror of setup-space.yaml injection.request_param.body_key).
SETUP_OVERRIDE_KEY = "_setup_override"

_VALID_TOOL_BREADTH = frozenset({"minimal", "standard", "full"})
_VALID_ORCHESTRATION = frozenset({"single_agent", "planner_executor", "router_specialists"})
_VALID_REASONING_EFFORT = frozenset({"minimal", "low", "medium", "high"})


@dataclass(frozen=True, slots=True)
class AgentSetup:
    """Resolved asb-v1 setup coordinates for a single agent invocation.

    Every field is ``None`` when neither an ``HPH_*`` env var nor a matching
    ``_setup_override`` value is present, which preserves pre-seam behavior.
    """

    max_agent_steps: int | None = None  # D
    memory_window_turns: int | None = None  # H
    tool_breadth_tier: str | None = None  # B
    max_output_tokens: int | None = None  # L
    orchestration_mode: str | None = None  # topology
    reasoning_effort: str | None = None  # E

    def to_metadata(self) -> dict[str, Any]:
        """Return the set coordinates only, for telemetry/observability."""
        items = {
            "max_agent_steps": self.max_agent_steps,
            "memory_window_turns": self.memory_window_turns,
            "tool_breadth_tier": self.tool_breadth_tier,
            "max_output_tokens": self.max_output_tokens,
            "orchestration_mode": self.orchestration_mode,
            "reasoning_effort": self.reasoning_effort,
        }
        return {key: value for key, value in items.items() if value is not None}


def _coerce_int(value: Any) -> int | None:
    """Parse a non-negative int from env/override text; return ``None`` if invalid."""
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _coerce_choice(value: Any, allowed: frozenset[str]) -> str | None:
    """Return a lower-cased value when it is in ``allowed``; else ``None``."""
    if value is None:
        return None
    candidate = str(value).strip().lower()
    return candidate if candidate in allowed else None


def resolve_agent_setup(overrides: dict[str, Any] | None = None) -> AgentSetup:
    """Resolve the active :class:`AgentSetup` from env vars and per-request overrides.

    Precedence: a per-request ``overrides`` value (from the ``_setup_override``
    request body key) shadows the matching ``HPH_*`` environment variable, which
    shadows the unset (``None``) default. Invalid values are dropped (treated as
    unset) rather than raising, so a malformed sweep cell degrades to baseline
    behavior instead of failing the request.
    """
    ov = overrides if isinstance(overrides, dict) else {}

    def pick(env_key: str, ov_key: str) -> Any:
        if ov_key in ov and ov[ov_key] is not None:
            return ov[ov_key]
        return os.getenv(env_key)

    return AgentSetup(
        max_agent_steps=_coerce_int(pick(ENV_MAX_AGENT_STEPS, "max_agent_steps")),
        memory_window_turns=_coerce_int(pick(ENV_MEMORY_WINDOW_TURNS, "memory_window_turns")),
        tool_breadth_tier=_coerce_choice(
            pick(ENV_TOOL_BREADTH_TIER, "tool_breadth_tier"), _VALID_TOOL_BREADTH
        ),
        max_output_tokens=_coerce_int(pick(ENV_MAX_OUTPUT_TOKENS, "max_output_tokens")),
        orchestration_mode=_coerce_choice(
            pick(ENV_ORCHESTRATION_MODE, "orchestration_mode"), _VALID_ORCHESTRATION
        ),
        reasoning_effort=_coerce_choice(
            pick(ENV_REASONING_EFFORT, "reasoning_effort"), _VALID_REASONING_EFFORT
        ),
    )


def apply_invocation_overrides(setup: AgentSetup, kwargs: dict[str, Any]) -> None:
    """Inject the model-call-honored coordinates (L, E) into invoker ``kwargs``.

    Mutates ``kwargs`` in place. A coordinate is applied only when it is set on
    ``setup`` *and* the caller has not already supplied that kwarg -- an explicit
    per-call value always wins over the swept default. ``max_output_tokens`` (L)
    and ``reasoning_effort`` (E) are consumed by
    :meth:`holiday_peak_lib.agents.direct.DirectModelInvoker._build_chat_options`.
    """
    if setup.max_output_tokens is not None and kwargs.get("max_output_tokens") is None:
        kwargs["max_output_tokens"] = setup.max_output_tokens
    if setup.reasoning_effort is not None and kwargs.get("reasoning_effort") is None:
        kwargs["reasoning_effort"] = setup.reasoning_effort


def _as_token_count(value: Any) -> int | None:
    """Coerce a token-count value to a non-negative int, or ``None`` if unusable."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    count = int(value)
    return count if count >= 0 else None


def normalize_usage(raw: Any) -> dict[str, int] | None:
    """Normalize a model usage mapping to the asb-v1 ``_telemetry.usage`` shape.

    The optimizer's ``cost_basis='tokens'`` objective reads ``prompt_tokens`` /
    ``completion_tokens`` / ``total_tokens``. Microsoft Agent Framework emits
    ``UsageDetails`` with ``input_token_count`` / ``output_token_count`` /
    ``total_token_count``; OpenAI-style backends already use the target keys. This
    adapter accepts either shape, derives ``total_tokens`` from prompt+completion
    when absent, drops non-int / ``None`` values, and returns ``None`` when nothing
    usable is present (so callers can skip emitting an empty ``usage`` block).
    """
    if not isinstance(raw, dict):
        return None

    prompt = _as_token_count(raw.get("prompt_tokens"))
    if prompt is None:
        prompt = _as_token_count(raw.get("input_token_count"))

    completion = _as_token_count(raw.get("completion_tokens"))
    if completion is None:
        completion = _as_token_count(raw.get("output_token_count"))

    total = _as_token_count(raw.get("total_tokens"))
    if total is None:
        total = _as_token_count(raw.get("total_token_count"))
    if total is None and (prompt is not None or completion is not None):
        total = (prompt or 0) + (completion or 0)

    normalized: dict[str, int] = {}
    if prompt is not None:
        normalized["prompt_tokens"] = prompt
    if completion is not None:
        normalized["completion_tokens"] = completion
    if total is not None:
        normalized["total_tokens"] = total
    return normalized or None


__all__ = [
    "AgentSetup",
    "ENV_MAX_AGENT_STEPS",
    "ENV_MEMORY_WINDOW_TURNS",
    "ENV_TOOL_BREADTH_TIER",
    "ENV_MAX_OUTPUT_TOKENS",
    "ENV_ORCHESTRATION_MODE",
    "ENV_REASONING_EFFORT",
    "SETUP_OVERRIDE_KEY",
    "apply_invocation_overrides",
    "normalize_usage",
    "resolve_agent_setup",
]
