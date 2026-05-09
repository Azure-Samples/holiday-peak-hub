"""Unit tests for ``scripts/ops/build_winloss_digest.py`` (Issue #1052)."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ops" / "build_winloss_digest.py"

# Register in sys.modules before exec so Python 3.13's dataclass machinery
# can introspect the module namespace.
_MODULE_NAME = "build_winloss_digest_under_test"
spec = importlib.util.spec_from_file_location(_MODULE_NAME, SCRIPT_PATH)
assert spec and spec.loader, "build_winloss_digest.py must be importable"
bwd = importlib.util.module_from_spec(spec)
sys.modules[_MODULE_NAME] = bwd
spec.loader.exec_module(bwd)


def _write_winloss(
    tmp_path: Path,
    *,
    relpath: str,
    title: str,
    last_reviewed: str,
    owner: str = "ricardo-cataldi",
    body: str = "Result: WIN. Reason: agentic catalog beat the incumbent on time-to-value.",
) -> Path:
    target = tmp_path / relpath
    target.parent.mkdir(parents=True, exist_ok=True)
    fm = (
        "---\n"
        f'title: "{title}"\n'
        "kind: win-loss\n"
        f"owner: {owner}\n"
        f"last_reviewed: {last_reviewed}\n"
        "---\n\n"
        f"{body}\n"
    )
    target.write_text(fm, encoding="utf-8")
    return target


# -- _quarter_bounds + _quarter_for ----------------------------------------


@pytest.mark.parametrize(
    "label,expected",
    [
        ("2025-Q1", (date(2025, 1, 1), date(2025, 3, 31))),
        ("2025-Q2", (date(2025, 4, 1), date(2025, 6, 30))),
        ("2025-Q3", (date(2025, 7, 1), date(2025, 9, 30))),
        ("2025-Q4", (date(2025, 10, 1), date(2025, 12, 31))),
        ("2024-Q1", (date(2024, 1, 1), date(2024, 3, 31))),
    ],
)
def test_quarter_bounds_known(label: str, expected: tuple[date, date]) -> None:
    assert bwd._quarter_bounds(label) == expected


@pytest.mark.parametrize("bad", ["2025", "2025-Q5", "2025Q1", "Q1", "abc"])
def test_quarter_bounds_invalid_raises(bad: str) -> None:
    with pytest.raises(ValueError):
        bwd._quarter_bounds(bad)


@pytest.mark.parametrize(
    "today,expected",
    [
        (date(2025, 1, 15), "2025-Q1"),
        (date(2025, 4, 1), "2025-Q2"),
        (date(2025, 7, 31), "2025-Q3"),
        (date(2025, 12, 31), "2025-Q4"),
    ],
)
def test_quarter_for_today(today: date, expected: str) -> None:
    assert bwd._quarter_for(today) == expected


# -- collect_entries + render_digest ---------------------------------------


def test_collect_only_winloss_in_quarter(tmp_path: Path) -> None:
    _write_winloss(
        tmp_path,
        relpath="win-loss/in-q4.md",
        title="In quarter",
        last_reviewed="2025-10-15",
    )
    _write_winloss(
        tmp_path,
        relpath="win-loss/in-q3.md",
        title="Last quarter",
        last_reviewed="2025-08-01",
    )
    # Non-winloss is ignored.
    bcard = tmp_path / "battle-cards/x.md"
    bcard.parent.mkdir(parents=True, exist_ok=True)
    bcard.write_text(
        "---\n"
        'title: "BC"\n'
        "kind: battle-card\n"
        "owner: ricardo-cataldi\n"
        "last_reviewed: 2025-10-30\n"
        "---\n",
        encoding="utf-8",
    )

    bounds = bwd._quarter_bounds("2025-Q4")
    entries, errors = bwd.collect_entries(tmp_path, bounds)
    assert errors == []
    titles = [e.title for e in entries]
    assert titles == ["In quarter"]


def test_render_digest_with_entries(tmp_path: Path) -> None:
    _write_winloss(
        tmp_path,
        relpath="win-loss/october.md",
        title="October win",
        last_reviewed="2025-10-10",
    )
    _write_winloss(
        tmp_path,
        relpath="win-loss/november.md",
        title="November win",
        last_reviewed="2025-11-01",
        body="Result: WIN. Replaced legacy Algolia stack.",
    )
    bounds = bwd._quarter_bounds("2025-Q4")
    entries, errors = bwd.collect_entries(tmp_path, bounds)
    assert errors == []
    digest = bwd.render_digest("2025-Q4", entries)
    assert "# Win/Loss digest" in digest
    assert "2 entries this quarter" in digest
    assert "October win" in digest
    assert "November win" in digest
    # Sorted oldest-first by last_reviewed.
    assert digest.index("October win") < digest.index("November win")
    assert "Result: WIN" in digest


def test_render_digest_empty_quarter(tmp_path: Path) -> None:
    bounds = bwd._quarter_bounds("2025-Q4")
    entries, errors = bwd.collect_entries(tmp_path, bounds)
    assert entries == []
    digest = bwd.render_digest("2025-Q4", entries)
    assert "No win/loss entries authored in 2025-Q4" in digest


def test_invalid_winloss_propagates_error(tmp_path: Path) -> None:
    target = tmp_path / "win-loss/broken.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\n" 'title: "Broken"\n' "kind: win-loss\n"
        # owner missing
        "last_reviewed: 2025-10-15\n" "---\n",
        encoding="utf-8",
    )
    bounds = bwd._quarter_bounds("2025-Q4")
    entries, errors = bwd.collect_entries(tmp_path, bounds)
    assert entries == []
    assert any("owner" in err for err in errors)


def test_strip_front_matter_returns_body() -> None:
    text = '---\ntitle: "x"\nkind: win-loss\n---\n\nBody line 1\nBody line 2\n'
    assert bwd._strip_front_matter(text) == "Body line 1\nBody line 2"


# -- CLI -------------------------------------------------------------------


def test_cli_check_succeeds_for_valid_quarter(tmp_path: Path) -> None:
    _write_winloss(
        tmp_path,
        relpath="win-loss/q4.md",
        title="Q4",
        last_reviewed="2025-10-15",
    )
    rc = bwd.main(
        [
            "--source",
            str(tmp_path),
            "--quarter",
            "2025-Q4",
            "--check",
        ]
    )
    assert rc == 0


def test_cli_fails_on_invalid_quarter(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    rc = bwd.main(["--source", str(tmp_path), "--quarter", "2025-Q9", "--check"])
    assert rc == 1
    assert "invalid quarter" in capsys.readouterr().err


def test_cli_writes_digest_file(tmp_path: Path) -> None:
    _write_winloss(
        tmp_path,
        relpath="win-loss/q4.md",
        title="Q4 win",
        last_reviewed="2025-10-15",
    )
    out_root = tmp_path / "digest"
    rc = bwd.main(
        [
            "--source",
            str(tmp_path),
            "--quarter",
            "2025-Q4",
            "--output-root",
            str(out_root),
        ]
    )
    assert rc == 0
    target = out_root / "2025-Q4" / "index.md"
    assert target.exists()
    content = target.read_text(encoding="utf-8")
    assert "Q4 win" in content
