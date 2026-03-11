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
