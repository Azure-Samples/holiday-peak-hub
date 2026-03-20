"""Schema registry guardrails for duplicate model definitions."""

from __future__ import annotations

import inspect

import holiday_peak_lib.schemas.search as search_schemas
import holiday_peak_lib.schemas.truth as truth_schemas


def _defined_model_names(module: object) -> set[str]:
    names: set[str] = set()
    module_name = getattr(module, "__name__", "")
    for name, value in vars(module).items():
        if not inspect.isclass(value):
            continue
        if getattr(value, "__module__", "") != module_name:
            continue
        if name.startswith("_"):
            continue
        names.add(name)
    return names


def test_no_duplicate_model_definitions_between_search_and_truth_modules() -> None:
    duplicates = _defined_model_names(search_schemas).intersection(
        _defined_model_names(truth_schemas)
    )
    assert duplicates == set(), f"Duplicate schema model definitions found: {duplicates}"
