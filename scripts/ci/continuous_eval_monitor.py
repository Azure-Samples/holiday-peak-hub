"""Run continuous agent evaluation and file drift issues when needed."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB_SRC = REPO_ROOT / "lib" / "src"
if str(LIB_SRC) not in sys.path:
    sys.path.insert(0, str(LIB_SRC))

from holiday_peak_lib.evaluation import (  # noqa: E402
    ConfiguredEvaluationRunner,
    DatasetLoader,
    DriftDetector,
    EvaluationResultEvent,
)
from holiday_peak_lib.evaluation.models import DriftReport  # noqa: E402


@dataclass(frozen=True)
class GitHubIssueClient:
    """Small GitHub Issues REST client used by the CI monitor."""

    repo: str
    token: str

    def search_open_drift_issue(self, fingerprint: str) -> bool:
        query = f'repo:{self.repo} state:open "Fingerprint: {fingerprint}"'
        encoded_query = urllib.parse.quote(query)
        payload = self._request_json("GET", f"/search/issues?q={encoded_query}")
        return int(payload.get("total_count", 0)) > 0

    def create_issue(self, *, title: str, body: str, labels: list[str]) -> str | None:
        payload = self._request_json(
            "POST",
            f"/repos/{self.repo}/issues",
            body={"title": title, "body": body, "labels": labels},
        )
        html_url = payload.get("html_url")
        return str(html_url) if html_url else None

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None
        if body is not None:
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"https://api.github.com{path}",
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            return json.loads(response.read().decode("utf-8"))


def parse_args() -> argparse.Namespace:
    """Parse monitor command-line arguments."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-root", required=True, help="Path to the agent app root")
    parser.add_argument("--run-name", default="continuous", help="Evaluation run name")
    parser.add_argument("--write-result", help="Path to write normalized result JSON")
    parser.add_argument("--write-log", help="Path to write monitor summary log")
    parser.add_argument("--state-path", help="Optional drift-state JSON path")
    parser.add_argument("--repo", help="GitHub owner/repo for issue creation")
    parser.add_argument("--github-token", help="GitHub token for issue creation")
    parser.add_argument("--create-issue", action="store_true", help="Create drift issues")
    parser.add_argument("--dry-run", action="store_true", help="Suppress issue creation")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update configured baseline.json when no drift is detected",
    )
    return parser.parse_args()


async def run_monitor(args: argparse.Namespace) -> int:
    """Run one continuous evaluation monitor cycle."""

    agent_root = Path(args.agent_root).resolve()
    loader = DatasetLoader(agent_root / ".foundry")
    runner = ConfiguredEvaluationRunner(loader=loader, prefer_foundry=True)
    result = await runner.run(run_name=str(args.run_name))
    baseline = loader.load_baseline(runner.config)
    drift_report = DriftDetector(runner.config).detect(
        result,
        baseline=baseline,
        run_name=str(args.run_name),
    )
    payload = _build_event_payload(runner.config.agent_name, args.run_name, result, drift_report)

    if args.write_result:
        _write_json(Path(args.write_result), payload)
    if args.state_path:
        _write_state(Path(args.state_path), runner.config.agent_name, drift_report)
    if args.update_baseline and drift_report is None and runner.config.baseline_path:
        _update_baseline(loader, runner.config, result)

    issue_url = None
    if drift_report is not None and args.create_issue and not args.dry_run:
        if not args.repo or not args.github_token:
            print("Skipping drift issue creation: repo or GitHub token not provided")
        else:
            issue_url = create_deduped_issue(
                repo=args.repo,
                token=args.github_token,
                agent_name=runner.config.agent_name,
                report=drift_report,
                result_path=args.write_result,
            )

    if args.write_log:
        _write_log(Path(args.write_log), runner.config.agent_name, payload, issue_url)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def _build_event_payload(
    agent_name: str,
    run_name: str,
    result: Any,
    drift_report: DriftReport | None,
) -> dict[str, Any]:
    event = EvaluationResultEvent(
        agent_name=agent_name,
        run_name=run_name,
        backend=result.backend,
        status=result.status,
        metrics=_float_metrics(result.metrics),
        eval_score=result.score,
        eval_baseline_id=result.baseline_id,
        baseline_source=result.baseline_source,
        drift_detected=drift_report is not None,
        drift_report=drift_report,
        details=result.details,
    )
    return event.model_dump(mode="json", by_alias=True)


def _float_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in metrics.items():
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(numeric_value):
            normalized[key] = numeric_value
    return normalized


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_state(path: Path, agent_name: str, report: DriftReport | None) -> None:
    state: dict[str, Any] = {}
    if path.exists():
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            state = {}
    state[agent_name] = {
        "consecutive_failures": report.consecutive_failures if report else 0,
        "last_signal_at": datetime.now(timezone.utc).isoformat() if report else None,
    }
    _write_json(path, state)


def _update_baseline(loader: DatasetLoader, config: Any, result: Any) -> None:
    baseline_path = loader.resolve_path(config.baseline_path)
    existing_payload: dict[str, Any] = {}
    if baseline_path.exists():
        try:
            existing_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            existing_payload = {}
    now = datetime.now(timezone.utc).isoformat()
    baseline_payload = {
        "agent_name": config.agent_name,
        "metrics": _float_metrics(result.metrics),
        "baseline_id": config.resolved_baseline_id,
        "dataset_version": result.details.get("dataset_version", "seed"),
        "created_at": existing_payload.get("created_at", now),
        "updated_at": now,
    }
    temporary_path = baseline_path.with_suffix(".tmp")
    _write_json(temporary_path, baseline_payload)
    temporary_path.replace(baseline_path)


def create_deduped_issue(
    *,
    repo: str,
    token: str,
    agent_name: str,
    report: DriftReport,
    result_path: str | None,
    client: GitHubIssueClient | None = None,
) -> str | None:
    """Create one drift issue per open fingerprint."""

    fingerprint = _report_fingerprint(report)
    github_client = client or GitHubIssueClient(repo=repo, token=token)
    try:
        if github_client.search_open_drift_issue(fingerprint):
            print(f"Found existing open drift issue for fingerprint {fingerprint}")
            return None
        severity = report.severity.value
        issue_url = github_client.create_issue(
            title=f"[DRIFT:{severity.upper()}] {agent_name} evaluation drift",
            body=_issue_body(agent_name, report, fingerprint, result_path),
            labels=["evaluation", f"drift:{severity}"],
        )
        if issue_url:
            print(f"Created drift issue: {issue_url}")
        return issue_url
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"Failed to create drift issue: {exc}")
        return None


def _issue_body(
    agent_name: str,
    report: DriftReport,
    fingerprint: str,
    result_path: str | None,
) -> str:
    lines = [
        f"Agent: **{agent_name}**",
        f"Severity: **{report.severity.value}**",
        f"Baseline: `{report.baseline_id or 'n/a'}`",
        f"Consecutive failures: `{report.consecutive_failures}`",
        f"Fingerprint: `{fingerprint}`",
        "",
        "Breached metrics:",
    ]
    lines.extend(f"- `{item}`" for item in report.breached_thresholds)
    lines.extend(["", "Drift magnitude:"])
    lines.extend(
        f"- `{key}`: `{value}`" for key, value in sorted(report.drift_metrics.items())
    )
    if result_path:
        lines.extend(["", f"Evaluation result path: `{result_path}`"])
    return "\n".join(lines)


def _report_fingerprint(report: DriftReport) -> str:
    parts = [
        *sorted(report.breached_thresholds),
        *[f"{key}:{round(value, 4)}" for key, value in sorted(report.drift_metrics.items())],
    ]
    return "|".join(parts) or "no-drift-details"


def _write_log(
    path: Path,
    agent_name: str,
    payload: dict[str, Any],
    issue_url: str | None,
) -> None:
    lines = [
        f"agent={agent_name}",
        f"status={payload.get('status')}",
        f"backend={payload.get('backend')}",
        f"drift_detected={payload.get('drift_detected')}",
    ]
    if issue_url:
        lines.append(f"issue_url={issue_url}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    """Run the monitor CLI."""

    return asyncio.run(run_monitor(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())