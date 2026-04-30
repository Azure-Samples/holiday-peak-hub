"""
Regenerate per-service deploy-azd entrypoint workflows.

For each single-service entrypoint (deploy-azd-<svc>.yml that called the
now-deleted deploy-azd-service.yml reusable), write a fresh entrypoint that
calls deploy-azd.yml directly with the proven contract used by
deploy-azd-dev.yml:

- githubEnvironment: dev (so jobs bind to the existing 'dev' GitHub
  Environment that has the required secrets and branch protection).
- environment: dev (azd env name).
- skipProvision: true (per-service deploys never re-run provision).
- deployStatic/uiOnly: false (per-service entrypoints are backend-only).
- serviceFilter: <service-name> (scopes the core workflow to that one svc).

Output uses LF line endings to avoid the CRLF parser edge cases that caused
every run of every per-service entrypoint to emit `startup_failure` with no
jobs scheduled.
"""

from pathlib import Path
import re
import sys

WORKFLOWS_DIR = Path(".github/workflows")

# Match entrypoints like deploy-azd-<svc>.yml that referenced the reusable
# wrapper (deploy-azd-service.yml). Exclude orchestration files.
EXCLUDE = {
    "deploy-azd.yml",
    "deploy-azd-dev.yml",
    "deploy-azd-prod.yml",
    "deploy-azd-truth.yml",      # scoped multi-service entrypoint, handled separately
    "deploy-azd-service.yml",    # already deleted
}


TEMPLATE = """name: deploy-azd-{svc} (entrypoint)

on:
  push:
    branches:
      - main
    paths:
      - apps/{svc}/**
      - lib/**
      - azure.yaml
      - .infra/**
      - .kubernetes/**
      - .github/workflows/deploy-azd.yml
      - .github/workflows/deploy-azd-{svc}.yml
  workflow_dispatch:
    inputs:
      location:
        description: Azure location
        required: true
        default: centralus
      projectName:
        description: Project prefix used by naming convention
        required: true
        default: holidaypeakhub405
      imageTag:
        description: Image tag to deploy
        required: true
        default: latest
      testedSourceSha:
        description: Optional tested source commit SHA to deploy
        required: false
        default: ''
      testedSourceRef:
        description: Optional tested source ref to deploy when testedSourceSha is empty
        required: false
        default: ''
      skipProvision:
        description: Skip azd provision and reuse the current environment infrastructure
        required: true
        type: boolean
        default: true
      forceApimSync:
        description: Force APIM sync and smoke checks even when no changed services are detected
        required: true
        type: boolean
        default: true
      autoAllowAcrRunnerIp:
        description: Temporarily allow GitHub runner egress IP in ACR firewall during deploy
        required: true
        type: boolean
        default: true
      skipPromptGates:
        description: Skip the prompt-sync CI gates (image prompt verification and Foundry instructions verification)
        required: true
        type: boolean
        default: false
      skipPostgresPreflight:
        description: Skip the PostgreSQL password preflight probe (CRUD only; ignored for agent services)
        required: true
        type: boolean
        default: false

permissions:
  id-token: write
  contents: write

concurrency:
  group: deploy-azd-dev-{svc}
  cancel-in-progress: false

jobs:
  deploy:
    permissions:
      id-token: write
      contents: write
      issues: write
    uses: ./.github/workflows/deploy-azd.yml
    with:
      environment: dev
      githubEnvironment: dev
      location: ${{{{ github.event_name == 'workflow_dispatch' && inputs.location || 'centralus' }}}}
      projectName: ${{{{ github.event_name == 'workflow_dispatch' && inputs.projectName || 'holidaypeakhub405' }}}}
      imageTag: ${{{{ github.event_name == 'workflow_dispatch' && inputs.imageTag || github.sha }}}}
      sourceSha: ${{{{ github.event_name == 'workflow_dispatch' && inputs.testedSourceSha || github.sha }}}}
      sourceRef: ${{{{ github.event_name == 'workflow_dispatch' && inputs.testedSourceRef || github.ref }}}}
      deployStatic: false
      uiOnly: false
      apiBaseUrl: ''
      deployChangedOnly: true
      skipProvision: ${{{{ fromJSON(github.event_name == 'workflow_dispatch' && toJSON(inputs.skipProvision) || 'true') }}}}
      serviceFilter: {svc}
      forceApimSync: ${{{{ fromJSON(github.event_name == 'workflow_dispatch' && toJSON(inputs.forceApimSync) || 'true') }}}}
      autoAllowAcrRunnerIp: ${{{{ fromJSON(github.event_name == 'workflow_dispatch' && toJSON(inputs.autoAllowAcrRunnerIp) || 'true') }}}}
      skipApiSmokeChecks: false
      skipPromptGates: ${{{{ fromJSON(github.event_name == 'workflow_dispatch' && toJSON(inputs.skipPromptGates) || 'false') }}}}
      skipPostgresPreflight: ${{{{ fromJSON(github.event_name == 'workflow_dispatch' && toJSON(inputs.skipPostgresPreflight) || 'false') }}}}
    secrets:
      AZURE_CLIENT_ID: ${{{{ secrets.AZURE_CLIENT_ID }}}}
      AZURE_TENANT_ID: ${{{{ secrets.AZURE_TENANT_ID }}}}
      AZURE_SUBSCRIPTION_ID: ${{{{ secrets.AZURE_SUBSCRIPTION_ID }}}}
"""


def service_name_from_file(path: Path) -> str | None:
    m = re.fullmatch(r"deploy-azd-(.+)\.yml", path.name)
    return m.group(1) if m else None


def regenerate() -> list[Path]:
    written: list[Path] = []
    for path in sorted(WORKFLOWS_DIR.glob("deploy-azd-*.yml")):
        if path.name in EXCLUDE:
            continue
        svc = service_name_from_file(path)
        if not svc:
            continue
        content = TEMPLATE.format(svc=svc)
        # Ensure LF-only line endings on disk.
        path.write_bytes(content.replace("\r\n", "\n").encode("utf-8"))
        written.append(path)
    return written


if __name__ == "__main__":
    for p in regenerate():
        print(p)
    print(f"TOTAL {len(regenerate())}", file=sys.stderr)
