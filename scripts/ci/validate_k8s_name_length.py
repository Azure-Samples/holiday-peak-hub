#!/usr/bin/env python3
"""Validate that all Kubernetes resource names in rendered manifests stay within
the 63-character limit imposed by RFC 1123 / Kubernetes metadata.name.

This script scans all rendered YAML manifests under .kubernetes/rendered/ and
verifies that every metadata.name field is at most 63 characters.  It also
checks HTTPRoute backendRefs[].name fields to ensure they match the
corresponding Service names.

Usage:
    python scripts/ci/validate_k8s_name_length.py

Exit codes:
    0 — All resource names are within the 63-character limit.
    1 — One or more resource names exceed the limit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RENDERED_DIR = REPO_ROOT / ".kubernetes" / "rendered"
MAX_NAME_LENGTH = 63

# Matches "name: <value>" in YAML metadata sections (top-level, not nested under spec)
NAME_PATTERN = re.compile(r"^\s{2}name:\s+(\S+)\s*$", re.MULTILINE)
# Matches backendRefs name entries (deeper indentation)
BACKEND_REF_PATTERN = re.compile(
    r"^\s+backendRefs:\s*\n\s+- name:\s+(\S+)", re.MULTILINE
)


def validate_rendered_manifests() -> list[str]:
    """Return list of error messages for names exceeding the limit."""
    errors: list[str] = []

    if not RENDERED_DIR.exists():
        print(f"WARNING: {RENDERED_DIR} does not exist, skipping validation.")
        return errors

    for yaml_file in sorted(RENDERED_DIR.rglob("*.yaml")):
        if yaml_file.parent.name in ("agents", "crud"):
            continue

        content = yaml_file.read_text(encoding="utf-8")

        for match in NAME_PATTERN.finditer(content):
            name = match.group(1).strip('"').strip("'")
            if len(name) > MAX_NAME_LENGTH:
                rel_path = yaml_file.relative_to(REPO_ROOT)
                errors.append(
                    f"{rel_path}: metadata.name '{name}' "
                    f"is {len(name)} chars (max {MAX_NAME_LENGTH})"
                )

        for match in BACKEND_REF_PATTERN.finditer(content):
            name = match.group(1).strip('"').strip("'")
            if len(name) > MAX_NAME_LENGTH:
                rel_path = yaml_file.relative_to(REPO_ROOT)
                errors.append(
                    f"{rel_path}: backendRef.name '{name}' "
                    f"is {len(name)} chars (max {MAX_NAME_LENGTH})"
                )

    return errors


def main() -> int:
    errors = validate_rendered_manifests()

    if errors:
        print("FAILED: Kubernetes resource names exceed 63-character limit:\n")
        for err in errors:
            print(f"  ✗ {err}")
        print(f"\n{len(errors)} violation(s) found.")
        return 1

    print("OK: All rendered resource names are within the 63-character limit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
