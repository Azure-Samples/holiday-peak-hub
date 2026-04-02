#!/usr/bin/env python3
"""Run repository push gate checks aligned with CI lint/test workflows."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def run_step(command: list[str], *, title: str) -> None:
    print(f"\n==> {title}")
    print("$", " ".join(command))
    subprocess.run(command, check=True, cwd=ROOT)


def run_lint_gate() -> None:
    run_step(
        ["python", "-m", "isort", "--check-only", "lib", "apps"],
        title="Lint gate: isort",
    )
    run_step(
        ["python", "-m", "black", "--check", "lib", "apps"],
        title="Lint gate: black",
    )

    pylint_targets = [str(ROOT / "lib" / "src")]
    pylint_targets.extend(
        str(path)
        for path in sorted((ROOT / "apps").glob("*/src"))
        if (path / "pyproject.toml").exists()
    )
    run_step(
        ["python", "-m", "pylint", "--fail-on=E,F", *pylint_targets],
        title="Lint gate: pylint",
    )

    run_step(
        [
            "python",
            "scripts/ops/check_markdown_links.py",
            "--roots",
            "docs/governance",
            "docs/architecture/README.md",
        ],
        title="Lint gate: governance/architecture links",
    )

    stale_tokens = (
        "OPERATIONAL-WORKFLOWS.md",
        "REPOSITORY-SURFACES.md",
        "governance-map.md",
    )
    agents_root = ROOT / ".github" / "agents"
    stale_refs: list[str] = []
    if agents_root.exists():
        for file_path in sorted(agents_root.rglob("*.md")):
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if any(token in content for token in stale_tokens):
                stale_refs.append(str(file_path.relative_to(ROOT)))

    if stale_refs:
        print("\nFound stale canonical governance references:")
        for item in stale_refs:
            print(f"- {item}")
        raise RuntimeError("Stale canonical governance references found in .github/agents")


def run_test_gate() -> None:
    run_step(
        ["pytest", "lib/tests", "--maxfail=1"],
        title="Test gate: lib tests",
    )

    app_test_dirs = [
        str(path)
        for path in sorted((ROOT / "apps").glob("*/tests"))
        if path.is_dir() and path.name == "tests"
    ]
    run_step(
        ["pytest", *app_test_dirs, "--ignore=apps/ui/tests"],
        title="Test gate: app tests (excluding UI tests)",
    )


def main() -> int:
    try:
        run_lint_gate()
        run_test_gate()
    except subprocess.CalledProcessError as exc:
        print(f"\nPush gate failed at exit code {exc.returncode}")
        return exc.returncode
    except Exception as exc:  # pylint: disable=broad-exception-caught
        print(f"\nPush gate failed: {exc}")
        return 1

    print("\nPush gate passed: lint + test checks match CI workflow expectations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
