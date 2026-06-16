"""Evaluation helpers for enrichment and search workloads."""

from .asb_models import (
    ASBCoordinate,
    ASBRunManifest,
    CoordinateBound,
    CostComponent,
    CostModelConfig,
    ScenarioRequest,
    SetupPoint,
)
from .catalog_topology import TopologyGraph, extract_topology, write_topology_artifacts
from .claim_map import export_claim_map, refresh_manifest_hashes, validate_bundle
from .cost_model import (
    SyntheticCostSource,
    TelemetryCostSource,
    build_cost_source,
    evaluate_cost,
    load_cost_model,
    validate_compact_bounds,
    write_cost_provenance,
)
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
from .quadratic_support import compute_quadratic_support, write_quadratic_support
from .search_evaluator import intent_accuracy, mean_reciprocal_rank, ndcg_at_k, precision_at_k
from .setup_surface import (
    SetupEvaluation,
    evaluate_setup_surface,
    load_requests,
    load_setup_grid,
    write_setup_artifacts,
)

__all__ = [
    "ASBCoordinate",
    "ASBRunManifest",
    "BaseEvaluationRunner",
    "CoordinateBound",
    "ConfiguredEvaluationRunner",
    "CONTINUOUS_EVAL_BASELINE_SOURCE",
    "CostComponent",
    "CostModelConfig",
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
    "ScenarioRequest",
    "SetupEvaluation",
    "SetupPoint",
    "SyntheticCostSource",
    "TelemetryCostSource",
    "TopologyGraph",
    "build_cost_source",
    "compute_quadratic_support",
    "confidence_calibration_bins",
    "evaluate_cost",
    "evaluate_setup_surface",
    "export_claim_map",
    "extract_topology",
    "enrichment_precision_recall_f1",
    "load_cost_model",
    "load_requests",
    "load_setup_grid",
    "refresh_manifest_hashes",
    "run_evaluation",
    "select_evaluator_strategy",
    "validate_bundle",
    "validate_compact_bounds",
    "write_cost_provenance",
    "write_quadratic_support",
    "write_setup_artifacts",
    "write_topology_artifacts",
    "ndcg_at_k",
    "mean_reciprocal_rank",
    "precision_at_k",
    "intent_accuracy",
]
