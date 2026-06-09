"""Continuous evaluation monitor: runs configured evaluation, detects drift, persists results, and files issues.

This is a lightweight orchestration wrapper around `ConfiguredEvaluationRunner` and
`DriftDetector`. It is intended for GitHub Actions and local dry-runs.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB_SRC = REPO_ROOT / "lib" / "src"
if str(LIB_SRC) not in sys.path:
    sys.path.insert(0, str(LIB_SRC))

from holiday_peak_lib.evaluation import (
    ConfiguredEvaluationRunner,
    DatasetLoader,
    DriftDetector,
    EvaluationResultEvent,
)

import requests


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-root", required=True)
    parser.add_argument("--run-name", default="continuous")
    parser.add_argument("--write-result", help="path to write result json")
    parser.add_argument("--repo", help="owner/repo for issue creation")
    parser.add_argument("--github-token", help="github token for issue creation")
    parser.add_argument("--create-issue", action="store_true")
    return parser.parse_args()


async def run_monitor(args: argparse.Namespace) -> int:
    agent_root = Path(args.agent_root).resolve()
    loader = DatasetLoader(agent_root / ".foundry")
    runner = ConfiguredEvaluationRunner(loader=loader, prefer_foundry=False)

    result = await runner.run(run_name=str(args.run_name))

    baseline = loader.load_baseline(runner.config)
    # Load persisted drift state so consecutive failure windows span runs
    state_path = (agent_root / ".foundry" / "results" / ".drift_state.json")
    persisted: dict[str, Any] = {}
    if state_path.exists():
        try:
            persisted = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            persisted = {}

    detector = DriftDetector(runner.config)
    # Seed detector internal counters from persisted state if present
    try:
        prior = persisted.get(runner.config.agent_name, {})
        if prior:
            detector._failure_counts[runner.config.agent_name] = int(prior.get("failure_count", 0))
            last = prior.get("last_signal_at")
            if last:
                from datetime import datetime

                detector._last_signal_at[runner.config.agent_name] = datetime.fromisoformat(last)
    except Exception:
        # Best-effort only; do not fail evaluation on persistence errors
        pass

    drift_report = detector.detect(result, baseline=baseline, run_name=str(args.run_name))

    event = EvaluationResultEvent(
        agent_name=runner.config.agent_name,
        run_name=str(args.run_name),
        backend=result.backend,
        status=result.status,
        metrics=_float_metrics(result.metrics),
        eval_score=result.score,
        eval_baseline_id=result.baseline_id,
        baselineSource=result.baseline_source,
        drift_detected=drift_report is not None,
        drift_report=drift_report,
        details=result.details,
    )

    # pydantic BaseModel.model_dump returns a dict; normalize to JSON-serializable dict
    try:
        payload = event.model_dump(mode="json", by_alias=True) if hasattr(event, "model_dump") else event.model_dump()
    except Exception:
        # fallback: use .model_dump() or dict(access)
        try:
            payload = event.model_dump()
        except Exception:
            payload = dict(event.__dict__)
    # Ensure write path
    if args.write_result:
        result_path = Path(args.write_result)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    # If drift detected, attempt to create a GitHub issue with dedupe guard
    if drift_report is not None and args.create_issue and args.repo and args.github_token:
        create_deduped_issue(
            repo=args.repo,
            token=args.github_token,
            agent=runner.config.agent_name,
            report=drift_report,
            result_path=str(args.write_result) if args.write_result else None,
        )

    # Only update baseline when no breach and no baseline path mutation risk
    if drift_report is None and runner.config.baseline_path:
        baseline_path = loader.resolve_path(runner.config.baseline_path)
        # write baseline atomically
        new_baseline = {
            "agent_name": runner.config.agent_name,
            "metrics": _float_metrics(result.metrics),
            "baseline_id": runner.config.resolved_baseline_id,
            "dataset_version": getattr(result, 'details', {}).get('dataset_version','seed'),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        tmp = baseline_path.with_suffix('.tmp')
        tmp.write_text(json.dumps(new_baseline, indent=2, sort_keys=True), encoding='utf-8')
        tmp.replace(baseline_path)

    return 0

    # Persist updated detector state so next run can continue the consecutive window
    try:
        stored = persisted
        stored[runner.config.agent_name] = {
            "failure_count": int(detector._failure_counts.get(runner.config.agent_name, 0)),
            "last_signal_at": (
                detector._last_signal_at.get(runner.config.agent_name).isoformat()
                if detector._last_signal_at.get(runner.config.agent_name)
                else None
            ),
        }
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(stored, indent=2, sort_keys=True), encoding="utf-8")
    except Exception:
        # non-fatal
        pass


def _float_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in metrics.items():
        try:
            normalized[key] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized


def create_deduped_issue(*, repo: str, token: str, agent: str, report, result_path: str | None) -> None:
    """Create a GitHub issue for a drift report if none exists for the same agent/severity/fingerprint."""
    owner, name = repo.split("/")
    session = requests.Session()
    session.headers.update({"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"})

    severity = report.severity.value
    fingerprint = _report_fingerprint(report)
    title = f"[DRIFT:{severity.upper()}] {agent} evaluation drift"
    body_lines = [
        f"Agent: {agent}",
        f"Severity: {severity}",
        f"Breached: {', '.join(report.breached_thresholds)}",
        f"Consecutive failures: {report.consecutive_failures}",
        f"Fingerprint: {fingerprint}",
    ]
    if result_path:
        body_lines.append(f"Result artifact: {result_path}")
    body = "\n\n".join(body_lines)

    # Search for existing open issue with same fingerprint label in body
    search_q = f'repo:{repo} state:open in:title "DRIFT" "Fingerprint: {fingerprint}"'
    search_url = f'https://api.github.com/search/issues?q={requests.utils.quote(search_q)}'
    r = session.get(search_url)
    if r.ok:
        data = r.json()
        if data.get('total_count', 0) > 0:
            print(f"Found existing issue for fingerprint {fingerprint}; skipping creation")
            return
    # Create issue
    create_url = f'https://api.github.com/repos/{repo}/issues'
    payload = {"title": title, "body": body, "labels": [f"drift:{severity}"]}
    r = session.post(create_url, json=payload)
    if not r.ok:
        print(f"Failed to create issue: {r.status_code} {r.text}")
    else:
        print(f"Created issue: {r.json().get('html_url')}")


def _report_fingerprint(report) -> str:
    # Simple fingerprint over breached keys and magnitude
    items = sorted(report.drift_metrics.items())
    return "|".join(f"{k}:{round(v,4)}" for k, v in items)


def main() -> int:
    return asyncio.run(run_monitor(parse_args()))


if __name__ == '__main__':
    raise SystemExit(main())
