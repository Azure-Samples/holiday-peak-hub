#!/usr/bin/env python
"""Register a Foundry V3 hosted-agent version from a service manifest.

Usage::

    python scripts/ops/deploy_hosted_agent.py \\
        --agent-yaml apps/inventory-health-check/agent.hosted.yaml \\
        --image-uri <acr>.azurecr.io/inventory-health-check:<tag> \\
        --project-endpoint $PROJECT_ENDPOINT

When ``--agent-yaml`` points at a directory the loader probes for files in
the documented priority order: ``agent.manifest.yaml`` (canonical name used
by Microsoft ``foundry-samples`` and ``azd ai agent init -m``), then
``agent.hosted.yaml`` (project-internal pilot name), then ``agent.yaml``
(legacy single-file sample layout).

Environment variables used as fallbacks:

* ``PROJECT_ENDPOINT`` \u2014 ``{account}.services.ai.azure.com/api/projects/{project}``
* ``FOUNDRY_HOSTED_AGENT_CPU`` / ``FOUNDRY_HOSTED_AGENT_MEMORY``

The script delegates to
``holiday_peak_lib.foundry_hosting.deploy_hosted_agent_version`` so all the
deploy logic stays library-side and unit-testable. CI can call this script
directly after pushing the container image.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LIB_SRC = REPO_ROOT / "lib" / "src"
if LIB_SRC.is_dir() and str(LIB_SRC) not in sys.path:
    sys.path.insert(0, str(LIB_SRC))

from holiday_peak_lib.foundry_hosting import (  # noqa: E402  (path setup above)
    deploy_hosted_agent_version,
    load_manifest,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Register a Foundry V3 hosted-agent version from an "
            "agent.manifest.yaml / agent.hosted.yaml manifest."
        ),
    )
    parser.add_argument(
        "--agent-yaml",
        required=True,
        help=(
            "Path to the service's hosted-agent manifest "
            "(typically ``apps/<service>/agent.hosted.yaml``; a directory is "
            "also accepted and resolved in order: ``agent.manifest.yaml`` "
            "(canonical), ``agent.hosted.yaml``, ``agent.yaml``)."
        ),
    )
    parser.add_argument(
        "--image-uri",
        default=None,
        help=(
            "Container image to register (e.g. <acr>.azurecr.io/<repo>:<tag>). "
            "Defaults to manifest.container.image when omitted."
        ),
    )
    parser.add_argument(
        "--project-endpoint",
        default=os.environ.get("PROJECT_ENDPOINT"),
        help=(
            "Foundry project endpoint "
            "({account}.services.ai.azure.com/api/projects/{project}). "
            "Falls back to $PROJECT_ENDPOINT."
        ),
    )
    parser.add_argument(
        "--cpu",
        default=os.environ.get("FOUNDRY_HOSTED_AGENT_CPU"),
        help="Container CPU request (e.g. '1', '2'). Defaults to manifest value.",
    )
    parser.add_argument(
        "--memory",
        default=os.environ.get("FOUNDRY_HOSTED_AGENT_MEMORY"),
        help="Container memory request (e.g. '2Gi'). Defaults to manifest value.",
    )
    parser.add_argument(
        "--no-poll",
        action="store_true",
        help="Return as soon as create_version() returns; skip status polling.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=5.0,
        help="Seconds between status polls (default: 5).",
    )
    parser.add_argument(
        "--poll-timeout-seconds",
        type=float,
        default=600.0,
        help="Maximum seconds to wait for a terminal status (default: 600).",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Override one environment variable on the resolved manifest (repeatable).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the result as a single JSON line on stdout (for CI).",
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Python logging level (default: INFO).",
    )
    return parser


def _parse_env_overrides(items: list[str]) -> dict[str, str]:
    """Convert ``["A=1", "B=2"]`` into ``{"A": "1", "B": "2"}``."""
    overrides: dict[str, str] = {}
    for raw in items:
        if "=" not in raw:
            raise SystemExit(f"--env expects NAME=VALUE, got {raw!r}")
        name, value = raw.split("=", 1)
        if not name:
            raise SystemExit(f"--env name must be non-empty, got {raw!r}")
        overrides[name] = value
    return overrides


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if not args.project_endpoint:
        raise SystemExit("--project-endpoint is required (or set $PROJECT_ENDPOINT).")

    manifest = load_manifest(args.agent_yaml)
    overrides = _parse_env_overrides(args.env)

    result = deploy_hosted_agent_version(
        manifest,
        image_uri=args.image_uri,
        project_endpoint=args.project_endpoint,
        cpu=args.cpu,
        memory=args.memory,
        environment_overrides=overrides or None,
        poll=not args.no_poll,
        poll_interval_seconds=args.poll_interval_seconds,
        poll_timeout_seconds=args.poll_timeout_seconds,
    )

    if args.json:
        sys.stdout.write(
            json.dumps(
                {
                    "agent_name": result.agent_name,
                    "version": result.version,
                    "status": result.status,
                    "succeeded": result.succeeded,
                    "endpoint_url": result.endpoint_url,
                    "polled_seconds": result.polled_seconds,
                    "polling_attempts": result.polling_attempts,
                }
            )
            + "\n"
        )
    else:
        sys.stdout.write(
            "hosted-agent deploy result: "
            f"agent={result.agent_name} version={result.version} "
            f"status={result.status} succeeded={result.succeeded} "
            f"endpoint={result.endpoint_url or '<not surfaced>'}\n"
        )

    return 0 if result.succeeded else 2


if __name__ == "__main__":  # pragma: no cover - CLI entry
    raise SystemExit(main())
