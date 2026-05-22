"""Load per-agent Foundry evaluation configuration and datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .models import EvalBaseline, EvalCase, EvalConfig

_CONFIG_FILE_NAME = "eval-config.yaml"
_FOUNDRY_DIR_NAME = ".foundry"


class DatasetLoader:
    """Repository for `.foundry` evaluation config and JSONL datasets.

    Pattern: Repository — isolates file storage details from evaluation runners.
    """

    def __init__(self, foundry_root: Path | str) -> None:
        self.foundry_root = Path(foundry_root).resolve()

    @classmethod
    def discover(cls, start_path: Path | str) -> "DatasetLoader | None":
        """Find the nearest parent `.foundry` directory from a starting path."""

        current = Path(start_path).resolve()
        if current.is_file():
            current = current.parent

        for candidate in (current, *current.parents):
            foundry_root = candidate / _FOUNDRY_DIR_NAME
            if (foundry_root / _CONFIG_FILE_NAME).exists():
                return cls(foundry_root)
        return None

    def load_config(self) -> EvalConfig:
        """Load and validate `.foundry/eval-config.yaml`."""

        config_path = self.foundry_root / _CONFIG_FILE_NAME
        if not config_path.exists():
            raise FileNotFoundError(f"Evaluation config not found: {config_path}")

        raw_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        if not isinstance(raw_config, dict):
            raise ValueError(f"Evaluation config must be a mapping: {config_path}")

        config_data: dict[str, Any] = dict(raw_config)
        config_data["foundry_root"] = self.foundry_root
        return EvalConfig.model_validate(config_data)

    def load_cases(self, config: EvalConfig | None = None) -> list[EvalCase]:
        """Load and validate JSONL cases referenced by the config."""

        resolved_config = config or self.load_config()
        dataset_path = self.resolve_path(resolved_config.dataset_path)
        if not dataset_path.exists():
            raise FileNotFoundError(f"Evaluation dataset not found: {dataset_path}")

        cases: list[EvalCase] = []
        with dataset_path.open("r", encoding="utf-8") as dataset_file:
            for line_number, raw_line in enumerate(dataset_file, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL at {dataset_path}:{line_number}: {exc.msg}"
                    ) from exc
                try:
                    cases.append(EvalCase.model_validate(payload))
                except ValidationError as exc:
                    raise ValueError(
                        f"Invalid evaluation case at {dataset_path}:{line_number}: {exc}"
                    ) from exc

        if not cases:
            raise ValueError(f"Evaluation dataset has no cases: {dataset_path}")
        return cases

    def load_baseline(self, config: EvalConfig | None = None) -> EvalBaseline | None:
        """Load an optional baseline referenced by the config."""

        resolved_config = config or self.load_config()
        if not resolved_config.baseline_path:
            return None
        baseline_path = self.resolve_path(resolved_config.baseline_path)
        if not baseline_path.exists():
            return None
        raw_baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        return EvalBaseline.model_validate(raw_baseline)

    def resolve_path(self, relative_or_absolute_path: str | Path) -> Path:
        """Resolve a config path relative to the `.foundry` root."""

        path = Path(relative_or_absolute_path)
        if path.is_absolute():
            return path
        return (self.foundry_root / path).resolve()
