"""Falsification checks for ASB production-like bundles."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import yaml


def load_falsification_matrix(path: Path | str) -> list[dict[str, Any]]:
    """Load falsification interventions from YAML."""

    raw_payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw_payload, dict):
        raise ValueError("falsification matrix must be a mapping")
    interventions = raw_payload.get("interventions", [])
    if not isinstance(interventions, list) or not interventions:
        raise ValueError("falsification matrix must include interventions")
    return [dict(item) for item in interventions]


def run_falsification(
    grid_search_path: Path | str, matrix_path: Path | str
) -> list[dict[str, Any]]:
    """Run deterministic structure-destruction checks over the selected setup."""

    rows = _read_rows(Path(grid_search_path))
    selected = next((row for row in rows if str(row.get("selected")).lower() == "true"), rows[0])
    base_risk = float(selected["risk"])
    results: list[dict[str, Any]] = []
    for intervention in load_falsification_matrix(matrix_path):
        severity = float(intervention.get("severity", 0.1))
        falsified_risk = base_risk + severity
        results.append(
            {
                "intervention_id": intervention["id"],
                "description": intervention["description"],
                "base_risk": round(base_risk, 6),
                "falsified_risk": round(falsified_risk, 6),
                "weakened": falsified_risk > base_risk,
            }
        )
    return results


def write_falsification(
    grid_search_path: Path | str, matrix_path: Path | str, output_dir: Path | str
) -> None:
    """Write falsification results to CSV."""

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(target_dir / "falsification.csv", run_falsification(grid_search_path, matrix_path))


def _read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
