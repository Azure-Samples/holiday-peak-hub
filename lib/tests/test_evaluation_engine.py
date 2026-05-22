"""Tests for the shared continuous agent evaluation engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from holiday_peak_lib.app_factory import _build_evaluation_runner
from holiday_peak_lib.app_factory_components.endpoints import register_standard_endpoints
from holiday_peak_lib.evaluation import (
    ConfiguredEvaluationRunner,
    DatasetLoader,
    DriftDetector,
    DriftReport,
    EvalBaseline,
    EvalCase,
    EvalConfig,
    EvalSeverity,
    EvaluationDriftSignal,
)
from holiday_peak_lib.self_healing import (
    IncidentClass,
    IncidentState,
    SelfHealingKernel,
    SurfaceType,
    default_surface_manifest,
)
from pydantic import ValidationError


class _Registry:
    async def count(self) -> int:
        return 1

    async def list_domains(self) -> dict[str, list[str]]:
        return {"mock": ["default"]}

    async def health(self) -> dict[str, str]:
        return {"mock": "ok"}


class _Router:
    async def route(self, _intent: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"payload": payload}


class _Tracer:
    def __init__(self) -> None:
        self.latest: dict[str, Any] | None = None

    def get_traces(self, limit: int = 50) -> list[dict[str, int]]:
        return [{"limit": limit}]

    def get_metrics(self) -> dict[str, int]:
        return {"count": 1}

    def get_latest_evaluation(self) -> dict[str, Any] | None:
        return self.latest

    def record_evaluation(self, payload: dict[str, Any]) -> None:
        self.latest = payload


class _Logger:
    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def warning(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def test_eval_case_validation_requires_query_and_expected_behavior() -> None:
    with pytest.raises(ValidationError):
        EvalCase(query=" ", expected_behavior="answer clearly")


def test_evaluation_drift_signal_from_report_is_self_healing_compatible() -> None:
    report = DriftReport(
        agent_name="catalog-search",
        run_name="nightly",
        severity=EvalSeverity.CRITICAL,
        breached_thresholds=["relevance"],
        drift_metrics={"relevance": -0.3},
        current_metrics={"relevance": 0.4},
        baseline_metrics={"relevance": 0.7},
        baseline_id="catalog-search:baseline",
    )

    signal = EvaluationDriftSignal.from_report(report)

    assert signal.surface == SurfaceType.EVALUATION
    assert signal.service_name == "catalog-search"
    assert signal.metadata["incident_class"] == "quality_drift"
    assert signal.metadata["baselineSource"] == "continuous-eval"


def test_dataset_loader_loads_yaml_config_and_jsonl_cases(tmp_path: Path) -> None:
    foundry_root = _write_foundry_fixture(tmp_path)
    loader = DatasetLoader(foundry_root)

    config = loader.load_config()
    cases = loader.load_cases(config)

    assert config.agent_name == "catalog-search"
    assert config.thresholds["dataset_readiness"] == 1.0
    assert len(cases) == 2
    assert cases[0].query == "find waterproof hiking boots"


@pytest.mark.asyncio
async def test_configured_runner_uses_local_strategy_when_requested(tmp_path: Path) -> None:
    foundry_root = _write_foundry_fixture(tmp_path)
    runner = ConfiguredEvaluationRunner.from_foundry_root(
        str(foundry_root),
        prefer_foundry=False,
    )

    result = await runner.run(run_name="unit")

    assert result.status == "ok"
    assert result.backend == "local-fallback"
    assert result.metrics["case_count"] == 2.0
    assert result.details["agent_name"] == "catalog-search"
    assert result.model_dump()["eval.score"] == 1.0
    assert result.model_dump()["eval.baseline_id"] == "catalog-search:baseline"
    assert result.model_dump()["baselineSource"] == "continuous-eval"


def test_drift_detector_emits_report_after_configured_failure_window() -> None:
    config = EvalConfig(
        agent_name="catalog-search",
        thresholds={"relevance": 0.8},
        consecutive_failure_window=2,
        rate_limit_hours=0,
    )
    baseline = EvalBaseline(
        agent_name="catalog-search",
        baseline_id="baseline-2026-05-22",
        metrics={"relevance": 0.9},
    )
    detector = DriftDetector(config)
    result = _result({"relevance": 0.5})

    assert detector.detect(result, baseline=baseline, run_name="first") is None
    report = detector.detect(result, baseline=baseline, run_name="second")

    assert report is not None
    assert report.severity == EvalSeverity.CRITICAL
    assert report.baseline_id == "baseline-2026-05-22"
    assert "relevance" in report.breached_thresholds


@pytest.mark.asyncio
async def test_quality_drift_signal_escalates_without_remediation() -> None:
    kernel = SelfHealingKernel(
        service_name="catalog-search",
        manifest=default_surface_manifest("catalog-search"),
        enabled=True,
    )
    report = DriftReport(
        agent_name="catalog-search",
        run_name="nightly",
        severity=EvalSeverity.WARNING,
        breached_thresholds=["relevance"],
        drift_metrics={"relevance": -0.1},
        current_metrics={"relevance": 0.7},
    )

    incident = await kernel.handle_failure_signal(EvaluationDriftSignal.from_report(report))

    assert incident is not None
    assert incident.incident_class == IncidentClass.QUALITY_DRIFT
    assert incident.state == IncidentState.ESCALATED
    assert incident.actions == []


def test_standard_app_evaluation_runner_discovers_repo_root_agent_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent_root = tmp_path / "apps" / "catalog-search"
    _write_foundry_fixture(agent_root)
    monkeypatch.chdir(tmp_path)

    runner = _build_evaluation_runner("catalog-search", _Logger())

    assert runner is not None
    assert runner.config.agent_name == "catalog-search"


def test_evaluation_run_and_history_endpoints(tmp_path: Path) -> None:
    foundry_root = _write_foundry_fixture(tmp_path)
    runner = ConfiguredEvaluationRunner.from_foundry_root(
        str(foundry_root),
        prefer_foundry=False,
    )
    tracer = _Tracer()
    app = FastAPI()

    register_standard_endpoints(
        app,
        service_name="catalog-search",
        registry=_Registry(),
        router=_Router(),
        tracer=tracer,
        logger=_Logger(),
        strict_foundry_mode=False,
        require_foundry_readiness=False,
        is_foundry_ready=lambda: True,
        requires_foundry_runtime_resolution=lambda: False,
        foundry_capabilities=lambda: {"ready": True},
        evaluation_runner_provider=lambda: runner,
    )

    client = TestClient(app)
    run_response = client.post("/agent/evaluation/run", json={"run_name": "unit"})
    history_response = client.get("/agent/evaluation/history")
    latest_response = client.get("/agent/evaluation/latest")

    assert run_response.status_code == 200
    run_payload = run_response.json()["result"]
    assert run_payload["backend"] == "local-fallback"
    assert run_payload["eval.score"] == 1.0
    assert run_payload["eval.baseline_id"] == "catalog-search:baseline"
    assert run_payload["baselineSource"] == "continuous-eval"
    assert history_response.json()["total"] == 1
    assert latest_response.json()["latest"]["backend"] == "local-fallback"


def test_evaluation_endpoints_return_useful_error_without_config() -> None:
    app = FastAPI()
    register_standard_endpoints(
        app,
        service_name="catalog-search",
        registry=_Registry(),
        router=_Router(),
        tracer=_Tracer(),
        logger=_Logger(),
        strict_foundry_mode=False,
        require_foundry_readiness=False,
        is_foundry_ready=lambda: True,
        requires_foundry_runtime_resolution=lambda: False,
        foundry_capabilities=lambda: {"ready": True},
    )

    response = TestClient(app).post("/agent/evaluation/run", json={})

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "evaluation_config_not_available"


def _result(metrics: dict[str, float]):
    from holiday_peak_lib.evaluation import EvaluationRunResult

    return EvaluationRunResult(
        status="ok",
        backend="local-fallback",
        metrics=metrics,
        details={"run_name": "unit"},
        score=metrics.get("relevance"),
        baseline_id="catalog-search:baseline",
    )


def _write_foundry_fixture(tmp_path: Path) -> Path:
    foundry_root = tmp_path / ".foundry"
    dataset_dir = foundry_root / "datasets"
    dataset_dir.mkdir(parents=True)
    (foundry_root / "eval-config.yaml").write_text(
        "\n".join(
            [
                "schema_version: '1'",
                "agent_name: catalog-search",
                "evaluators:",
                "  - relevance",
                "dataset_path: datasets/seed.jsonl",
                "baseline_id: catalog-search:baseline",
                "thresholds:",
                "  dataset_readiness: 1.0",
                "  response_coverage: 0.0",
                "model_targets:",
                "  - slm",
                "  - llm",
            ]
        ),
        encoding="utf-8",
    )
    cases = [
        {
            "query": "find waterproof hiking boots",
            "expected_behavior": "return relevant waterproof hiking boot products",
            "expected_model_tier": "slm",
        },
        {
            "query": "compare premium trail shoes",
            "expected_behavior": "compare products with concise tradeoffs",
            "expected_model_tier": "llm",
        },
    ]
    (dataset_dir / "seed.jsonl").write_text(
        "\n".join(json.dumps(case) for case in cases),
        encoding="utf-8",
    )
    return foundry_root
