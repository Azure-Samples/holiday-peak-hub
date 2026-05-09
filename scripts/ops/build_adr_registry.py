"""
Build an ADR (Architecture Decision Record) registry for the `/builders/adrs`
UI page. Issue #1048 / Epic #1053.

Inputs : `docs/architecture/adrs/adr-*.md`
Output : `apps/ui/public/adrs/registry.json`

Front-matter contract
=====================
The current ADR template uses **bold-key** fields rather than YAML front-matter.
Recognized fields (case-insensitive on the key, value taken to end of line):

    **Status**: Accepted | Proposed | Superseded | Deprecated | ...
    **Date**: 2025-11-04
    **Tags**: tag-a, tag-b, ...
    **Deciders**: Name1, Name2

The ADR title comes from the first H1 (`# ADR-NNN: Title`).
The ADR number comes from the filename (`adr-035-ui-design-system.md` → 35).

Strict mode
===========
- Default (`--strict` NOT set):
  * Parse errors are LOGGED but do not exit non-zero.
  * Output JSON has `stale: true` and a `parse_errors` list.
  * Empty input directory produces an empty-but-valid registry.

- `--strict`:
  * Any parse error or missing required field exits 1.
  * Output JSON has `stale: false`.

This honors Epic #1053's "default produces empty-but-valid JSON with stale
banner so a malformed ADR doesn't block the SWA build" rule.

Usage
=====
    python scripts/ops/build_adr_registry.py
    python scripts/ops/build_adr_registry.py --strict
    python scripts/ops/build_adr_registry.py --source docs/architecture/adrs --output apps/ui/public/adrs/registry.json
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Iterable

ADR_FILE_RE = re.compile(r"^adr-(\d+)-(.+)\.md$", re.IGNORECASE)
H1_RE = re.compile(r"^#\s+(?:ADR-\d+:?\s*)?(?P<title>.+?)\s*$")
BOLD_KEY_RE = re.compile(
    r"^\*\*(?P<key>Status|Date|Tags|Deciders|References)\*\*\s*[:：]\s*(?P<value>.+?)\s*$",
    re.IGNORECASE,
)


@dataclasses.dataclass
class AdrEntry:
    number: int
    slug: str
    title: str
    status: str
    date: str
    tags: list[str]
    deciders: list[str]
    source_path: str

    def to_json(self) -> dict[str, object]:
        return {
            "number": self.number,
            "slug": self.slug,
            "title": self.title,
            "status": self.status,
            "date": self.date,
            "tags": self.tags,
            "deciders": self.deciders,
            "source_path": self.source_path,
        }


def parse_adr(path: Path) -> tuple[AdrEntry | None, list[str]]:
    """Parse a single ADR file. Return (entry, errors)."""
    errors: list[str] = []
    match = ADR_FILE_RE.match(path.name)
    if not match:
        errors.append(f"{path.name}: filename does not match adr-NNN-*.md")
        return None, errors

    number = int(match.group(1))
    slug = match.group(2).lower()

    title: str | None = None
    status: str | None = None
    date: str | None = None
    tags: list[str] = []
    deciders: list[str] = []

    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if title is None:
            m = H1_RE.match(line)
            if m:
                title = m.group("title").strip()
                continue
        m = BOLD_KEY_RE.match(line)
        if m:
            key = m.group("key").lower()
            value = m.group("value").strip()
            if key == "status":
                status = value.split(" ")[0].rstrip(".,;:")
            elif key == "date":
                date = value
            elif key == "tags":
                tags = [t.strip() for t in value.split(",") if t.strip()]
            elif key == "deciders":
                deciders = [d.strip() for d in value.split(",") if d.strip()]

    if title is None:
        errors.append(f"{path.name}: missing H1 title")
        title = f"ADR-{number:03d}"
    if status is None:
        errors.append(f"{path.name}: missing **Status**")
        status = "unknown"
    if date is None:
        errors.append(f"{path.name}: missing **Date**")
        date = "unknown"

    entry = AdrEntry(
        number=number,
        slug=slug,
        title=title,
        status=status,
        date=date,
        tags=tags,
        deciders=deciders,
        source_path=str(path).replace("\\", "/"),
    )
    return entry, errors


def build_registry(
    source_dir: Path,
    strict: bool,
) -> tuple[dict[str, object], list[str], int]:
    """Return (registry, parse_errors, exit_code)."""
    parse_errors: list[str] = []
    entries: list[AdrEntry] = []

    if not source_dir.exists():
        msg = f"source directory not found: {source_dir}"
        parse_errors.append(msg)
        if strict:
            return _build_payload([], parse_errors, stale=True, source_dir=source_dir), parse_errors, 1
        return _build_payload([], parse_errors, stale=True, source_dir=source_dir), parse_errors, 0

    for path in sorted(source_dir.glob("adr-*.md")):
        entry, errors = parse_adr(path)
        if errors:
            parse_errors.extend(errors)
        if entry is not None:
            entries.append(entry)

    stale = bool(parse_errors)
    if strict and parse_errors:
        return _build_payload(entries, parse_errors, stale=False, source_dir=source_dir), parse_errors, 1

    return _build_payload(entries, parse_errors, stale=stale, source_dir=source_dir), parse_errors, 0


def _build_payload(
    entries: Iterable[AdrEntry],
    parse_errors: list[str],
    *,
    stale: bool,
    source_dir: Path,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source_dir": str(source_dir).replace("\\", "/"),
        "stale": stale,
        "parse_errors": parse_errors,
        "adrs": [e.to_json() for e in entries],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the ADR registry JSON.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("docs/architecture/adrs"),
        help="ADR source directory (default: docs/architecture/adrs).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("apps/ui/public/adrs/registry.json"),
        help="Output JSON path (default: apps/ui/public/adrs/registry.json).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on parse errors; default mode emits empty-but-valid JSON.",
    )
    args = parser.parse_args(argv)

    registry, parse_errors, exit_code = build_registry(args.source, args.strict)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    n_adrs = len(registry["adrs"])  # type: ignore[arg-type]
    print(
        f"build_adr_registry: wrote {n_adrs} ADR(s) to {args.output} "
        f"(stale={registry['stale']}, errors={len(parse_errors)})"
    )
    if parse_errors and not args.strict:
        for e in parse_errors:
            print(f"  warn: {e}", file=sys.stderr)
    elif parse_errors and args.strict:
        for e in parse_errors:
            print(f"  error: {e}", file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
