"""Build the enablement asset index consumed by the UI.

This script enforces the front-matter contract documented in
``docs/governance/enablement-asset-contract.md`` for every Markdown file under
the configured curated source path (default: ``docs/enablement``). It emits
``apps/ui/public/enablement-index.json`` with the shape expected by the UI.

It is the **single source of truth** for the schema:

* Required fields ÔÇö ``title``, ``kind``, ``owner``, ``last_reviewed``.
* Conditional fields ÔÇö ``attribution_status`` (when ``kind == customer-quote``)
  and ``permission_doc`` (when ``attribution_status == approved``).
* Closed schema ÔÇö unknown front-matter keys are rejected.

Running without ``--check`` writes the index file. Running with ``--check`` only
validates and exits non-zero on any violation; this is the CI mode.

Exit codes
----------
* ``0`` ÔÇö all assets valid; index written (or check passed).
* ``1`` ÔÇö at least one validation error.

Usage
-----
::

    python scripts/ops/build_enablement_index.py
    python scripts/ops/build_enablement_index.py --check
    python scripts/ops/build_enablement_index.py --source docs/enablement \\
        --output apps/ui/public/enablement-index.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SOURCE_DIR = REPO_ROOT / "docs" / "enablement"
DEFAULT_OUTPUT_PATH = REPO_ROOT / "apps" / "ui" / "public" / "enablement-index.json"

REPO_BLOB_BASE = "https://github.com/Azure-Samples/holiday-peak-hub/blob/main"

SCHEMA_VERSION = 1

KIND_VALUES = frozenset({"battle-card", "demo-script", "win-loss", "customer-quote"})
ATTRIBUTION_VALUES = frozenset({"approved", "pending", "unknown"})

EXPIRY_DAYS: dict[str, int | None] = {
    "battle-card": 90,
    "demo-script": 180,
    "win-loss": None,
    "customer-quote": None,
}

REQUIRED_BASE_FIELDS = ("title", "kind", "owner", "last_reviewed")
ALLOWED_FIELDS = frozenset({*REQUIRED_BASE_FIELDS, "attribution_status", "permission_doc"})

# Subdirectories whose Markdown files MUST carry the contract. Everything
# outside these (README, digest indexes, work-in-progress notes) is ignored
# by the validator and the index.
KIND_DIRS: tuple[str, ...] = (
    "battle-cards",
    "demos",
    "win-loss",
    "quotes",
)

# GitHub handle: 1ÔÇô39 chars, alnum + dash, no leading/trailing dash.
GITHUB_HANDLE_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}[A-Za-z0-9])?$")

FRONT_MATTER_RE = re.compile(r"^---\r?\n(?P<body>.*?)\r?\n---", re.DOTALL)


@dataclass(frozen=True)
class ValidationError:
    """A single front-matter or schema violation."""

    file: str
    field: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"file": self.file, "field": self.field, "message": self.message}


@dataclass
class BuildResult:
    """Outcome of an index build pass."""

    assets: list[dict[str, object]] = field(default_factory=list)
    expired_count: int = 0
    hidden_quote_count: int = 0
    errors: list[ValidationError] = field(default_factory=list)


def _parse_front_matter(text: str) -> dict[str, str] | None:
    """Parse the YAML-ish front-matter block at the top of *text*.

    The contract is intentionally tiny: only flat ``key: value`` pairs are
    supported. Authors who reach for nested structures should split into
    multiple files instead.
    """

    match = FRONT_MATTER_RE.match(text)
    if match is None:
        return None
    body = match.group("body")
    out: dict[str, str] = {}
    for line in body.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        idx = line.find(":")
        if idx == -1:
            continue
        key = line[:idx].strip()
        value = line[idx + 1 :].strip()
        # Strip wrapping double quotes.
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            value = value[1:-1]
        out[key] = value
    return out


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _validate_front_matter(fm: dict[str, str], rel_path: str) -> list[ValidationError]:
    errors: list[ValidationError] = []

    # Closed schema: reject unknown keys.
    for key in fm:
        if key not in ALLOWED_FIELDS:
            errors.append(
                ValidationError(
                    file=rel_path,
                    field=key,
                    message=f"unknown front-matter field '{key}' (closed schema)",
                )
            )

    # Required base fields.
    for required in REQUIRED_BASE_FIELDS:
        if not fm.get(required):
            errors.append(
                ValidationError(
                    file=rel_path,
                    field=required,
                    message=f"missing required field '{required}'",
                )
            )

    kind = fm.get("kind", "")
    if kind and kind not in KIND_VALUES:
        errors.append(
            ValidationError(
                file=rel_path,
                field="kind",
                message=(f"invalid kind '{kind}'; " f"must be one of {sorted(KIND_VALUES)}"),
            )
        )

    last_reviewed = fm.get("last_reviewed", "")
    if last_reviewed and _parse_iso_date(last_reviewed) is None:
        errors.append(
            ValidationError(
                file=rel_path,
                field="last_reviewed",
                message=(f"'{last_reviewed}' is not an ISO date (YYYY-MM-DD)"),
            )
        )

    owner = fm.get("owner", "")
    if owner and not GITHUB_HANDLE_RE.match(owner):
        errors.append(
            ValidationError(
                file=rel_path,
                field="owner",
                message=(
                    f"'{owner}' is not a valid GitHub handle "
                    "(alnum + dash, 1ÔÇô39 chars, no leading/trailing dash)"
                ),
            )
        )

    if kind == "customer-quote":
        attribution = fm.get("attribution_status", "")
        if not attribution:
            errors.append(
                ValidationError(
                    file=rel_path,
                    field="attribution_status",
                    message=(
                        "customer-quote requires 'attribution_status' "
                        "(approved | pending | unknown)"
                    ),
                )
            )
        elif attribution not in ATTRIBUTION_VALUES:
            errors.append(
                ValidationError(
                    file=rel_path,
                    field="attribution_status",
                    message=(
                        f"invalid attribution_status '{attribution}'; "
                        f"must be one of {sorted(ATTRIBUTION_VALUES)}"
                    ),
                )
            )
        elif attribution == "approved" and not fm.get("permission_doc"):
            errors.append(
                ValidationError(
                    file=rel_path,
                    field="permission_doc",
                    message=(
                        "approved customer-quote requires 'permission_doc' "
                        "(link to permission record)"
                    ),
                )
            )

    return errors


def _days_to_expiry(kind: str, reviewed_at: date, today: date) -> float:
    expiry = EXPIRY_DAYS.get(kind)
    if expiry is None:
        return float("inf")
    age_days = (today - reviewed_at).days
    return float(expiry - age_days)


def _iter_markdown(source_dir: Path) -> Iterable[Path]:
    """Yield every contract-bearing Markdown file under *source_dir*.

    Only files inside one of :data:`KIND_DIRS` are returned; READMEs,
    digest indexes, and stray notes at the top of the tree are ignored.
    """

    if not source_dir.exists():
        return ()
    out: list[Path] = []
    for kind_dir in KIND_DIRS:
        sub = source_dir / kind_dir
        if not sub.exists():
            continue
        for path in sub.rglob("*.md"):
            if path.is_file() and path.name.lower() != "readme.md":
                out.append(path)
    return sorted(out)


def _slug_from_path(path: Path) -> str:
    return path.stem


def _safe_relative(path: Path, base: Path) -> str:
    """Return *path* relative to *base*, or relative to *path* parent on failure.

    Used to build a human-friendly href and rel_path for assets that may live
    outside the repository root (e.g., during unit tests against ``tmp_path``).
    """

    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.name


def _href_for(path: Path, base: Path) -> str:
    rel = _safe_relative(path, base)
    return f"{REPO_BLOB_BASE}/{rel}"


def build_index(
    source_dir: Path = DEFAULT_SOURCE_DIR,
    today: date | None = None,
    repo_root: Path = REPO_ROOT,
) -> BuildResult:
    """Build the enablement index from *source_dir*.

    Returns a :class:`BuildResult` regardless of validation state; callers are
    responsible for inspecting ``errors`` and deciding whether to write the
    index or fail the build.

    *repo_root* anchors relative paths used in error messages and ``href``
    fields. It defaults to the repository root; tests may pass an alternative
    base when working under ``tmp_path``.
    """

    today = today or date.today()
    result = BuildResult()

    for md_path in _iter_markdown(source_dir):
        rel_path = _safe_relative(md_path, repo_root)
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError as exc:
            result.errors.append(
                ValidationError(
                    file=rel_path,
                    field="<file>",
                    message=f"cannot read file: {exc}",
                )
            )
            continue

        fm = _parse_front_matter(text)
        if fm is None:
            result.errors.append(
                ValidationError(
                    file=rel_path,
                    field="<front-matter>",
                    message="missing YAML front-matter block",
                )
            )
            continue

        errors = _validate_front_matter(fm, rel_path)
        if errors:
            result.errors.extend(errors)
            continue  # do not surface invalid assets

        kind = fm["kind"]
        reviewed_at = _parse_iso_date(fm["last_reviewed"])
        if reviewed_at is None:
            # Defensive; _validate_front_matter would have flagged it.
            continue
        days_to_expiry = _days_to_expiry(kind, reviewed_at, today)

        if kind == "customer-quote" and fm.get("attribution_status") != "approved":
            result.hidden_quote_count += 1
            continue

        if days_to_expiry < 0:
            result.expired_count += 1
            continue

        result.assets.append(
            {
                "slug": _slug_from_path(md_path),
                "title": fm["title"],
                "kind": kind,
                "owner": fm["owner"],
                "lastReviewed": fm["last_reviewed"],
                "daysToExpiry": (None if days_to_expiry == float("inf") else int(days_to_expiry)),
                "href": _href_for(md_path, repo_root),
            }
        )

    # Stable sort: soonest-to-expire first; immutable assets at the bottom by
    # title.
    def _sort_key(asset: dict[str, object]) -> tuple[int, int | str, str]:
        days = asset["daysToExpiry"]
        if days is None:
            return (1, asset["title"], asset["slug"])
        return (0, int(days), asset["slug"])

    result.assets.sort(key=_sort_key)
    return result


def render_index(result: BuildResult, generated_at: datetime | None = None) -> dict:
    generated_at = generated_at or datetime.now(timezone.utc)
    return {
        "generatedAt": generated_at.isoformat(),
        "schemaVersion": SCHEMA_VERSION,
        "expiredCount": result.expired_count,
        "hiddenQuoteCount": result.hidden_quote_count,
        "assets": result.assets,
    }


def _print_errors(errors: list[ValidationError]) -> None:
    print(f"enablement-index: {len(errors)} validation error(s):", file=sys.stderr)
    for err in errors:
        print(f"  - {err.file} [{err.field}] {err.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE_DIR,
        help="curated source directory containing enablement Markdown files",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="path to write the enablement-index.json artifact",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate only; do not write the index file",
    )
    args = parser.parse_args(argv)

    result = build_index(source_dir=args.source)

    if result.errors:
        _print_errors(result.errors)
        return 1
    if args.check:
        print(
            f"enablement-index: OK ({len(result.assets)} live, "
            f"{result.expired_count} expired, "
            f"{result.hidden_quote_count} quotes hidden)",
            file=sys.stderr,
        )
        return 0

    payload = render_index(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"enablement-index: wrote {args.output} "
        f"({len(result.assets)} live, "
        f"{result.expired_count} expired, "
        f"{result.hidden_quote_count} quotes hidden)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
