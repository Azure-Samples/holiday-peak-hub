#!/usr/bin/env python3
"""Verify that every agent Dockerfile copies prompts into the production image.

This script is a fast, static CI gate that reads each agent Dockerfile and
checks for the required ``COPY ... prompts/`` line in the production stage.
It runs without Docker and catches missing-prompt packaging bugs before any
image is built — preventing the silent Foundry-agent-creation failure that
occurs when ``prompts/instructions.md`` is absent from the container.

Usage:
    python scripts/ci/verify_dockerfile_prompts.py

Exit codes:
    0 — All Dockerfiles that need the prompts COPY have it.
    1 — One or more Dockerfiles are missing the prompts COPY.

Root-cause context:
    When the ``prompts/`` directory is not copied into the prod stage, the
    ``prompt_loader`` falls back to generic instructions, Foundry refuses to
    create agents with fallback text (``fallback_instructions_refused``),
    the pod never passes its readiness probe, and /invoke returns errors.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
APPS_DIR = REPO_ROOT / "apps"

# Services that are NOT agents and do not need prompts
NON_AGENT_SERVICES = {"crud-service", "ui"}

# Pattern: COPY with prompts/ destination in the prod stage
_PROMPTS_COPY_RE = re.compile(
    r"COPY\s+.*prompts/\s+/app/apps/.+/prompts/"
)


def find_agent_services() -> list[str]:
    """Return service names that have both a Dockerfile and a prompts dir."""
    services = []
    for app_dir in sorted(APPS_DIR.iterdir()):
        if not app_dir.is_dir():
            continue
        name = app_dir.name
        if name in NON_AGENT_SERVICES:
            continue
        dockerfile = app_dir / "src" / "Dockerfile"
        prompts_dir = app_dir / "prompts"
        if dockerfile.is_file() and prompts_dir.is_dir():
            services.append(name)
    return services


def check_dockerfile(service_name: str) -> str | None:
    """Return an error message if the Dockerfile is missing prompts COPY, else None."""
    dockerfile = APPS_DIR / service_name / "src" / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")

    if _PROMPTS_COPY_RE.search(content):
        return None

    return (
        f"  {service_name}: Dockerfile missing 'COPY ... prompts/' in prod stage.\n"
        f"    File: apps/{service_name}/src/Dockerfile\n"
        f"    Fix:  Add 'COPY --chown=appuser:appgroup apps/{service_name}/prompts/ "
        f"/app/apps/{service_name}/prompts/' after the prod-builder COPY line."
    )


def main() -> int:
    services = find_agent_services()
    if not services:
        print("[verify_dockerfile_prompts] WARNING: No agent services found.")
        return 0

    errors: list[str] = []
    for svc in services:
        err = check_dockerfile(svc)
        if err:
            errors.append(err)

    if errors:
        print(
            "[verify_dockerfile_prompts] FAIL: "
            f"{len(errors)}/{len(services)} Dockerfiles missing prompts COPY.\n"
        )
        for err in errors:
            print(err)
        print(
            "\nWithout prompts in the image, Foundry agent creation is refused,\n"
            "pods never pass readiness, and /invoke returns errors.\n"
            "See: docs/architecture/standalone-deployment-guide.md § Prompt Packaging"
        )
        return 1

    print(
        f"[verify_dockerfile_prompts] OK: "
        f"{len(services)}/{len(services)} agent Dockerfiles include prompts COPY."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
