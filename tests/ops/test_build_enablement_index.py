"""Unit tests for ``scripts/ops/build_enablement_index.py`` (Issue #1052)."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ops" / "build_enablement_index.py"

# Load by file path so the test does not depend on `scripts/ops` being on
# `sys.path` at test collection time. Register in sys.modules before exec so
# Python 3.13's dataclass machinery can introspect the module namespace.
_MODULE_NAME = "build_enablement_index_under_test"
spec = importlib.util.spec_from_file_location(_MODULE_NAME, SCRIPT_PATH)
assert spec and spec.loader, "build_enablement_index.py must be importable"
beim = importlib.util.module_from_spec(spec)
sys.modules[_MODULE_NAME] = beim
spec.loader.exec_module(beim)


def _write_asset(
    tmp_path: Path,
    *,
    relpath: str,
    title: str,
    kind: str,
    owner: str,
    last_reviewed: str,
    attribution_status: str | None = None,
    permission_doc: str | None = None,
    extra_field: str | None = None,
) -> Path:
    """Create an asset markdown file with the given front-matter."""

    target = tmp_path / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    fm_lines = [
        "---",
        f'title: "{title}"',
        f"kind: {kind}",
        f"owner: {owner}",
        f"last_reviewed: {last_reviewed}",
    ]
    if attribution_status is not None:
        fm_lines.append(f"attribution_status: {attribution_status}")
    if permission_doc is not None:
        fm_lines.append(f"permission_doc: {permission_doc}")
    if extra_field is not None:
        fm_lines.append(f"extra_unknown_field: {extra_field}")
    fm_lines.append("---")
    fm_lines.append("")
    fm_lines.append("Body content goes here.")
    target.write_text("\n".join(fm_lines), encoding="utf-8")
    return target


# -- happy path -------------------------------------------------------------


def test_battle_card_within_window_is_included(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="battle-cards/vs-algolia.md",
        title="Vs Algolia",
        kind="battle-card",
        owner="ricardo-cataldi",
        last_reviewed="2025-10-01",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert result.errors == []
    assert result.expired_count == 0
    assert len(result.assets) == 1
    asset = result.assets[0]
    assert asset["kind"] == "battle-card"
    assert asset["title"] == "Vs Algolia"
    # 90 - (2025-11-04 - 2025-10-01) = 90 - 34 = 56
    assert asset["daysToExpiry"] == 56


def test_demo_script_window_is_180_days(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="demos/holiday-peak-narrated.md",
        title="Holiday Peak narrated demo",
        kind="demo-script",
        owner="ricardo-cataldi",
        last_reviewed="2025-08-01",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert result.errors == []
    assert len(result.assets) == 1
    # 180 - (2025-11-04 - 2025-08-01) = 180 - 95 = 85
    assert result.assets[0]["daysToExpiry"] == 85


def test_winloss_never_expires_and_is_immutable(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="win-loss/2024-q1-acme.md",
        title="ACME Q1 2024 win",
        kind="win-loss",
        owner="ricardo-cataldi",
        last_reviewed="2020-01-01",  # ancient
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert result.errors == []
    assert result.expired_count == 0
    assert len(result.assets) == 1
    # Immutable assets carry None for daysToExpiry in the artifact.
    assert result.assets[0]["daysToExpiry"] is None


def test_approved_quote_is_included(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="quotes/acme-cto.md",
        title="ACME CTO quote",
        kind="customer-quote",
        owner="ricardo-cataldi",
        last_reviewed="2025-11-01",
        attribution_status="approved",
        permission_doc="https://example.com/perm/acme.pdf",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert result.errors == []
    assert len(result.assets) == 1
    assert result.assets[0]["kind"] == "customer-quote"


# -- hide / expire behaviors -----------------------------------------------


def test_expired_battle_card_is_hidden_and_counted(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="battle-cards/old.md",
        title="Old battle card",
        kind="battle-card",
        owner="ricardo-cataldi",
        last_reviewed="2025-05-01",  # > 90 days
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert result.errors == []
    assert result.expired_count == 1
    assert result.assets == []


def test_pending_quote_is_hidden_and_counted(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="quotes/pending.md",
        title="Pending quote",
        kind="customer-quote",
        owner="ricardo-cataldi",
        last_reviewed="2025-11-01",
        attribution_status="pending",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert result.errors == []
    assert result.hidden_quote_count == 1
    assert result.assets == []


def test_unknown_quote_is_hidden(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="quotes/unknown.md",
        title="Unknown quote",
        kind="customer-quote",
        owner="ricardo-cataldi",
        last_reviewed="2025-11-01",
        attribution_status="unknown",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert result.errors == []
    assert result.hidden_quote_count == 1
    assert result.assets == []


# -- validation errors ------------------------------------------------------


def test_missing_required_field_produces_error(tmp_path: Path) -> None:
    target = tmp_path / "battle-cards/missing.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\n" 'title: "Missing fields"\n' "kind: battle-card\n"
        # owner + last_reviewed deliberately missing
        "---\n" "body\n",
        encoding="utf-8",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    fields = {e.field for e in result.errors}
    assert "owner" in fields and "last_reviewed" in fields
    assert result.assets == []


def test_invalid_kind_produces_error(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="battle-cards/bad.md",
        title="Bad",
        kind="not-a-kind",
        owner="ricardo-cataldi",
        last_reviewed="2025-11-01",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert any(e.field == "kind" for e in result.errors)


def test_invalid_iso_date_produces_error(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="battle-cards/bad-date.md",
        title="Bad date",
        kind="battle-card",
        owner="ricardo-cataldi",
        last_reviewed="not-a-date",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert any(e.field == "last_reviewed" for e in result.errors)


def test_unknown_field_is_rejected(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="battle-cards/extra.md",
        title="Extra field",
        kind="battle-card",
        owner="ricardo-cataldi",
        last_reviewed="2025-11-01",
        extra_field="boom",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert any(e.field == "extra_unknown_field" for e in result.errors)


def test_invalid_owner_handle_is_rejected(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="battle-cards/bad-owner.md",
        title="Bad owner",
        kind="battle-card",
        owner="-leading-dash",
        last_reviewed="2025-11-01",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert any(e.field == "owner" for e in result.errors)


def test_quote_without_attribution_is_error(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="quotes/no-attribution.md",
        title="No attribution",
        kind="customer-quote",
        owner="ricardo-cataldi",
        last_reviewed="2025-11-01",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert any(e.field == "attribution_status" for e in result.errors)


def test_approved_quote_without_permission_doc_is_error(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="quotes/approved-no-doc.md",
        title="Approved no doc",
        kind="customer-quote",
        owner="ricardo-cataldi",
        last_reviewed="2025-11-01",
        attribution_status="approved",
        # permission_doc deliberately missing
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert any(e.field == "permission_doc" for e in result.errors)


def test_missing_front_matter_is_error(tmp_path: Path) -> None:
    target = tmp_path / "battle-cards/no-fm.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("Just a body, no front-matter.\n", encoding="utf-8")
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert any(e.field == "<front-matter>" for e in result.errors)


def test_files_outside_kind_dirs_are_ignored(tmp_path: Path) -> None:
    """README.md, digest indexes, and stray notes must not fail validation."""

    # Top-level README without front-matter.
    (tmp_path / "README.md").write_text("# index\n", encoding="utf-8")
    # README inside a kind dir is also ignored.
    (tmp_path / "battle-cards").mkdir()
    (tmp_path / "battle-cards" / "README.md").write_text("# section\n", encoding="utf-8")
    # Stray note in a non-kind subdirectory.
    (tmp_path / "drafts").mkdir()
    (tmp_path / "drafts" / "random.md").write_text("draft body\n", encoding="utf-8")

    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    assert result.errors == []
    assert result.assets == []


# -- sort order + render ---------------------------------------------------


def test_assets_sort_soonest_to_expire_first(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="battle-cards/soon.md",
        title="Soon",
        kind="battle-card",
        owner="ricardo-cataldi",
        last_reviewed="2025-09-01",  # 90 - 64 = 26 days left
    )
    _write_asset(
        tmp_path,
        relpath="battle-cards/later.md",
        title="Later",
        kind="battle-card",
        owner="ricardo-cataldi",
        last_reviewed="2025-10-15",  # 90 - 20 = 70 days left
    )
    _write_asset(
        tmp_path,
        relpath="win-loss/immutable.md",
        title="Immutable",
        kind="win-loss",
        owner="ricardo-cataldi",
        last_reviewed="2025-01-01",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    titles = [a["title"] for a in result.assets]
    assert titles == ["Soon", "Later", "Immutable"]


def test_render_index_shape(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="battle-cards/ok.md",
        title="OK",
        kind="battle-card",
        owner="ricardo-cataldi",
        last_reviewed="2025-11-01",
    )
    result = beim.build_index(tmp_path, today=date(2025, 11, 4))
    payload = beim.render_index(result)
    assert payload["schemaVersion"] == 1
    assert payload["expiredCount"] == 0
    assert payload["hiddenQuoteCount"] == 0
    assert "generatedAt" in payload
    assert isinstance(payload["assets"], list)
    # Round-trip JSON-clean.
    roundtrip = json.loads(json.dumps(payload))
    assert roundtrip == payload


# -- CLI entry point --------------------------------------------------------


def test_cli_check_succeeds_on_empty_dir(tmp_path: Path) -> None:
    rc = beim.main(["--source", str(tmp_path), "--check"])
    assert rc == 0


def test_cli_check_fails_on_validation_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    target = tmp_path / "battle-cards" / "bad.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("---\nkind: battle-card\n---\nbody\n", encoding="utf-8")
    rc = beim.main(["--source", str(tmp_path), "--check"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "validation error" in err


def test_cli_writes_index_file(tmp_path: Path) -> None:
    _write_asset(
        tmp_path,
        relpath="battle-cards/ok.md",
        title="OK",
        kind="battle-card",
        owner="ricardo-cataldi",
        last_reviewed=date.today().isoformat(),
    )
    output = tmp_path / "index.json"
    rc = beim.main(["--source", str(tmp_path), "--output", str(output)])
    assert rc == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == 1
    assert len(payload["assets"]) == 1
