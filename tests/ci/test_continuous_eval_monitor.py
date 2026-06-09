"""Tests for the continuous evaluation monitor helper."""

from __future__ import annotations

import json
from pathlib import Path

from holiday_peak_lib.evaluation import EvaluationRunResult
from holiday_peak_lib.evaluation.models import DriftReport, EvalSeverity

from scripts.ci.continuous_eval_monitor import (
    _build_event_payload,
    _float_metrics,
    _report_fingerprint,
    _write_state,
    create_deduped_issue,
)


class FakeGitHubIssueClient:
    def __init__(self, *, existing: bool = False) -> None:
        self.existing = existing
        self.created: list[dict[str, object]] = []

    def search_open_drift_issue(self, _fingerprint: str) -> bool:
        return self.existing

    def create_issue(self, *, title: str, body: str, labels: list[str]) -> str:
        self.created.append({"title": title, "body": body, "labels": labels})
        return "https://github.com/example/repo/issues/1"


def test_float_metrics_skips_non_finite_values() -> None:
    source = {"score": "1.0", "count": 3, "nan": "nan", "bad": None}

    assert _float_metrics(source) == {"score": 1.0, "count": 3.0}


def test_event_payload_marks_no_drift() -> None:
    result = EvaluationRunResult(
        status="ok",
        backend="local-fallback",
        metrics={"dataset_readiness": 1.0},
        details={"case_count": 2},
        score=1.0,
        baseline_id="catalog-search:baseline",
    )

    payload = _build_event_payload("catalog-search", "unit", result, None)

    assert payload["agent_name"] == "catalog-search"
    assert payload["drift_detected"] is False
    assert payload["eval.score"] == 1.0
    assert payload["metrics"] == {"dataset_readiness": 1.0}


def test_write_state_records_drift_signal(tmp_path: Path) -> None:
    report = _drift_report()
    state_path = tmp_path / ".drift_state.json"

    _write_state(state_path, "catalog-search", report)

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["catalog-search"]["consecutive_failures"] == 3
    assert state["catalog-search"]["last_signal_at"]


def test_create_deduped_issue_creates_when_fingerprint_is_new() -> None:
    report = _drift_report()
    client = FakeGitHubIssueClient(existing=False)

    issue_url = create_deduped_issue(
        repo="owner/repo",
        token="token",
        agent_name="catalog-search",
        report=report,
        result_path="apps/catalog/.foundry/results/run.json",
        client=client,  # type: ignore[arg-type]
    )

    assert issue_url == "https://github.com/example/repo/issues/1"
    assert client.created
    assert "[DRIFT:CRITICAL] catalog-search evaluation drift" == client.created[0]["title"]
    assert client.created[0]["labels"] == ["evaluation", "drift:critical"]
    assert "Fingerprint:" in str(client.created[0]["body"])


def test_create_deduped_issue_skips_existing_fingerprint() -> None:
    report = _drift_report()
    client = FakeGitHubIssueClient(existing=True)

    issue_url = create_deduped_issue(
        repo="owner/repo",
        token="token",
        agent_name="catalog-search",
        report=report,
        result_path=None,
        client=client,  # type: ignore[arg-type]
    )

    assert issue_url is None
    assert client.created == []


def test_report_fingerprint_is_stable() -> None:
    assert _report_fingerprint(_drift_report()) == "quality|quality:-0.25"


def _drift_report() -> DriftReport:
    return DriftReport(
        agent_name="catalog-search",
        run_name="unit",
        severity=EvalSeverity.CRITICAL,
        breached_thresholds=["quality"],
        drift_metrics={"quality": -0.25},
        current_metrics={"quality": 0.55},
        baseline_metrics={"quality": 0.8},
        baseline_id="catalog-search:baseline",
        consecutive_failures=3,
    )