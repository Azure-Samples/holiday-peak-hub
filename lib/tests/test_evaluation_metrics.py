"""Tests for evaluation metric helpers and eval runner fallback."""

from __future__ import annotations

from holiday_peak_lib.evaluation.enrichment_evaluator import (
    confidence_calibration_bins,
    enrichment_precision_recall_f1,
)
from holiday_peak_lib.evaluation.eval_runner import run_evaluation
from holiday_peak_lib.evaluation.search_evaluator import (
    intent_accuracy,
    mean_reciprocal_rank,
    ndcg_at_k,
    precision_at_k,
)


def test_enrichment_precision_recall_f1() -> None:
    result = enrichment_precision_recall_f1(
        predicted_items=["color", "material", "size"],
        expected_items=["color", "size", "brand"],
    )
    assert result["precision"] == 2 / 3
    assert result["recall"] == 2 / 3
    assert result["f1"] == 2 / 3


def test_confidence_calibration_bins() -> None:
    bins = confidence_calibration_bins(
        [(0.1, False), (0.2, True), (0.9, True)],
        bins=5,
    )
    assert len(bins) == 5
    assert bins[0]["count"] == 1.0
    assert bins[1]["count"] == 1.0
    assert bins[4]["count"] == 1.0


def test_precision_at_k() -> None:
    score = precision_at_k(["a", "b", "c"], {"a", "x"}, 2)
    assert score == 0.5


def test_mean_reciprocal_rank() -> None:
    score = mean_reciprocal_rank([["x", "a"], ["a", "x"]], {"a"})
    assert score == (0.5 + 1.0) / 2


def test_ndcg_at_k() -> None:
    score = ndcg_at_k(["a", "b", "c"], {"a": 3.0, "b": 2.0, "c": 1.0}, 3)
    assert score == 1.0


def test_intent_accuracy() -> None:
    score = intent_accuracy(["browse", "buy", "support"], ["browse", "return", "support"])
    assert score == 2 / 3


def test_eval_runner_fallback_without_sdk() -> None:
    def evaluator(dataset):
        return {"items": len(dataset), "quality": 0.8}

    result = run_evaluation(dataset=[{"id": 1}, {"id": 2}], evaluator=evaluator, run_name="test-run")
    assert result.status in {"ok", "degraded"}
    assert result.metrics["items"] == 2
    assert result.backend in {"local-fallback", "azure-ai-evaluation"}
