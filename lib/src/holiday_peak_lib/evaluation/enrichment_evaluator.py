"""Deterministic enrichment evaluation metrics."""

from __future__ import annotations

from typing import Iterable


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def enrichment_precision_recall_f1(
    predicted_items: Iterable[str],
    expected_items: Iterable[str],
) -> dict[str, float]:
    """Compute precision/recall/F1 for enrichment outputs.

    Args:
        predicted_items: IDs/labels predicted by the enrichment flow.
        expected_items: Ground-truth IDs/labels.

    Returns:
        Dictionary with precision, recall, f1, tp, fp, and fn values.
    """

    predicted_set = {item for item in predicted_items if item is not None}
    expected_set = {item for item in expected_items if item is not None}

    true_positive = len(predicted_set & expected_set)
    false_positive = len(predicted_set - expected_set)
    false_negative = len(expected_set - predicted_set)

    precision = _safe_divide(true_positive, true_positive + false_positive)
    recall = _safe_divide(true_positive, true_positive + false_negative)
    f1 = _safe_divide(2 * precision * recall, precision + recall)

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": float(true_positive),
        "fp": float(false_positive),
        "fn": float(false_negative),
    }


def confidence_calibration_bins(
    predictions: Iterable[tuple[float, bool]],
    *,
    bins: int = 10,
) -> list[dict[str, float]]:
    """Return confidence calibration aggregates by probability bins.

    Args:
        predictions: Iterable of `(confidence, is_correct)` tuples.
        bins: Number of equal-width bins in [0, 1].

    Returns:
        List of per-bin aggregates with count, avg_confidence, and accuracy.
    """

    if bins <= 0:
        raise ValueError("bins must be > 0")

    aggregates: list[dict[str, float]] = [
        {
            "bin_start": index / bins,
            "bin_end": (index + 1) / bins,
            "count": 0.0,
            "avg_confidence": 0.0,
            "accuracy": 0.0,
        }
        for index in range(bins)
    ]

    confidence_sums = [0.0] * bins
    correct_sums = [0.0] * bins

    for confidence, is_correct in predictions:
        bounded_confidence = max(0.0, min(1.0, confidence))
        bin_index = min(int(bounded_confidence * bins), bins - 1)
        aggregates[bin_index]["count"] += 1.0
        confidence_sums[bin_index] += bounded_confidence
        correct_sums[bin_index] += 1.0 if is_correct else 0.0

    for bin_index, aggregate in enumerate(aggregates):
        count = aggregate["count"]
        aggregate["avg_confidence"] = _safe_divide(confidence_sums[bin_index], count)
        aggregate["accuracy"] = _safe_divide(correct_sums[bin_index], count)

    return aggregates
