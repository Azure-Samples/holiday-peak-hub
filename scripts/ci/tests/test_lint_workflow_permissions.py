"""Unit tests for the workflow permission-cap linter.

Verifies that ``scripts/ci/lint_workflow_permissions.py`` correctly catches
the class of bug introduced by PR #1097 (and recorded in issue #1099):
a reusable callee declaring ``permissions:`` keys not granted by the caller's
``uses:`` job, which causes silent ``startup_failure`` at the GitHub
orchestrator.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

# tests/ is alongside the script: scripts/ci/lint_workflow_permissions.py
SCRIPT = Path(__file__).resolve().parents[1] / "lint_workflow_permissions.py"


def _run_linter_in(workspace: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        check=False,
    )


def _write_workflow(workspace: Path, name: str, body: str) -> None:
    target = workspace / ".github" / "workflows" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")


def test_linter_passes_when_caller_grants_required_permissions(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "callee.yml",
        """
        name: Callee
        on:
          workflow_call: {}
        jobs:
          do:
            runs-on: ubuntu-latest
            permissions:
              contents: write
              issues: write
            steps:
              - run: echo ok
        """,
    )
    _write_workflow(
        tmp_path,
        "caller.yml",
        """
        name: Caller
        on:
          push: {}
        jobs:
          invoke:
            permissions:
              contents: write
              issues: write
            uses: ./.github/workflows/callee.yml
        """,
    )

    result = _run_linter_in(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "no permission-cap violations" in result.stdout


def test_linter_flags_missing_pull_requests_grant(tmp_path: Path) -> None:
    """Regression: PR #1097 / issue #1099. Callee requires pull-requests:write,
    caller does not grant it -> GitHub rejects with startup_failure."""
    _write_workflow(
        tmp_path,
        "callee.yml",
        """
        name: Callee
        on:
          workflow_call: {}
        jobs:
          open-pr:
            runs-on: ubuntu-latest
            permissions:
              contents: write
              pull-requests: write
            steps:
              - run: echo open-pr
        """,
    )
    _write_workflow(
        tmp_path,
        "caller.yml",
        """
        name: Caller
        on:
          push: {}
        jobs:
          invoke:
            permissions:
              id-token: write
              contents: write
              issues: write
            uses: ./.github/workflows/callee.yml
        """,
    )

    result = _run_linter_in(tmp_path)
    assert result.returncode == 1, result.stdout
    assert "pull-requests" in result.stderr
    assert "startup_failure" in result.stderr


def test_linter_flags_read_only_caller_against_write_callee(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "callee.yml",
        """
        name: Callee
        on:
          workflow_call: {}
        jobs:
          push-tag:
            runs-on: ubuntu-latest
            permissions:
              contents: write
            steps:
              - run: echo push
        """,
    )
    _write_workflow(
        tmp_path,
        "caller.yml",
        """
        name: Caller
        on:
          push: {}
        jobs:
          invoke:
            permissions:
              contents: read
            uses: ./.github/workflows/callee.yml
        """,
    )

    result = _run_linter_in(tmp_path)
    assert result.returncode == 1, result.stdout
    assert "'contents: write'" in result.stderr


def test_linter_handles_callee_without_per_job_permissions(tmp_path: Path) -> None:
    _write_workflow(
        tmp_path,
        "callee.yml",
        """
        name: Callee
        on:
          workflow_call: {}
        jobs:
          do:
            runs-on: ubuntu-latest
            steps:
              - run: echo ok
        """,
    )
    _write_workflow(
        tmp_path,
        "caller.yml",
        """
        name: Caller
        on:
          push: {}
        jobs:
          invoke:
            uses: ./.github/workflows/callee.yml
        """,
    )

    result = _run_linter_in(tmp_path)
    assert result.returncode == 0
