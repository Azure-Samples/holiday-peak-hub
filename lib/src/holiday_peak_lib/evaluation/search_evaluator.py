"""Deterministic search evaluation metrics."""

from __future__ import annotations

import math
from typing import Iterable, Sequence


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def precision_at_k(results: Sequence[str], relevant_items: set[str], k: int) -> float:
    """Compute precision@k for a ranked result list."""

    if k <= 0:
        raise ValueError("k must be > 0")

    top_k = results[:k]
    if not top_k:
        return 0.0

    hits = sum(1 for item in top_k if item in relevant_items)
    return _safe_divide(float(hits), float(len(top_k)))


def mean_reciprocal_rank(result_lists: Iterable[Sequence[str]], relevant_items: set[str]) -> float:
    """Compute MRR over multiple ranked lists."""

    reciprocal_ranks: list[float] = []
    for results in result_lists:
        reciprocal = 0.0
        for index, item in enumerate(results, start=1):
            if item in relevant_items:
                reciprocal = 1.0 / index
                break
        reciprocal_ranks.append(reciprocal)

    if not reciprocal_ranks:
        return 0.0
    return sum(reciprocal_ranks) / len(reciprocal_ranks)


def ndcg_at_k(
    ranked_items: Sequence[str],
    relevance_by_item: dict[str, float],
    k: int,
) -> float:
    """Compute NDCG@k given explicit graded relevance labels."""

    if k <= 0:
        raise ValueError("k must be > 0")

    top_k = ranked_items[:k]
    dcg = 0.0
    for index, item in enumerate(top_k, start=1):
        relevance = relevance_by_item.get(item, 0.0)
        dcg += (2**relevance - 1) / math.log2(index + 1)

    ideal_relevances = sorted(relevance_by_item.values(), reverse=True)[:k]
    idcg = 0.0
    for index, relevance in enumerate(ideal_relevances, start=1):
        idcg += (2**relevance - 1) / math.log2(index + 1)

    return _safe_divide(dcg, idcg)


def intent_accuracy(predicted_intents: Sequence[str], expected_intents: Sequence[str]) -> float:
    """Compute exact-match intent classification accuracy."""

    if len(predicted_intents) != len(expected_intents):
        raise ValueError("predicted_intents and expected_intents must have equal length")

    if not predicted_intents:
        return 0.0

    matches = sum(
        1
        for predicted, expected in zip(predicted_intents, expected_intents)
        if predicted == expected
    )
    return _safe_divide(float(matches), float(len(predicted_intents)))
