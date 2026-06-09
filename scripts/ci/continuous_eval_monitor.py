"""CI helper: run configured evaluation, detect drift, persist result, open issues (optional).

This script is an orchestration wrapper around the evaluation helpers in
`holiday_peak_lib.evaluation`. It is intentionally thin: it runs a configured
evaluation, emits a normalized `EvaluationResultEvent` payload, and (optionally)
persists the run artifact and files a GitHub issue when drift is detected.
It avoids mutating private members of `DriftDetector`; consecutive failure
windows across runs are not seeded by this helper (callers may choose to
provide an explicit state path and a separate orchestrator to manage
cross-run windows).
"""
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB_SRC = REPO_ROOT / "lib" / "src"
import sys
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
    parser.add_argument("--write-log", help="path to write run log")
    parser.add_argument("--state-path", help="path to persist monitoring state (optional)")
    parser.add_argument("--repo", help="owner/repo for issue creation")
    parser.add_argument("--github-token", help="github token for issue creation")
    parser.add_argument("--create-issue", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--update-baseline", action="store_true")
    return parser.parse_args()


async def run_monitor(args: argparse.Namespace) -> int:
    agent_root = Path(args.agent_root).resolve()
    loader = DatasetLoader(agent_root / ".foundry")
    runner = ConfiguredEvaluationRunner(loader=loader, prefer_foundry=False)

    result = await runner.run(run_name=str(args.run_name))

    baseline = loader.load_baseline(runner.config)

    detector = DriftDetector(runner.config)
    # Do not mutate private Detector internals. We run detection for this run
    # and emit the report. Cross-run consecutive windows are out-of-band for
    # this helper unless a caller provides an external orchestrator.
    drift_report = detector.detect(result, baseline=baseline, run_name=str(args.run_name))

    # Build event payload
    event = EvaluationResultEvent(
        agent_name=runner.config.agent_name,
        run_name=str(args.run_name),
        backend=getattr(result, 'backend', None),
        status=getattr(result, 'status', None),
        metrics=_float_metrics(getattr(result, 'metrics', {})),
        eval_score=getattr(result, 'score', None),
        eval_baseline_id=getattr(result, 'baseline_id', None),
        baselineSource=getattr(result, 'baseline_source', None),
        drift_detected=drift_report is not None,
        drift_report=drift_report,
        details=getattr(result, 'details', None),
    )

    # Serialize payload
    try:
        payload = event.model_dump(mode="json", by_alias=True) if hasattr(event, "model_dump") else event.model_dump()
    except Exception:
        try:
            payload = event.model_dump()
        except Exception:
            payload = dict(event.__dict__)

    # Write result if requested
    if args.write_result:
        result_path = Path(args.write_result)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    # Persist a small state file if a state path is provided by the caller.
    if args.state_path:
        try:
            state_p = Path(args.state_path)
            state = {}
            if state_p.exists():
                state = json.loads(state_p.read_text(encoding="utf-8"))
            state[runner.config.agent_name] = {
                "consecutive_failures": getattr(drift_report, 'consecutive_failures', 0) if drift_report else 0,
                "last_signal_at": datetime.now(timezone.utc).isoformat() if drift_report else None,
            }
            state_p.parent.mkdir(parents=True, exist_ok=True)
            state_p.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")
        except Exception:
            # non-fatal; do not fail the run if state persistence fails
            pass

    # Issue creation (guarded by dry-run and presence of repo/token)
    if drift_report is not None and args.create_issue and args.repo and args.github_token and not args.dry_run:
        create_deduped_issue(
            repo=args.repo,
            token=args.github_token,
            agent=runner.config.agent_name,
            report=drift_report,
            result_path=str(args.write_result) if args.write_result else None,
        )

    # Optionally update baseline when requested and no drift
    if drift_report is None and args.update_baseline and runner.config.baseline_path:
        try:
            baseline_path = loader.resolve_path(runner.config.baseline_path)
            new_baseline = {
                "agent_name": runner.config.agent_name,
                "metrics": _float_metrics(getattr(result, 'metrics', {})),
                "baseline_id": runner.config.resolved_baseline_id,
                "dataset_version": getattr(result, 'details', {}).get('dataset_version', 'seed'),
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            tmp = baseline_path.with_suffix('.tmp')
            tmp.write_text(json.dumps(new_baseline, indent=2, sort_keys=True), encoding='utf-8')
            tmp.replace(baseline_path)
        except Exception:
            pass

    return 0


def _float_metrics(metrics: Dict[str, Any]) -> Dict[str, float]:
    normalized: Dict[str, float] = {}
    for key, value in metrics.items():
        try:
            v = float(value)
            # filter NaN / Inf values which are not JSON-friendly for our metrics
            import math

            if not math.isfinite(v):
                continue
            normalized[key] = v
        except (TypeError, ValueError):
            continue
    return normalized


def create_deduped_issue(*, repo: str, token: str, agent: str, report, result_path: Optional[str] = None) -> None:
    """Create a GitHub issue for a drift report if none exists for the same agent/severity/fingerprint.

    This function is a small wrapper over the GitHub REST API. It performs a
    search for existing open issues matching a fingerprint and avoids creating
    duplicates.
    """
    owner, name = repo.split("/")
    session = requests.Session()
    session.headers.update({"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"})

    severity = getattr(report.severity, 'value', str(getattr(report.severity, 'name', report.severity)))
    fingerprint = _report_fingerprint(report)
    title = f"[DRIFT:{severity.upper()}] {agent} evaluation drift"
    body_lines = [
        f"Agent: {agent}",
        f"Severity: {severity}",
        f"Breached: {', '.join(getattr(report, 'breached_thresholds', []))}",
        f"Consecutive failures: {getattr(report, 'consecutive_failures', 0)}",
        f"Fingerprint: {fingerprint}",
    ]
    if result_path:
        body_lines.append(f"Result artifact: {result_path}")
    body = "\n\n".join(body_lines)

    # Search for existing open issue by fingerprint
    search_q = f'repo:{repo} state:open in:title "DRIFT" "Fingerprint: {fingerprint}"'
    search_url = f'https://api.github.com/search/issues?q={requests.utils.quote(search_q)}'
    try:
        r = session.get(search_url)
        if r.ok:
            data = r.json()
            if data.get('total_count', 0) > 0:
                print(f"Found existing issue for fingerprint {fingerprint}; skipping creation")
                return
    except Exception:
        # network/search failures should not raise
        pass

    create_url = f'https://api.github.com/repos/{repo}/issues'
    payload = {"title": title, "body": body, "labels": [f"drift:{severity}"]}
    try:
        r = session.post(create_url, json=payload)
        if not r.ok:
            print(f"Failed to create issue: {r.status_code} {r.text}")
        else:
            print(f"Created issue: {r.json().get('html_url')}")
    except Exception:
        print("Failed to create issue due to network error")


def _report_fingerprint(report) -> str:
    items = sorted(getattr(report, 'drift_metrics', {}).items())
    return "|".join(f"{k}:{round(v,4)}" for k, v in items)


def main() -> int:
    return asyncio.run(run_monitor(parse_args()))


if __name__ == '__main__':
    raise SystemExit(main())
