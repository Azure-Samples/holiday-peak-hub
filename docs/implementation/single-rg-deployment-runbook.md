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

This starts AKS and PostgreSQL, validates direct AGC CRUD health plus APIM CRUD endpoints, and runs CRUD demo seed job.

### 3. Pre-Demo Wake-Up + Connectivity Validation

```powershell
./scripts/ops/demo-preflight-validate.ps1
```

This is the recommended command before live demos. It:

- Starts AKS, Application Gateway, and PostgreSQL when stopped.
- Validates AKS ingress/public IP signals (App Gateway public IP, AGC frontend DNS, and LoadBalancer service IPs when present).
- Validates APIM `api` and `agents/*` backend host resolution overlaps AKS ingress IP signals.
- Executes APIM smoke checks for:
  - `GET /api/health`
  - `GET /api/products?limit=1`
  - `GET /api/categories`
- Writes a report to `.tmp/demo-preflight-report-<timestamp>.json`.

### 4. Pause (Cost Save)

```powershell
./scripts/ops/demo-deprovision.ps1
```

This stops AKS, Application Gateway, and PostgreSQL.

### 5. Full Teardown

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
- Default AKS publication is now `PUBLICATION_MODE=agc`.
- Legacy ingress publication is rollback-only and must be requested explicitly with:
  - `PUBLICATION_MODE=legacy` or `PUBLICATION_MODE=dual`
  - `LEGACY_INGRESS_CLASS_NAME=<explicit-class>`

## CRUD Cutover And Rollback

The dev cutover path is now `APIM -> AGC -> AKS` for CRUD.

- Normal validation target:
  - direct AGC `GET /health`
  - APIM `GET /api/health`
  - APIM `GET /api/products?limit=1`
- Soak expectation:
  - no dependency on nginx or Web App Routing for successful CRUD traffic

If rollback is required during the soak window, use an explicit legacy override for the affected deploy only.

```powershell
$env:PUBLICATION_MODE = 'legacy'
$env:LEGACY_INGRESS_CLASS_NAME = 'webapprouting.kubernetes.azure.com'
azd deploy --service crud-service -e dev
```

Use `dual` instead of `legacy` if you need temporary side-by-side rollback validation before restoring AGC-only publication.

## UI Runtime Clarification (SWA)

The production UI on Azure Static Web Apps runs with **Next.js server runtime (hybrid)**, not static export-only hosting.

- Expected production signals:
  - `X-Powered-By: Next.js` on UI responses.
  - `x-holiday-peak-proxy: next-app-api` on `/api/*` responses served via Next Route Handlers.
- Operational implication: `/api/*` availability depends on Next server runtime health and upstream API reachability.

### How to verify

```bash
curl -s -D - -o /dev/null https://blue-meadow-00fcb8810.4.azurestaticapps.net/
curl -s -D - -o /dev/null https://blue-meadow-00fcb8810.4.azurestaticapps.net/api/health
curl -s -D - -o /dev/null "https://blue-meadow-00fcb8810.4.azurestaticapps.net/api/products?limit=1"
```

Expected results:

- HTTP status `200` for all three requests.
- `X-Powered-By: Next.js` present in at least UI/runtime-served responses.
- `x-holiday-peak-proxy: next-app-api` present on `/api/health` and `/api/products`.

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
