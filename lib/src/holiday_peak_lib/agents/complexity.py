"""Shared complexity assessment for SLM/LLM request routing.

The score is a number in ``[0.0, 1.0]`` that :class:`BaseRetailAgent` and
:class:`RoutingStrategy` compare against ``complexity_threshold`` (default
``0.5``) to decide whether to invoke the SLM or escalate to the LLM.

Design choices (why not classical lexical-complexity metrics):

* Most published lexical-complexity families — Type-Token Ratio (TTR),
  MTLD, Flesch-Kincaid, Coh-Metrix — were calibrated on paragraphs of
  natural-language prose. Retail traffic is dominated by short queries
  (1–30 tokens) where those metrics are noisy or undefined.
* The *real* question for routing is "does this request need an LLM to do
  well?", not "is this text lexically complex?" Those overlap but are not
  the same — a 4-token reasoning query (``"compare iPhone 15 and 16"``) is
  lexically trivial yet demands an LLM.

We therefore combine cheap **agent-routing signals** that target the actual
decision:

==========================  ==========  ============================================
Signal                      Max weight  What it captures
==========================  ==========  ============================================
``reasoning verbs``         0.30        Presence of ``compare``/``why``/``recommend``/...
``multi_tool``              0.20        Caller-supplied ``requires_multi_tool`` flag
``clause count``            0.15        Comma/conjunction/question density
``payload shape``           0.15        Large item lists or many filter keys
``diversity`` (Guiraud's R) 0.10        Vocabulary breadth, length-corrected
``entropy``  (Shannon, nat) 0.10        How evenly the vocabulary is used
==========================  ==========  ============================================

Note what is **not** in this list: raw length. A long prompt is not a
complex prompt — ``"aaaa…aaaa"`` repeated a thousand times needs no
reasoning. Diversity and entropy reward *information density* (not
bytes) and degrade gracefully on short inputs: a 1–token query simply
scores ~0 on both, a 2–word repeated query scores ~0 on entropy,
varied prose earns close to full weight. There is no length-based
gate — every signal is bounded, cheap, and applied uniformly.

Services that need domain-specific tuning (e.g. SKU short-circuit,
intent-aware weights) override :meth:`BaseRetailAgent._assess_complexity`
on their concrete agent class. See
``apps/ecommerce-catalog-search`` for an example.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

# Module-level constants — pre-computed once at import time so the hot
# path (called per agent request) does no allocation beyond the token
# scan itself.

_REASONING_VERBS: frozenset[str] = frozenset(
    {
        # synthesis
        "compare",
        "contrast",
        "differ",
        "difference",
        "vs",
        "versus",
        # justification
        "explain",
        "why",
        "reason",
        "justify",
        "rationale",
        # advice
        "recommend",
        "suggest",
        "advise",
        "propose",
        "best",
        # summarization
        "summarize",
        "summarise",
        "summary",
        "overview",
        "tldr",
        # analysis
        "analyze",
        "analyse",
        "evaluate",
        "assess",
        "review",
        # prediction
        "predict",
        "forecast",
        "estimate",
        "expect",
        # decision
        "decide",
        "choose",
        "select",
        "prefer",
    }
)

_CLAUSE_PUNCT: tuple[str, ...] = (",", ";", "?")
_CLAUSE_PHRASES: tuple[str, ...] = (
    " and ",
    " or ",
    " but ",
    " because ",
    " however ",
    " whereas ",
)

# Payload-shape thresholds — small values keep this signal as a *hint*,
# not a hard escalation. Services with truly bulk-shaped requests can
# override ``_assess_complexity`` on the concrete agent.
_BULK_LIST_THRESHOLD = 5
_FILTER_KEYS_THRESHOLD = 3


def _reasoning_verb_score(tokens: list[str], weight: float) -> float:
    """Score reasoning-verb presence in ``[0.0, weight]``.

    Saturates at two distinct verbs — beyond that we are no longer
    learning anything new about the request's intent.
    """
    hits = sum(1 for t in tokens if t in _REASONING_VERBS)
    if hits == 0:
        return 0.0
    return weight * min(hits / 2.0, 1.0)


def _clause_score(text_lower: str, weight: float) -> float:
    """Score clause density in ``[0.0, weight]``.

    A single clause contributes nothing; the signal grows with additional
    clauses and saturates after three boundaries.
    """
    boundaries = sum(text_lower.count(p) for p in _CLAUSE_PUNCT)
    boundaries += sum(text_lower.count(p) for p in _CLAUSE_PHRASES)
    if boundaries == 0:
        return 0.0
    return weight * min(boundaries / 3.0, 1.0)


def _payload_shape_score(payload: dict[str, Any], weight: float) -> float:
    """Score structural complexity of the request payload in ``[0.0, weight]``.

    Two cheap signals: long item lists (bulk operations) and many
    filter keys (richly-constrained queries). Each contributes half
    the available weight independently.
    """
    score = 0.0
    items = payload.get("items")
    if isinstance(items, list) and len(items) >= _BULK_LIST_THRESHOLD:
        score += 0.5
    for key in ("filters", "query_filters", "facets"):
        candidate = payload.get(key)
        if isinstance(candidate, dict) and len(candidate) >= _FILTER_KEYS_THRESHOLD:
            score += 0.5
            break
    return weight * min(score, 1.0)


def _diversity_score(tokens: list[str], weight: float) -> float:
    """Length-corrected lexical diversity in ``[0.0, weight]``.

    Uses Guiraud's R (``unique / sqrt(total)``), which is far less
    length-sensitive than raw TTR. Normalised by the empirical
    ``R == 15`` ceiling for English prose so the score caps at
    ``weight``.
    """
    n = len(tokens)
    if n == 0:
        return 0.0
    unique = len(set(tokens))
    guiraud = unique / math.sqrt(n)
    return weight * min(guiraud / 15.0, 1.0)


def _entropy_score(tokens: list[str], weight: float) -> float:
    """Normalised Shannon entropy in ``[0.0, weight]``.

    ``H / log(|vocab|)`` is in ``[0, 1]`` and measures how evenly the
    vocabulary is used. Highly repetitive boilerplate scores low;
    information-dense prose scores high.
    """
    n = len(tokens)
    if n < 2:
        return 0.0
    counts = Counter(tokens)
    if len(counts) < 2:
        return 0.0
    total = float(n)
    entropy = -sum((c / total) * math.log(c / total) for c in counts.values())
    return weight * (entropy / math.log(len(counts)))


def assess_complexity(
    payload: dict[str, Any],
    *,
    multi_tool_weight: float = 0.2,
    reasoning_verb_weight: float = 0.3,
    clause_weight: float = 0.15,
    payload_shape_weight: float = 0.15,
    diversity_weight: float = 0.1,
    entropy_weight: float = 0.1,
) -> float:
    """Return a complexity score in ``[0.0, 1.0]`` for routing decisions.

    Higher values indicate requests that should be served by the LLM
    rather than the SLM. The score combines six bounded signals —
    multi-tool hint, reasoning verbs, clause density, payload shape,
    lexical diversity, and Shannon entropy — each contributing at most
    its named weight.

    Raw length is intentionally **not** a signal: a prompt is not made
    complex by being long. ``"aaaa…aaaa"`` repeated a thousand times
    requires no reasoning. Diversity and entropy reward *information
    density*, not bytes, and degrade gracefully on short inputs (a
    1–token query simply scores ~0 on both).

    All weights are kwargs so individual services can recalibrate without
    forking the function — see :class:`AgentBuilder` for the threshold
    knob applied at construction time.

    Args:
        payload: Request dict; uses ``"query"`` key or falls back to the
            stringified payload. Recognised optional keys: ``items``
            (list), ``filters``/``query_filters``/``facets`` (dict),
            ``requires_multi_tool`` (truthy).
        multi_tool_weight: Contribution when ``requires_multi_tool`` is
            set in the payload.
        reasoning_verb_weight: Max contribution from
            reasoning/synthesis verbs (saturates at two verbs).
        clause_weight: Max contribution from clause boundary density
            (saturates after three boundaries).
        payload_shape_weight: Max contribution from bulk lists or
            heavily-filtered queries.
        diversity_weight: Max contribution from Guiraud's R lexical
            diversity. Bounded and well-defined for any token count.
        entropy_weight: Max contribution from normalised Shannon
            entropy. Returns 0 for inputs with fewer than two distinct
            tokens; bounded otherwise.
    """
    text = str(payload.get("query") or payload)
    tokens = text.lower().split()

    score = 0.0
    if payload.get("requires_multi_tool"):
        score += multi_tool_weight
    score += _reasoning_verb_score(tokens, reasoning_verb_weight)
    score += _clause_score(text.lower(), clause_weight)
    score += _payload_shape_score(payload, payload_shape_weight)
    score += _diversity_score(tokens, diversity_weight)
    score += _entropy_score(tokens, entropy_weight)

    return min(score, 1.0)


# --------------------------------------------------------------------------- #
# Routing-hint construction                                                    #
# --------------------------------------------------------------------------- #

#: Sentinel the SLM is asked to reply with when it wants the runtime to
#: escalate to the LLM. Exposed so callers (and detection logic) share a
#: single source of truth.
UPGRADE_SENTINEL = "UPGRADE"

_SLM_UPGRADE_HINT_TEMPLATE = (
    "[Routing] Complexity {complexity:.2f} / threshold {threshold:.2f}. "
    "You are the fast SLM target. Answer directly if you can. If the request "
    "truly needs deeper reasoning, reply with the single token "
    f"{UPGRADE_SENTINEL} on its own line so the runtime escalates to the LLM."
)

_SLM_DIRECT_HINT_TEMPLATE = (
    "[Routing] Complexity {complexity:.2f} / threshold {threshold:.2f}. "
    "You are the fast SLM target. Answer directly."
)

_LLM_ROUTING_HINT_TEMPLATE = (
    "[Routing] Complexity {complexity:.2f} / threshold {threshold:.2f}. "
    "You are the LLM target, selected because the request was judged complex. "
    "Reason step-by-step before answering."
)


def build_complexity_hint(
    *,
    complexity: float,
    threshold: float,
    target_kind: str,
    can_upgrade: bool = False,
) -> str:
    """Return a tier-framed routing note for the selected model.

    Models otherwise see only the messages and tools — they have no idea
    which tier was selected for them or why. This helper produces a
    short system-prompt sentence the framework can hand off through any
    surface (messages, kwargs, portal-bound metadata) so the model can
    behave accordingly: the SLM may decline and request escalation if
    the routing was wrong, and the LLM is reminded to reason carefully
    when it was picked specifically for complexity.

    Args:
        complexity: Score from :func:`assess_complexity`, in ``[0, 1]``.
        threshold: Routing cut-off configured on the agent.
        target_kind: ``"slm"`` or ``"llm"`` — which tier was selected.
        can_upgrade: Only meaningful for the SLM tier. When ``True``,
            instruct the model to reply with the
            :data:`UPGRADE_SENTINEL` token to trigger runtime
            escalation; when ``False``, omit that clause (used by the
            streaming path, which cannot honor a mid-stream upgrade,
            and by configurations with no LLM target).

    Returns:
        A single-paragraph system-prompt note describing the routing
        decision and the model's expected behaviour.

    Raises:
        ValueError: If ``target_kind`` is anything other than ``"slm"``
            or ``"llm"``.
    """
    if target_kind == "slm":
        template = _SLM_UPGRADE_HINT_TEMPLATE if can_upgrade else _SLM_DIRECT_HINT_TEMPLATE
        return template.format(complexity=complexity, threshold=threshold)
    if target_kind == "llm":
        return _LLM_ROUTING_HINT_TEMPLATE.format(complexity=complexity, threshold=threshold)
    raise ValueError(f"Unknown target_kind: {target_kind!r}")
