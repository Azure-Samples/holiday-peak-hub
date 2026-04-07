"""Shared pytest fixtures for app-level smoke tests."""

from __future__ import annotations

import pytest
from holiday_peak_lib.app_factory_components.foundry_lifecycle import (
    FoundryReadinessSnapshot,
)


@pytest.fixture
def mock_foundry_readiness(monkeypatch: pytest.MonkeyPatch) -> None:
    # No GoF pattern applies — this pytest seam keeps app smoke tests focused on
    # service behavior once the shared Foundry readiness gate is satisfied.
    def _ready_foundry_snapshot(
        **kwargs: object,
    ) -> FoundryReadinessSnapshot:
        require_foundry_readiness = bool(kwargs.get("require_foundry_readiness", False))
        strict_foundry_mode = bool(kwargs.get("strict_foundry_mode", False))
        auto_ensure_on_startup = bool(kwargs.get("auto_ensure_on_startup", False))
        last_error = kwargs.get("last_error")
        if last_error is not None and not isinstance(last_error, dict):
            last_error = None

        return FoundryReadinessSnapshot(
            required=require_foundry_readiness,
            strict_mode=strict_foundry_mode,
            project_configured=True,
            endpoint_configured=True,
            configured_roles=("fast",),
            resolved_roles=("fast",),
            unresolved_roles=(),
            agent_targets_bound=True,
            runtime_resolution_required=False,
            auto_ensure_on_startup=auto_ensure_on_startup,
            last_error=last_error,
        )

    monkeypatch.setattr(
        "holiday_peak_lib.app_factory.build_foundry_readiness_snapshot",
        _ready_foundry_snapshot,
    )
