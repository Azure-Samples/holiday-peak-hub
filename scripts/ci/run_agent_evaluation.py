"""Run one agent evaluation from its `.foundry` configuration."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
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


def parse_args() -> argparse.Namespace:
    """Parse command-line options.

    # No GoF pattern applies — command-line boundary parsing.
    """

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent-root", required=True, help="Path to the agent app root")
    parser.add_argument("--run-name", default="ci", help="Evaluation run name")
    parser.add_argument(
        "--prefer-foundry",
        action="store_true",
        help="Use Azure AI Evaluation when the optional SDK is available",
    )
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="Exit non-zero when drift is detected",
    )
    parser.add_argument(
        "--write-result",
        help="Optional path to write the normalized evaluation event JSON",
    )
    return parser.parse_args()


async def run_agent_evaluation(args: argparse.Namespace) -> int:
    """Execute evaluation for one agent root."""

    agent_root = Path(args.agent_root).resolve()
    loader = DatasetLoader(agent_root / ".foundry")
    runner = ConfiguredEvaluationRunner(loader=loader, prefer_foundry=args.prefer_foundry)
    result = await runner.run(run_name=str(args.run_name))

    baseline = loader.load_baseline(runner.config)
    drift_report = DriftDetector(runner.config).detect(
        result,
        baseline=baseline,
        run_name=str(args.run_name),
    )
    event = EvaluationResultEvent(
        agent_name=runner.config.agent_name,
        run_name=str(args.run_name),
        backend=result.backend,
        status=result.status,
        metrics=_float_metrics(result.metrics),
        drift_detected=drift_report is not None,
        drift_report=drift_report,
        details=result.details,
    )
    payload = event.model_dump(mode="json")
    print(json.dumps(payload, indent=2, sort_keys=True))

    if args.write_result:
        result_path = Path(args.write_result).resolve()
        result_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    if args.fail_on_drift and drift_report is not None:
        return 2
    return 0


def _float_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for key, value in metrics.items():
        try:
            normalized[key] = float(value)
        except (TypeError, ValueError):
            continue
    return normalized


def main() -> int:
    return asyncio.run(run_agent_evaluation(parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
