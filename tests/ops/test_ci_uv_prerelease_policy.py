from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_lint_workflow_checks_app_locks_with_preview_policy() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "lint.yml").read_text(
        encoding="utf-8"
    )

    assert "grep -q 'prerelease-mode = \"allow\"' uv.lock" in workflow
    assert "uv lock --prerelease=allow --check" in workflow
    assert "uv lock --check" in workflow


def test_python_app_installs_allow_preview_dependency_chain() -> None:
    for workflow_name in ("test.yml", "lint.yml", "dependency-audit.yml"):
        workflow = (REPO_ROOT / ".github" / "workflows" / workflow_name).read_text(
            encoding="utf-8"
        )

        assert "uv pip install --system --prerelease=allow -e \"$d\"" in workflow