"""Evaluation helpers for enrichment and search workloads."""

from .dataset_loader import DatasetLoader
from .drift_detector import DriftDetector
from .enrichment_evaluator import (
    confidence_calibration_bins,
    enrichment_precision_recall_f1,
)
from .eval_runner import (
    BaseEvaluationRunner,
    ConfiguredEvaluationRunner,
    EvaluationRunResult,
    run_evaluation,
)
from .foundry_evaluators import (
    EvaluationBackendUnavailable,
    EvaluatorStrategy,
    FoundryEvaluatorStrategy,
    LocalEvaluatorStrategy,
    select_evaluator_strategy,
)
from .models import (
    CONTINUOUS_EVAL_BASELINE_SOURCE,
    DriftReport,
    EvalBaseline,
    EvalCase,
    EvalConfig,
    EvalModelTier,
    EvalSeverity,
    EvaluationDriftSignal,
    EvaluationResultEvent,
)
from .search_evaluator import intent_accuracy, mean_reciprocal_rank, ndcg_at_k, precision_at_k

__all__ = [
    "BaseEvaluationRunner",
    "ConfiguredEvaluationRunner",
    "CONTINUOUS_EVAL_BASELINE_SOURCE",
    "DatasetLoader",
    "DriftDetector",
    "DriftReport",
    "EvalBaseline",
    "EvalCase",
    "EvalConfig",
    "EvalModelTier",
    "EvalSeverity",
    "EvaluationBackendUnavailable",
    "EvaluationDriftSignal",
    "EvaluationRunResult",
    "EvaluationResultEvent",
    "EvaluatorStrategy",
    "FoundryEvaluatorStrategy",
    "LocalEvaluatorStrategy",
    "confidence_calibration_bins",
    "enrichment_precision_recall_f1",
    "run_evaluation",
    "select_evaluator_strategy",
    "ndcg_at_k",
    "mean_reciprocal_rank",
    "precision_at_k",
    "intent_accuracy",
]
