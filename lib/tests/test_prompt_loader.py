"""Tests for structured prompt loader utilities."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from holiday_peak_lib.agents import prompt_loader
from holiday_peak_lib.agents.prompt_loader import (
    PromptInstructionsNotFoundError,
    is_fallback_instructions,
    load_prompt_instructions,
    load_service_prompt_instructions,
    prompt_instructions_sha256,
)


def test_load_prompt_instructions_reads_utf8_file(tmp_path: Path) -> None:
    service_root = tmp_path / "apps" / "sample-service"
    agents_file = service_root / "src" / "sample_service" / "agents.py"
    prompts_file = service_root / "prompts" / "instructions.md"

    agents_file.parent.mkdir(parents=True)
    agents_file.write_text("# placeholder", encoding="utf-8")
    prompts_file.parent.mkdir(parents=True)
    prompts_file.write_text("## Identity and Role\nSample instructions", encoding="utf-8")

    loaded = load_prompt_instructions(str(agents_file), "sample-service")
    assert "## Identity and Role" in loaded
    assert "Sample instructions" in loaded
    assert "## Foundry Runtime Security and Tool Policy" in loaded
    assert "Max calls per request" in loaded
    assert prompt_loader.LAST_LOAD_WAS_FALLBACK is False


def test_load_prompt_instructions_fallback_message_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FOUNDRY_STRICT_ENFORCEMENT", raising=False)
    monkeypatch.chdir(tmp_path)
    service_root = tmp_path / "apps" / "missing-service"
    agents_file = service_root / "src" / "missing_service" / "agents.py"
    agents_file.parent.mkdir(parents=True)
    agents_file.write_text("# placeholder", encoding="utf-8")

    loaded = load_prompt_instructions(str(agents_file), "missing-service")
    assert "Structured instructions file not found" in loaded
    assert "missing-service" in loaded
    assert "## Foundry Runtime Security and Tool Policy" in loaded
    assert prompt_loader.LAST_LOAD_WAS_FALLBACK is True
    assert is_fallback_instructions(loaded) is True


def test_load_service_prompt_instructions_from_repo_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prompt_path = tmp_path / "apps" / "test-service" / "prompts" / "instructions.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("## Identity and Role\nRepo prompt", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    loaded = load_service_prompt_instructions("test-service")
    assert loaded is not None
    assert "Repo prompt" in loaded
    assert "## Foundry Runtime Security and Tool Policy" in loaded


def test_load_prompt_instructions_strict_mode_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FOUNDRY_STRICT_ENFORCEMENT", "true")
    monkeypatch.chdir(tmp_path)
    agents_file = tmp_path / "apps" / "nope" / "src" / "nope_pkg" / "agents.py"
    agents_file.parent.mkdir(parents=True)
    agents_file.write_text("# placeholder", encoding="utf-8")

    with pytest.raises(PromptInstructionsNotFoundError) as exc:
        load_prompt_instructions(str(agents_file), "nope-service")
    assert exc.value.service_name == "nope-service"
    assert exc.value.searched_paths
    assert prompt_loader.LAST_LOAD_WAS_FALLBACK is False


def test_load_prompt_instructions_uses_package_data(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("FOUNDRY_STRICT_ENFORCEMENT", raising=False)
    pkg_root = tmp_path / "pkgroot"
    pkg_dir = pkg_root / "fake_pkg_for_prompt_loader"
    prompts_dir = pkg_dir / "prompts"
    prompts_dir.mkdir(parents=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (prompts_dir / "__init__.py").write_text("", encoding="utf-8")
    (prompts_dir / "instructions.md").write_text(
        "## Identity and Role\nPackaged prompt content", encoding="utf-8"
    )
    agents_file = pkg_dir / "agents.py"
    agents_file.write_text("# placeholder", encoding="utf-8")

    monkeypatch.syspath_prepend(str(pkg_root))
    sys.modules.pop("fake_pkg_for_prompt_loader", None)
    try:
        loaded = load_prompt_instructions(str(agents_file), "fake-service")
    finally:
        sys.modules.pop("fake_pkg_for_prompt_loader", None)

    assert "Packaged prompt content" in loaded
    assert prompt_loader.LAST_LOAD_WAS_FALLBACK is False
    assert is_fallback_instructions(loaded) is False


def test_prompt_instructions_sha256_is_stable() -> None:
    digest = prompt_instructions_sha256("hello")
    assert digest == ("2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824")


def test_is_fallback_instructions_discriminates() -> None:
    fallback = (
        "Structured instructions file not found for 'svc'. Expected UTF-8 markdown. "
        "Use only provided request data."
    )
    real = "## Identity and Role\nYou are the agent."
    assert is_fallback_instructions(fallback) is True
    assert is_fallback_instructions(real) is False
    assert is_fallback_instructions("") is False
