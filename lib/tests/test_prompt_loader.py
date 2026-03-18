"""Tests for structured prompt loader utilities."""

from pathlib import Path

from holiday_peak_lib.agents.prompt_loader import (
    load_prompt_instructions,
    load_service_prompt_instructions,
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


def test_load_prompt_instructions_fallback_message_when_missing(tmp_path: Path) -> None:
    service_root = tmp_path / "apps" / "missing-service"
    agents_file = service_root / "src" / "missing_service" / "agents.py"
    agents_file.parent.mkdir(parents=True)
    agents_file.write_text("# placeholder", encoding="utf-8")

    loaded = load_prompt_instructions(str(agents_file), "missing-service")
    assert "Structured instructions file not found" in loaded
    assert "missing-service" in loaded
    assert "## Foundry Runtime Security and Tool Policy" in loaded


def test_load_service_prompt_instructions_from_repo_layout(tmp_path: Path, monkeypatch) -> None:
    prompt_path = tmp_path / "apps" / "test-service" / "prompts" / "instructions.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("## Identity and Role\nRepo prompt", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    loaded = load_service_prompt_instructions("test-service")
    assert loaded is not None
    assert "Repo prompt" in loaded
    assert "## Foundry Runtime Security and Tool Policy" in loaded
