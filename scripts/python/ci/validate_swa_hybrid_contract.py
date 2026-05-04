#!/usr/bin/env python3
"""Validate SWA + Next.js hybrid runtime contract.

This guard prevents accidental drift to static-export-only mode that would
break Next Route Handlers used by `/api/*` and `/agent-api/*` proxy routes.
"""

from __future__ import annotations

from pathlib import Path
import sys


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(f"Unable to read {path}: {exc}") from exc


def assert_contains(content: str, needle: str, error: str, failures: list[str]) -> None:
    if needle not in content:
        failures.append(error)


def validate(repo_root: Path) -> list[str]:
    failures: list[str] = []

    next_config_path = repo_root / "apps" / "ui" / "next.config.js"
    deploy_ui_swa_path = repo_root / ".github" / "workflows" / "deploy-ui-swa.yml"
    deploy_azd_path = repo_root / ".github" / "workflows" / "deploy-azd.yml"
    api_proxy_path = repo_root / "apps" / "ui" / "app" / "api" / "[...path]" / "route.ts"
    agent_proxy_path = repo_root / "apps" / "ui" / "app" / "agent-api" / "[...path]" / "route.ts"

    for required in [
        next_config_path,
        deploy_ui_swa_path,
        deploy_azd_path,
        api_proxy_path,
        agent_proxy_path,
    ]:
        if not required.exists():
            failures.append(f"Missing required contract file: {required.relative_to(repo_root)}")

    if failures:
        return failures

    next_config = read_text(next_config_path)
    deploy_ui_swa = read_text(deploy_ui_swa_path)
    deploy_azd = read_text(deploy_azd_path)
    api_proxy = read_text(api_proxy_path)
    agent_proxy = read_text(agent_proxy_path)

    # Next runtime mode guard
    assert_contains(
        next_config,
        "output: 'standalone'",
        "apps/ui/next.config.js must keep output: 'standalone' for SWA hybrid runtime.",
        failures,
    )
    if "output: 'export'" in next_config or 'output: "export"' in next_config:
        failures.append("apps/ui/next.config.js must not use output: 'export' (static-only mode).")

    # Proxy handlers and identity headers guard
    assert_contains(
        api_proxy,
        "next-app-api",
        "apps/ui/app/api/[...path]/route.ts must preserve next-app-api proxy header contract.",
        failures,
    )
    assert_contains(
        agent_proxy,
        "next-app-agent-api",
        "apps/ui/app/agent-api/[...path]/route.ts must preserve next-app-agent-api proxy header contract.",
        failures,
    )

    # SWA deploy contract guard
    for workflow_name, content in [
        (".github/workflows/deploy-ui-swa.yml", deploy_ui_swa),
        (".github/workflows/deploy-azd.yml", deploy_azd),
    ]:
        assert_contains(
            content,
            "Azure/static-web-apps-deploy@v1",
            f"{workflow_name} must deploy UI via Azure/static-web-apps-deploy@v1.",
            failures,
        )
        assert_contains(
            content,
            "app_location: apps/ui",
            f"{workflow_name} must keep app_location: apps/ui.",
            failures,
        )
        assert_contains(
            content,
            "output_location: ''",
            f"{workflow_name} must keep output_location: '' for Next runtime handling.",
            failures,
        )

    if "next export" in deploy_ui_swa or "next export" in deploy_azd:
        failures.append("SWA deployment workflow must not use next export for UI build.")

    return failures


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    failures = validate(repo_root)

    if failures:
        print("SWA hybrid runtime contract: FAILED")
        for failure in failures:
            print(f"- {failure}")
        return 2

    print("SWA hybrid runtime contract: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
