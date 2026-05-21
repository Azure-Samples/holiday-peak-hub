#!/usr/bin/env python3
"""Update a Flux HelmRelease's top-level ``spec.values.image`` block in place.

The HelmRelease files under ``.kubernetes/releases/{agents,crud}`` are the
Flux source of truth that the helm-controller reconciles. After each
successful deploy of the dev cluster, the CI workflow opens a PR using
this script to bump ``image.repository`` and ``image.tag`` to point at the
freshly built and tested artifact in ACR. Pinning by tag (rather than
digest) keeps the diff readable; digest pinning can be layered on later
without changing this script's CLI contract.

This script intentionally performs a *surgical* edit — line by line — to
avoid reflowing the YAML, dropping comments, or reordering keys (any of
which a YAML round-trip via PyYAML/ruamel would do unless carefully
configured). The chart only honours the *first* ``image:`` block at four-
space indent (the top-level ``spec.values.image``), so scanning until the
first match suffices.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_IMAGE_BLOCK_RE = re.compile(r"^    image:\s*$")
_REPO_RE = re.compile(r"^(\s+)repository:\s+\S+\s*$")
_TAG_RE = re.compile(r"^(\s+)tag:\s+\S+\s*$")
_SIBLING_RE = re.compile(r"^    \S")


def update_helmrelease(path: Path, repository: str, tag: str) -> bool:
    """Edit ``path`` to set ``image.repository`` and ``image.tag``.

    Returns ``True`` when the file content changed, ``False`` otherwise.
    Raises ``ValueError`` when the expected image block is missing.
    """
    original = path.read_text(encoding="utf-8")
    # Preserve line endings of the source file; the workflow normalises to LF.
    lines = original.splitlines()
    inside = False
    replaced_repo = False
    replaced_tag = False
    for index, line in enumerate(lines):
        if not inside and _IMAGE_BLOCK_RE.match(line):
            inside = True
            continue
        if not inside:
            continue
        if not replaced_repo and (match := _REPO_RE.match(line)):
            lines[index] = f"{match.group(1)}repository: {repository}"
            replaced_repo = True
            continue
        if not replaced_tag and (match := _TAG_RE.match(line)):
            lines[index] = f"{match.group(1)}tag: {tag}"
            replaced_tag = True
        if replaced_repo and replaced_tag:
            break
        # Bail when the cursor leaves the image block (sibling key at four
        # spaces of indent that is not ``image:`` itself).
        if _SIBLING_RE.match(line):
            inside = False
    if not replaced_repo:
        raise ValueError(f"image.repository not found in {path}")
    if not replaced_tag:
        raise ValueError(f"image.tag not found in {path}")
    updated = "\n".join(lines) + "\n"
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="HelmRelease YAML to edit")
    parser.add_argument("repository", help="ACR repository, e.g. acr.azurecr.io/svc")
    parser.add_argument("tag", help="Image tag (commit SHA)")
    args = parser.parse_args(argv)
    if not args.path.is_file():
        print(f"::error::HelmRelease not found: {args.path}", file=sys.stderr)
        return 1
    try:
        changed = update_helmrelease(args.path, args.repository, args.tag)
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2
    print(f"{'updated' if changed else 'unchanged'}: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
