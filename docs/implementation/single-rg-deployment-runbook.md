# Single Resource Group Deployment Runbook

This runbook standardizes dev/demo operations on a single resource group:

- Resource group: `holidaypeakhub405-dev-rg`
- Project prefix: `holidaypeakhub405`
- Environment: `dev`

## Why

This repository has had outages caused by external automation stopping backend dependencies. The runbook provides a reliable way to:

- Provision quickly for demos
- Recover and reseed data when services were stopped or recreated
- Deprovision cleanly when demos end

## Standard Commands

Run from repository root.

### 1. Provision and Deploy

```powershell
./scripts/ops/demo-provision.ps1
```

This configures azd environment values for `holidaypeakhub405-dev-rg` and runs `azd up`.

### 2. Recover and Reseed

```powershell
./scripts/ops/demo-recover-and-seed.ps1
```

This starts AKS, Application Gateway, and PostgreSQL, validates APIM CRUD endpoints, and runs CRUD demo seed job.

### 3. Pause (Cost Save)

```powershell
./scripts/ops/demo-deprovision.ps1
```

This stops AKS, Application Gateway, and PostgreSQL.

### 4. Full Teardown

```powershell
./scripts/ops/demo-deprovision.ps1 -DeleteResourceGroup
```

This deletes `holidaypeakhub405-dev-rg` asynchronously.

## Connectivity Durability Notes

- Workflow defaults were aligned to `projectName=holidaypeakhub405` in:
  - `.github/workflows/deploy-azd.yml`
  - `.github/workflows/deploy-ui-swa.yml`
- CRUD seed hooks now support both PostgreSQL auth modes:
  - `POSTGRES_AUTH_MODE=password`
  - `POSTGRES_AUTH_MODE=entra`

## Required Governance Action

An external principal (`MCAPSGov-AutomationApp`) is stopping services on a daily cadence. Restrict or exclude this environment from that automation; otherwise, connectivity will continue to break regardless of deployment script quality.

## First-Failure Investigation Protocol (Deploy Workflow)

Use this protocol after the first deployment failure and before any rerun.

1. Capture run metadata (run id, attempt, job name, workflow, SHA, ref, actor, trigger).
2. Capture first-failed-step clues and relevant Kubernetes rollout diagnostics.
3. Upload and reference the workflow artifact bundle (`deploy-crud-first-failure-<run-id>-attempt-<n>`).
4. Classify root cause (`config`, `code`, `infra`, `identity`, `quota`, `transient`, `platform`) and record deterministic vs transient assessment in issue/PR.
5. Approve rerun only after hypothesis and evidence links are documented.

### Rerun policy

- Deterministic failure: rerun is blocked until fix or rollback is linked.
- Transient failure: rerun allowed with explicit justification and owner assignment.
- Repeated failure after rerun: escalate with Sev1/Sev2 incident handling and preserve evidence links.
