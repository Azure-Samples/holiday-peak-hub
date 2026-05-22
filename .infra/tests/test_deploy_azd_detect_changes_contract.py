from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = ROOT / ".github" / "workflows" / "deploy-azd.yml"
DETECT_MARKER = "      - name: Detect changed services\n"
PROVISION_MARKER = "  provision:\n"


def _detect_block() -> str:
    content = WORKFLOW_PATH.read_text(encoding="utf-8")
    assert content.count(DETECT_MARKER) == 1
    return content.split(DETECT_MARKER, 1)[1].split(PROVISION_MARKER, 1)[0]


def test_workflow_run_source_sha_diff_fetches_enough_parent_history() -> None:
    block = _detect_block()

    assert 'git fetch origin "$DEFAULT_BRANCH" --depth=1' not in block
    assert 'git fetch origin "$DEFAULT_BRANCH" || true' in block
    assert "Source SHA parent is unavailable; fetching additional default branch history." in block
    assert (
        'git fetch origin "$DEFAULT_BRANCH" --deepen=50 || git fetch origin "$DEFAULT_BRANCH" || true'
        in block
    )
    assert "source-sha-first-parent-three-dot" in block
    assert "Source SHA parent for '${TARGET_SHA}' is unavailable" in block

    source_sha_fetch = block.index(
        "Source SHA parent is unavailable; fetching additional default branch history."
    )
    source_sha_strategy = block.index("source-sha-first-parent-three-dot")
    default_branch_fallback = block.index('if [ -z "$DIFF_RANGE" ]; then')

    assert source_sha_fetch < source_sha_strategy < default_branch_fallback
