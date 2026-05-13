"""Unit tests for :func:`assess_complexity`.

Covers each sub-signal independently plus the long-text gate so regressions
to the routing heuristic are caught before they reach production traffic.
"""

from __future__ import annotations

import pytest
from holiday_peak_lib.agents.complexity import assess_complexity

# --------------------------------------------------------------------------- #
# Range invariants                                                             #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"query": ""},
        {"query": "short"},
        {"query": " ".join(["word"] * 1000)},
        {"requires_multi_tool": True},
        {"items": list(range(100))},
        {"filters": {f"k{i}": i for i in range(50)}},
    ],
)
def test_score_always_in_unit_interval(payload: dict) -> None:
    """The score contract is ``[0.0, 1.0]`` for every payload shape."""
    score = assess_complexity(payload)
    assert 0.0 <= score <= 1.0


# --------------------------------------------------------------------------- #
# Backward-compatibility contracts (existing test_agents_base.py assertions)   #
# --------------------------------------------------------------------------- #


def test_short_simple_query_below_threshold() -> None:
    """``{"query": "short"}`` must score below the default 0.5 threshold."""
    assert assess_complexity({"query": "short"}) < 0.5


def test_long_multi_tool_query_above_threshold() -> None:
    """A genuinely complex multi-tool query must clear 0.5.

    The query must have *varied* vocabulary — the previous heuristic
    treated 100 repetitions of ``"word"`` as complex; the new heuristic
    correctly does not. We use a realistic reasoning query instead.
    """
    payload = {
        "query": (
            "compare and analyze the differences between these products and "
            "recommend the best one based on reviews and pricing"
        ),
        "requires_multi_tool": True,
    }
    assert assess_complexity(payload) > 0.5


def test_long_repetitive_string_stays_low() -> None:
    """The bug the new design fixes: long-and-repetitive cannot route to LLM.

    A 1000-token string of one repeated word carries no
    routing-relevant information — no reasoning verbs, no clauses, no
    payload structure — and must score near zero. This is the exact
    scenario the previous (length-based) heuristic mishandled.
    """
    repetitive = {"query": " ".join(["word"] * 1000)}
    assert assess_complexity(repetitive) < 0.1


# --------------------------------------------------------------------------- #
# Reasoning-verb signal                                                        #
# --------------------------------------------------------------------------- #


def test_reasoning_verb_raises_score_over_neutral_query() -> None:
    """A short reasoning query scores strictly higher than a neutral one."""
    neutral = assess_complexity({"query": "show iphone 15 and 16"})
    reasoning = assess_complexity({"query": "compare iphone 15 and 16"})
    assert reasoning > neutral


def test_reasoning_verb_saturation_caps_at_two_verbs() -> None:
    """Beyond two verbs the contribution saturates — three is not 1.5× two.

    Other signals are explicitly disabled via kwargs so this test
    isolates the reasoning-verb signal.
    """
    isolate = {
        "clause_weight": 0.0,
        "payload_shape_weight": 0.0,
        "diversity_weight": 0.0,
        "entropy_weight": 0.0,
    }
    one = assess_complexity({"query": "compare items"}, **isolate)
    two = assess_complexity({"query": "compare recommend items"}, **isolate)
    three = assess_complexity({"query": "compare recommend analyze items"}, **isolate)
    assert two > one
    assert three == pytest.approx(two, abs=1e-9)


# --------------------------------------------------------------------------- #
# Clause-density signal                                                        #
# --------------------------------------------------------------------------- #


def test_clause_boundaries_increase_score() -> None:
    """Comma-separated multi-clause queries score higher than single clauses."""
    single = assess_complexity({"query": "find red shoes"})
    multi = assess_complexity({"query": "find red shoes, blue jeans, and a hat"})
    assert multi > single


# --------------------------------------------------------------------------- #
# Payload-shape signal                                                         #
# --------------------------------------------------------------------------- #


def test_bulk_item_list_raises_score() -> None:
    """A request with many items scores higher than a single-item request."""
    single = assess_complexity({"query": "checkout", "items": [{"sku": "A"}]})
    bulk = assess_complexity({"query": "checkout", "items": [{"sku": str(i)} for i in range(10)]})
    assert bulk > single


def test_heavily_filtered_query_raises_score() -> None:
    """A query carrying many filter keys scores higher than an unfiltered one."""
    plain = assess_complexity({"query": "search products"})
    filtered = assess_complexity(
        {
            "query": "search products",
            "filters": {"category": "x", "brand": "y", "price_min": 10, "price_max": 100},
        }
    )
    assert filtered > plain


# --------------------------------------------------------------------------- #
# Diversity + entropy (applied to all inputs)                                  #
# --------------------------------------------------------------------------- #


def test_varied_long_text_scores_above_repetitive_long_text() -> None:
    """Lexically varied long text scores strictly higher than repetitive.

    Diversity and entropy fire on every input, so this gap exists at
    any length — not just past a gate.
    """
    repetitive = " ".join(["word"] * 200)
    varied = " ".join(f"w{i}" for i in range(200))
    repetitive_score = assess_complexity({"query": repetitive})
    varied_score = assess_complexity({"query": varied})
    assert varied_score > repetitive_score


def test_short_varied_text_scores_above_short_repetitive_text() -> None:
    """Same contract as the long-text case, on short inputs.

    Encodes the user's design intent: diversity/entropy are cheap and
    well-defined for any token count, so they contribute uniformly.
    """
    repetitive = assess_complexity({"query": "word word word"})
    varied = assess_complexity({"query": "alpha beta gamma"})
    assert varied > repetitive
