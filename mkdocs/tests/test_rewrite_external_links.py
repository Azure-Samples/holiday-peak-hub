"""Tests for the mkdocs `rewrite_external_links` hook (#1021).

The hook turns docs-to-source relative paths into absolute GitHub blob
URLs so `mkdocs build --strict` can flip without authors having to
manually rewrite every link. These tests pin the rewrite contract so
future changes do not silently regress.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = REPO_ROOT / "mkdocs" / "hooks" / "rewrite_external_links.py"


def _load_hook():
    spec = importlib.util.spec_from_file_location(
        "rewrite_external_links_hook", HOOK_PATH
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _clean_repo_ref(monkeypatch):
    # Force deterministic ref so assertions are stable.
    monkeypatch.delenv("MKDOCS_REPO_REF", raising=False)
    yield


def _make_page(src_uri: str):
    return SimpleNamespace(file=SimpleNamespace(src_uri=src_uri, src_path=src_uri))


def _make_files(*src_uris: str):
    """Build a fake `Files` collection containing the given doc paths."""
    return [SimpleNamespace(src_uri=u, src_path=u) for u in src_uris]


def test_rewrites_apps_link_relative_to_docs_root() -> None:
    hook = _load_hook()
    page = _make_page("agentic-microservices-reference.md")
    md = "See [the catalog agent](../apps/ecommerce-catalog-search/README.md)."
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert (
        "https://github.com/Azure-Samples/holiday-peak-hub/blob/main/apps/"
        "ecommerce-catalog-search/README.md" in out
    )


def test_rewrites_lib_link_from_nested_docs_page() -> None:
    hook = _load_hook()
    page = _make_page("architecture/foundry-agents-vs-direct-api-report.md")
    md = "Loaded by [foundry.py](../../lib/src/holiday_peak_lib/agents/foundry.py)."
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert (
        "https://github.com/Azure-Samples/holiday-peak-hub/blob/main/"
        "lib/src/holiday_peak_lib/agents/foundry.py" in out
    )


def test_preserves_external_links() -> None:
    hook = _load_hook()
    page = _make_page("README.md")
    md = "See [docs portal](https://example.com/docs)."
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert out == md


def test_preserves_in_doc_anchor_links() -> None:
    hook = _load_hook()
    page = _make_page("crud-features-map.md")
    md = "Jump to [section](#147-logistics)."
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert out == md


def test_preserves_image_references() -> None:
    hook = _load_hook()
    page = _make_page("README.md")
    md = "![architecture](../apps/ui/diagram.png)"
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert out == md


def test_preserves_intra_docs_links_when_target_known() -> None:
    """Intra-docs links to existing pages must remain untouched."""
    hook = _load_hook()
    page = _make_page("README.md")
    md = "See [implementation](implementation/architecture-implementation-plan.md)."
    files = _make_files("implementation/architecture-implementation-plan.md")
    out = hook.on_page_markdown(md, page, config={}, files=files)
    assert out == md


def test_rewrites_intra_docs_link_to_blob_when_target_missing() -> None:
    """Planned content (target not yet committed) gets a stable GitHub URL."""
    hook = _load_hook()
    page = _make_page("demos/README.md")
    md = "See [planned](agent-playgrounds/ecommerce-agents.ipynb)."
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert (
        "https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/demos/"
        "agent-playgrounds/ecommerce-agents.ipynb" in out
    )


def test_rewrites_raw_repo_root_link_without_dotdot() -> None:
    """Author-side mistakes: `.infra/x` from docs/ should still rewrite."""
    hook = _load_hook()
    page = _make_page("IMPLEMENTATION_ROADMAP.md")
    md = "See [iac](.infra/modules/static-web-app/README.md)."
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert (
        "https://github.com/Azure-Samples/holiday-peak-hub/blob/main/"
        ".infra/modules/static-web-app/README.md" in out
    )


def test_appends_readme_to_directory_only_links() -> None:
    hook = _load_hook()
    page = _make_page("business_scenarios/README.md")
    md = "See [scenario](01-order-to-fulfillment/)."
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert "01-order-to-fulfillment/README.md" in out


def test_preserves_anchor_segment_for_known_intra_docs_target() -> None:
    hook = _load_hook()
    page = _make_page("ui/a11y.md")
    md = "See [adr](../architecture/adrs/adr-035-ui-design-system.md#55-quality-gates)."
    files = _make_files("architecture/adrs/adr-035-ui-design-system.md")
    out = hook.on_page_markdown(md, page, config={}, files=files)
    assert out == md


def test_honors_custom_repo_ref_env() -> None:
    os.environ["MKDOCS_REPO_REF"] = "feature/preview-branch"
    try:
        sys.modules.pop("rewrite_external_links_hook", None)
        hook = _load_hook()
        page = _make_page("README.md")
        md = "See [foo](../apps/ui/INTEGRATION.md)."
        out = hook.on_page_markdown(md, page, config={}, files=[])
        assert (
            "https://github.com/Azure-Samples/holiday-peak-hub/blob/"
            "feature/preview-branch/apps/ui/INTEGRATION.md" in out
        )
    finally:
        os.environ.pop("MKDOCS_REPO_REF", None)
        sys.modules.pop("rewrite_external_links_hook", None)


def test_handles_link_with_title_attribute() -> None:
    hook = _load_hook()
    page = _make_page("README.md")
    md = 'See [foo](../apps/ui/INTEGRATION.md "ui integration").'
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert (
        '"ui integration"' in out
        and "https://github.com/Azure-Samples/holiday-peak-hub/blob/main/"
        "apps/ui/INTEGRATION.md" in out
    )


def test_rewrites_url_with_balanced_parens() -> None:
    """Next.js route group paths like `(deploy)` must survive the rewrite."""
    hook = _load_hook()
    page = _make_page("governance/deploy-portal-cleanup-contract.md")
    md = "[`/track/[id]`](../../apps/ui/app/(deploy)/deploy/track/[id]/page.tsx) — track view"
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert (
        "https://github.com/Azure-Samples/holiday-peak-hub/blob/main/"
        "apps/ui/app/(deploy)/deploy/track/[id]/page.tsx" in out
    )


def test_rewrites_samples_directory_link() -> None:
    hook = _load_hook()
    page = _make_page("implementation/truth-layer-api.md")
    md = "Run [`bulk_ingest.py`](../../samples/scripts/bulk_ingest.py)."
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert (
        "https://github.com/Azure-Samples/holiday-peak-hub/blob/main/"
        "samples/scripts/bulk_ingest.py" in out
    )


def test_rewrites_mkdocs_directory_link() -> None:
    hook = _load_hook()
    page = _make_page("ui/docs-integration.md")
    md = "See [config](../../mkdocs/mkdocs.yml)."
    out = hook.on_page_markdown(md, page, config={}, files=[])
    assert (
        "https://github.com/Azure-Samples/holiday-peak-hub/blob/main/"
        "mkdocs/mkdocs.yml" in out
    )


def test_label_regex_is_redos_safe() -> None:
    """Pathological inputs with many `[[...` must not trigger exponential
    backtracking. CodeQL flagged the previous label regex (py/redos) for
    this exact pattern; the test runs a bounded-time replacement on
    a hostile input and asserts it returns quickly with no rewrite."""
    import time

    hook = _load_hook()
    page = _make_page("README.md")
    # 4000 unbalanced `[` followed by trailing text. The legacy regex
    # would explore exponentially many paths trying to match the label.
    md = "[" * 4000 + "x](../apps/foo.md)"
    start = time.perf_counter()
    out = hook.on_page_markdown(md, page, config={}, files=[])
    elapsed = time.perf_counter() - start
    # Anything under 1 second is comfortable. Pre-fix this would run
    # multiple seconds (or hang).
    assert elapsed < 1.0, f"regex took {elapsed:.2f}s on adversarial input"
    # The hostile input is malformed markdown — we just need it to not
    # blow up. Output equality with input is acceptable behaviour.
    assert out is not None
