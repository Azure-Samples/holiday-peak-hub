"""
Build an architecture-diagram registry for the `/builders/architecture` UI
page. Issue #1047 / Epic #1053.

Inputs : `docs/architecture/*.md` (top-level only at v1)
Output : `apps/ui/public/architecture/registry.json`
Side effect: copies extracted Mermaid sources to
             `apps/ui/public/architecture/<slug>-<idx>.mmd`

Strategy
========
- Walk `docs/architecture/*.md` (NOT including `adrs/`, `patterns/`, etc.).
- For each file, scan for ```` ```mermaid ```` fenced code blocks.
- For each block, write a sidecar `.mmd` file under
  `apps/ui/public/architecture/` so the UI can offer a download.
- Emit `registry.json` with one entry per (document, block) pair containing:
    {slug, doc_title, block_index, mermaid_path, source_doc, mermaid_live_url}
  `mermaid_live_url` is a deterministic deep link to the Mermaid Live Editor
  with the raw source pre-loaded (base64-encoded JSON payload).

Like build_adr_registry.py:
- Default mode: empty-but-valid output on missing inputs / parse errors,
  with `stale: true` banner.
- `--strict`: fail on any error.

Usage
=====
    python scripts/ops/build_architecture_registry.py
    python scripts/ops/build_architecture_registry.py --strict
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import re
import sys
from pathlib import Path

H1_RE = re.compile(r"^#\s+(?P<title>.+?)\s*$")
MERMAID_FENCE_RE = re.compile(
    r"^```mermaid\s*$(?P<body>.*?)^```\s*$",
    re.MULTILINE | re.DOTALL,
)


def slugify(name: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return out or "diagram"


def mermaid_live_url(source: str) -> str:
    """Deterministic deep link to the Mermaid Live Editor."""
    payload = {"code": source, "mermaid": {"theme": "default"}}
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    encoded = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
    return f"https://mermaid.live/edit#base64:{encoded}"


def parse_doc(path: Path) -> tuple[str, list[str]]:
    """Return (doc_title, [mermaid_blocks])."""
    text = path.read_text(encoding="utf-8")
    title = path.stem.replace("-", " ").title()
    for line in text.splitlines():
        m = H1_RE.match(line)
        if m:
            title = m.group("title").strip()
            break
    blocks = [m.group("body").strip("\n") for m in MERMAID_FENCE_RE.finditer(text)]
    return title, blocks


def build(
    source_dir: Path,
    public_dir: Path,
    output: Path,
    strict: bool,
) -> int:
    parse_errors: list[str] = []
    entries: list[dict[str, object]] = []

    if public_dir.exists():
        # Wipe stale .mmd sidecars only (registry.json overwritten below).
        for old in public_dir.glob("*.mmd"):
            try:
                old.unlink()
            except OSError as exc:
                parse_errors.append(f"failed to remove stale sidecar {old}: {exc}")
    public_dir.mkdir(parents=True, exist_ok=True)

    if not source_dir.exists():
        parse_errors.append(f"source directory not found: {source_dir}")
    else:
        for doc in sorted(source_dir.glob("*.md")):
            try:
                title, blocks = parse_doc(doc)
            except OSError as exc:
                parse_errors.append(f"{doc.name}: {exc}")
                continue
            for idx, src in enumerate(blocks):
                slug = f"{slugify(doc.stem)}-{idx + 1}"
                sidecar = public_dir / f"{slug}.mmd"
                try:
                    sidecar.write_text(src + "\n", encoding="utf-8")
                except OSError as exc:
                    parse_errors.append(f"{doc.name}: failed to write {sidecar}: {exc}")
                    continue
                entries.append(
                    {
                        "slug": slug,
                        "doc_title": title,
                        "doc_filename": doc.name,
                        "block_index": idx + 1,
                        "mermaid_path": f"/architecture/{slug}.mmd",
                        "source_doc": str(doc).replace("\\", "/"),
                        "mermaid_live_url": mermaid_live_url(src),
                    }
                )

    stale = bool(parse_errors)
    payload = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "source_dir": str(source_dir).replace("\\", "/"),
        "stale": stale,
        "parse_errors": parse_errors,
        "diagrams": entries,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    n = len(entries)
    print(
        f"build_architecture_registry: wrote {n} diagram(s) to {output} "
        f"(stale={stale}, errors={len(parse_errors)})"
    )
    if parse_errors and not strict:
        for e in parse_errors:
            print(f"  warn: {e}", file=sys.stderr)
    elif parse_errors and strict:
        for e in parse_errors:
            print(f"  error: {e}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the architecture diagram registry.")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("docs/architecture"),
        help="Source documentation directory (default: docs/architecture).",
    )
    parser.add_argument(
        "--public-dir",
        type=Path,
        default=Path("apps/ui/public/architecture"),
        help="Public dir to copy .mmd sidecars into.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("apps/ui/public/architecture/registry.json"),
        help="Output JSON path.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on parse errors.",
    )
    args = parser.parse_args(argv)
    return build(args.source, args.public_dir, args.output, args.strict)


if __name__ == "__main__":
    sys.exit(main())
