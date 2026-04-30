#!/usr/bin/env python3
"""Validate ADR preflight and prompt/agent governance consistency."""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

BACKTICK_PATTERN = re.compile(r"`([^`]+)`")
TABLE_ROW_PATTERN = re.compile(r"^\|\s*`([^`]+)`\s*\|\s*`([^`]+)`\s*\|")

TEAM_MAPPING_PATH = Path(".github/agents/data/team-mapping.md")
PROMPTS_DIR = Path(".github/prompts")


@dataclass(frozen=True)
class PromptPolicy:
    """Defines consistency checks for a governance-critical prompt file."""

    required_snippets: tuple[str, ...]
    required_canonical_agents: tuple[str, ...]


TARGET_PROMPT_POLICIES: dict[Path, PromptPolicy] = {
    Path(".github/prompts/issue-engineering-with-process.prompt.md"): PromptPolicy(
        required_snippets=("ADR Preflight", "docs/architecture/ADRs.md", "#runSubagent"),
        required_canonical_agents=(
            "system-architect",
            "python-specialist",
            "typescript-specialist",
            "rust-specialist",
            "ui-agent",
            "platform-quality",
        ),
    ),
    Path(".github/prompts/tech-lead-plan.prompt.md"): PromptPolicy(
        required_snippets=(
            "ADR Preflight",
            "docs/architecture/ADRs.md",
            ".github/skills/issue-engineering-workflows/SKILL.md",
        ),
        required_canonical_agents=(
            "python-specialist",
            "rust-specialist",
            "typescript-specialist",
            "ui-agent",
            "platform-quality",
            "system-architect",
            "pr-evaluator",
        ),
    ),
    Path(".github/prompts/tech-lead-issue-execute.prompt.md"): PromptPolicy(
        required_snippets=("ADR Preflight", "docs/architecture/ADRs.md", "#runSubagent"),
        required_canonical_agents=(
            "python-specialist",
            "rust-specialist",
            "typescript-specialist",
            "ui-agent",
            "platform-quality",
            "system-architect",
            "enterprise-connectors",
            "pr-evaluator",
        ),
    ),
}

REQUIRED_SNIPPETS_BY_FILE: dict[Path, tuple[str, ...]] = {
    Path(".github/skills/issue-engineering-workflows/SKILL.md"): (
        "ADR preflight",
        "docs/architecture/ADRs.md",
    ),
    Path(".github/agents/tech-manager.agent.md"): (
        "Documentation-First Protocol",
        ".github/agents/data/team-mapping.md",
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate ADR preflight and prompt/agent governance consistency."
    )
    parser.add_argument(
        "--report-file",
        default="",
        help="Optional path for a markdown report (workspace-relative).",
    )
    return parser.parse_args()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _frontmatter_value(text: str, key: str) -> str:
    if not text.startswith("---\n"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    frontmatter = parts[1]
    match = re.search(rf'^{re.escape(key)}:\s*"?([^"\n]+)"?\s*$', frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _parse_team_mapping(repo_root: Path) -> dict[str, Path]:
    mapping_path = repo_root / TEAM_MAPPING_PATH
    mapping: dict[str, Path] = {}
    for line in _read_text(mapping_path).splitlines():
        match = TABLE_ROW_PATTERN.match(line.strip())
        if not match:
            continue
        canonical_name, agent_file = match.groups()
        if not agent_file.endswith(".agent.md"):
            continue
        mapping[canonical_name] = Path(agent_file)
    return mapping


def _canonical_runtime_names(
    repo_root: Path, canonical_to_file: dict[str, Path]
) -> tuple[dict[str, str], list[str]]:
    runtime_by_canonical: dict[str, str] = {}
    errors: list[str] = []

    for canonical_name, agent_file in canonical_to_file.items():
        agent_path = (repo_root / agent_file).resolve()
        if not agent_path.exists():
            errors.append(
                f"{TEAM_MAPPING_PATH}: mapped agent file '{agent_file.as_posix()}' is missing"
            )
            continue
        runtime_name = _frontmatter_value(_read_text(agent_path), "name")
        if not runtime_name:
            # Repo-local support agents may intentionally omit a frontmatter name.
            continue
        runtime_by_canonical[canonical_name] = runtime_name

    return runtime_by_canonical, errors


def _validate_prompt_targets(repo_root: Path, runtime_names: set[str]) -> list[str]:
    errors: list[str] = []
    for prompt_path in sorted((repo_root / PROMPTS_DIR).glob("*.prompt.md")):
        prompt_text = _read_text(prompt_path)
        prompt_agent = _frontmatter_value(prompt_text, "agent")
        relative_prompt = prompt_path.relative_to(repo_root).as_posix()
        if not prompt_agent:
            errors.append(f"{relative_prompt}: missing frontmatter 'agent' value")
            continue
        if prompt_agent not in runtime_names:
            errors.append(
                f"{relative_prompt}: agent '{prompt_agent}' does not map to any registered .agent.md name"
            )
    return errors


def _validate_required_snippets(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path, snippets in REQUIRED_SNIPPETS_BY_FILE.items():
        file_path = repo_root / relative_path
        if not file_path.exists():
            errors.append(f"Missing required file: {relative_path.as_posix()}")
            continue
        content = _read_text(file_path)
        lowered = content.lower()
        for snippet in snippets:
            if snippet.lower() not in lowered:
                errors.append(
                    f"{relative_path.as_posix()}: missing required governance snippet '{snippet}'"
                )
    return errors


def _validate_target_prompts(
    repo_root: Path,
    runtime_by_canonical: dict[str, str],
    canonical_names: set[str],
) -> list[str]:
    errors: list[str] = []

    # No GoF pattern applies here: this script is a deterministic policy validator.
    for relative_prompt, policy in TARGET_PROMPT_POLICIES.items():
        prompt_path = repo_root / relative_prompt
        if not prompt_path.exists():
            errors.append(f"Missing required prompt: {relative_prompt.as_posix()}")
            continue

        prompt_text = _read_text(prompt_path)
        prompt_tokens = set(BACKTICK_PATTERN.findall(prompt_text))
        lowered = prompt_text.lower()

        for snippet in policy.required_snippets:
            if snippet.lower() not in lowered:
                errors.append(
                    f"{relative_prompt.as_posix()}: missing required snippet '{snippet}'"
                )

        for canonical_agent in policy.required_canonical_agents:
            if canonical_agent not in canonical_names:
                errors.append(
                    f"{relative_prompt.as_posix()}: canonical agent '{canonical_agent}' is not in team mapping"
                )
                continue

            if canonical_agent not in prompt_tokens:
                errors.append(
                    f"{relative_prompt.as_posix()}: missing canonical agent token '{canonical_agent}'"
                )

            runtime_alias = runtime_by_canonical.get(canonical_agent, "")
            if runtime_alias and runtime_alias in prompt_tokens:
                errors.append(
                    f"{relative_prompt.as_posix()}: uses runtime alias '{runtime_alias}' where canonical '{canonical_agent}' is required"
                )

    return errors


def _build_report(errors: list[str]) -> str:
    status = "PASSED" if not errors else "FAILED"
    lines = [
        "# Governance Drift Report",
        "",
        f"Status: {status}",
        "",
        "## Scope",
        "- ADR preflight coverage in governance-critical prompts and skill docs",
        "- Prompt frontmatter agent target validity against registered agent files",
        "- Canonical team-mapping agent naming in issue-engineering prompts",
        "",
    ]

    if not errors:
        lines.extend(["## Findings", "- No governance drift detected.", ""])
        return "\n".join(lines)

    lines.append("## Findings")
    lines.extend([f"- {error}" for error in errors])
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()

    if not (repo_root / TEAM_MAPPING_PATH).exists():
        print(f"Missing canonical team mapping file: {TEAM_MAPPING_PATH.as_posix()}")
        return 2

    canonical_to_file = _parse_team_mapping(repo_root)
    canonical_names = set(canonical_to_file.keys())

    runtime_by_canonical, mapping_errors = _canonical_runtime_names(
        repo_root, canonical_to_file
    )
    runtime_names = set(runtime_by_canonical.values())

    errors: list[str] = []
    errors.extend(mapping_errors)
    errors.extend(_validate_required_snippets(repo_root))
    errors.extend(_validate_prompt_targets(repo_root, runtime_names))
    errors.extend(_validate_target_prompts(repo_root, runtime_by_canonical, canonical_names))

    report = _build_report(errors)
    if args.report_file:
        report_path = (repo_root / args.report_file).resolve()
        report_path.write_text(report, encoding="utf-8")

    if errors:
        print("Governance prompt/agent consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Governance prompt/agent consistency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
