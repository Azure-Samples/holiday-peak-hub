"""Local quadratic support checks for ASB setup surfaces."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any


def compute_quadratic_support(
    grid_search_path: Path | str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Compute scalar and multivariate local support rows from grid-search output."""

    rows = _read_rows(Path(grid_search_path))
    if not rows:
        return [], []
    selected = next((row for row in rows if str(row.get("selected")).lower() == "true"), rows[0])
    scalar_rows = []
    for coordinate in (
        "retrieval_depth",
        "memory_policy",
        "tool_budget",
        "token_budget",
        "topology_policy",
        "hitl_policy",
    ):
        selected_value = float(selected[coordinate])
        values = sorted(rows, key=_distance_from_selected(coordinate, selected_value))
        local = values[: min(3, len(values))]
        curvature = _local_curvature(local)
        scalar_rows.append(
            {
                "coordinate": coordinate,
                "selected_value": selected[coordinate],
                "support_status": _support_status(curvature),
                "curvature": round(curvature, 6),
                "local_points": len(local),
            }
        )
    multivariate = [
        {
            "claim_id": "C7-PRODUCTION-LIKE-WORKLOAD",
            "support_rows": sum(1 for row in scalar_rows if row["support_status"] == "supported"),
            "selected_rows": 1,
            "status": (
                "supported"
                if any(row["support_status"] == "supported" for row in scalar_rows)
                else "weak"
            ),
        }
    ]
    return scalar_rows, multivariate


def write_quadratic_support(grid_search_path: Path | str, output_dir: Path | str) -> None:
    """Write scalar and multivariate QLST artifacts."""

    scalar_rows, multivariate_rows = compute_quadratic_support(grid_search_path)
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(target_dir / "qlst-scalar.csv", scalar_rows)
    _write_csv(target_dir / "qlst-multivariate.csv", multivariate_rows)


def _local_curvature(rows: list[dict[str, str]]) -> float:
    if len(rows) < 3:
        return 0.0
    risks = [float(row["risk"]) for row in rows[:3]]
    return risks[0] - 2 * risks[1] + risks[2]


def _distance_from_selected(coordinate: str, selected_value: float):
    def distance(row: dict[str, str]) -> float:
        return abs(float(row[coordinate]) - selected_value)

    return distance


def _support_status(curvature: float) -> str:
    if curvature > 0:
        return "supported"
    if curvature == 0:
        return "flat"
    return "weak"


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
