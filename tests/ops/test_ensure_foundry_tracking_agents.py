"""Unit tests for ``scripts/ops/ensure_foundry_tracking_agents.py``.

Covers the pure-logic functions in the ensure script. Network paths
(``_acquire_token``, ``_request``, ``_list_assistants``,
``_create_assistant``, ``_update_assistant``) are intentionally not
exercised here — they are validated by the deploy-time integration job and
by the ``verify_foundry_prompt.py`` gate that the script feeds.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ops" / "ensure_foundry_tracking_agents.py"


# Module loaded once per test session — the script is dependency-light and
# loading it as a module keeps imports out of the script's CLI path.
@pytest.fixture(scope="module")
def ensure_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ensure_foundry_tracking_agents", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_script_module_loads(ensure_module: ModuleType) -> None:
    assert hasattr(ensure_module, "main")
    assert hasattr(ensure_module, "_compose_published_prompt")
    assert hasattr(ensure_module, "_discover_services")


def test_compose_published_prompt_empty(ensure_module: ModuleType) -> None:
    composed = ensure_module._compose_published_prompt("")
    assert "## Foundry Runtime Security and Tool Policy" in composed


def test_compose_published_prompt_already_hardened(ensure_module: ModuleType) -> None:
    raw = "Body.\n## Foundry Runtime Security and Tool Policy\nx\n"
    assert ensure_module._compose_published_prompt(raw) == raw


def test_compose_published_prompt_appends_block(ensure_module: ModuleType) -> None:
    raw = "Body.\n"
    composed = ensure_module._compose_published_prompt(raw)
    assert composed.startswith("Body.")
    assert composed.rstrip().endswith("- No extra keys beyond schema.")
    # The hardening block must appear exactly once.
    assert composed.count("## Foundry Runtime Security and Tool Policy") == 1


def test_normalize_handles_crlf(ensure_module: ModuleType) -> None:
    assert ensure_module._normalize("a\r\nb\r\n") == "a\nb\n"


def test_normalize_trims_trailing_blank_lines(ensure_module: ModuleType) -> None:
    assert ensure_module._normalize("a\n\n\n") == "a\n"


def test_discover_services_finds_twenty_six(ensure_module: ModuleType) -> None:
    services = ensure_module._discover_services()
    assert len(services) == 26
    names = {s.name for s in services}
    # Spot-check both clusters that need to be present.
    assert "truth-ingestion" in names
    assert "search-enrichment-agent" in names
    assert "crm-profile-aggregation" in names


def test_discover_services_each_has_prompt_file(ensure_module: ModuleType) -> None:
    for service in ensure_module._discover_services():
        assert (
            service.prompt_path.is_file()
        ), f"{service.name}: missing prompt at {service.prompt_path}"
        assert service.prompt_path.read_text(
            encoding="utf-8"
        ).strip(), f"{service.name}: prompt file is empty"


def test_desired_for_returns_role_specific_model(ensure_module: ModuleType) -> None:
    services = ensure_module._discover_services()
    sample = next(s for s in services if s.name == "truth-ingestion")
    fast_name, fast_model, fast_instr = ensure_module._desired_for(
        sample, "fast", fast_model="gpt-5-nano", rich_model="gpt-5"
    )
    rich_name, rich_model, rich_instr = ensure_module._desired_for(
        sample, "rich", fast_model="gpt-5-nano", rich_model="gpt-5"
    )
    assert fast_name == "truth-ingestion-fast"
    assert rich_name == "truth-ingestion-rich"
    assert fast_model == "gpt-5-nano"
    assert rich_model == "gpt-5"
    # Instructions content is identical for fast/rich — only the role
    # constraint in the hardening block disambiguates runtime behaviour.
    assert fast_instr == rich_instr
    assert "## Foundry Runtime Security and Tool Policy" in fast_instr


def test_hardening_block_matches_prompt_loader(ensure_module: ModuleType) -> None:
    """The hardening block must stay byte-identical to the lib constant.

    ``scripts/ci/verify_foundry_prompt.py`` and the runtime prompt loader both
    embed the same canonical block. Drift between the three locations would
    cause the verify gate to flag every agent as divergent right after this
    script runs. This test pins the ensure script to the lib copy.
    """
    sys.path.insert(0, str(REPO_ROOT / "lib" / "src"))
    try:
        from holiday_peak_lib.agents import prompt_loader  # type: ignore[import-not-found]
    finally:
        sys.path.pop(0)
    assert ensure_module._FOUNDRY_HARDENING_BLOCK == prompt_loader._FOUNDRY_HARDENING_BLOCK


@dataclass
class _FakeArgs:
    project_endpoint: str | None
    fast_model: str = "gpt-5-nano"
    rich_model: str = "gpt-5"
    dry_run: bool = False


def test_main_requires_project_endpoint(
    ensure_module: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("PROJECT_ENDPOINT", raising=False)
    # Override sys.argv to simulate a CLI invocation with no endpoint.
    monkeypatch.setattr(sys, "argv", ["ensure_foundry_tracking_agents.py"])
    rc = ensure_module.main()
    assert rc == 2
    captured = capsys.readouterr()
    assert "PROJECT_ENDPOINT" in captured.err
