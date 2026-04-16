"""Shared complexity assessment for request routing.

Extracts the duplicated heuristic from ``BaseRetailAgent._assess_complexity``
and ``RoutingStrategy._assess_complexity`` into a single, reusable function.

# No GoF pattern applies — pure stateless scoring utility.
"""

from typing import Any


def assess_complexity(
    payload: dict[str, Any],
    *,
    word_divisor: float = 50.0,
    multi_tool_weight: float = 0.2,
) -> float:
    """Return a lightweight complexity score in ``[0.0, 1.0]``.

    Higher values indicate more complex requests that should route to an LLM.

    Args:
        payload: Request dict; uses ``"query"`` key or falls back to str.
        word_divisor: Number of words that maps to a score of 1.0.
        multi_tool_weight: Bonus added when ``requires_multi_tool`` is set.
    """
    text = str(payload.get("query") or payload)
    word_score = min(len(text.split()) / word_divisor, 1.0)
    tool_score = multi_tool_weight if payload.get("requires_multi_tool") else 0.0
    return min(word_score + tool_score, 1.0)
