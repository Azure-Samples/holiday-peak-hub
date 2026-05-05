#!/usr/bin/env python3
"""Validate internal markdown links for selected documentation roots."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

_LINK_PATTERN = re.compile(r"(?<!\!)\[[^\]]+\]\(([^)]+)\)")


def _is_external(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme in {"http", "https", "mailto", "tel"}


def _normalize_target(raw_target: str) -> str:
    target = raw_target.strip()
    if not target:
        return ""
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1].strip()
    return unquote(target)


def _iter_markdown_files(roots: list[Path]) -> list[Path]:
    markdown_files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix.lower() == ".md":
            markdown_files.append(root)
            continue
        if root.is_dir():
            markdown_files.extend(sorted(root.rglob("*.md")))
    return markdown_files


def _resolve_target(current_file: Path, target: str) -> Path:
    cleaned_target = target.split("#", 1)[0].split("?", 1)[0].strip()
    if cleaned_target.startswith("/"):
        return Path(cleaned_target.lstrip("/"))
    return (current_file.parent / cleaned_target).resolve()


def validate_links(roots: list[Path], repo_root: Path) -> list[str]:
    errors: list[str] = []
    markdown_files = _iter_markdown_files(roots)

    for markdown_file in markdown_files:
        text = markdown_file.read_text(encoding="utf-8")
        relative_file = markdown_file.resolve().relative_to(repo_root)

        for line_number, line in enumerate(text.splitlines(), start=1):
            for match in _LINK_PATTERN.finditer(line):
                raw_target = _normalize_target(match.group(1))
                if not raw_target or raw_target.startswith("#") or _is_external(raw_target):
                    continue

                resolved_path = _resolve_target(markdown_file.resolve(), raw_target)
                if not resolved_path.is_absolute():
                    resolved_path = (repo_root / resolved_path).resolve()

                if resolved_path.exists():
                    continue

                display_target = raw_target.replace("`", "")
                errors.append(
                    f"{relative_file}:{line_number} unresolved link target '{display_target}'"
                )

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate internal markdown link targets under given roots."
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        required=True,
        help="Workspace-relative paths to markdown files/directories.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd().resolve()
    roots = [(repo_root / item).resolve() for item in args.roots]

    missing_roots = [root for root in roots if not root.exists()]
    if missing_roots:
        for missing in missing_roots:
            print(f"Missing root: {missing.relative_to(repo_root)}")
        return 2

    errors = validate_links(roots, repo_root)
    if errors:
        print("Markdown link validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Markdown link validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
