# ADR-021: azd-First Deployment with GitHub Actions CI/CD

**Status**: Accepted  
**Date**: 2026-02  
**Deciders**: Architecture Team, Ricardo Cataldi  
**Tags**: infrastructure, deployment, ci-cd, azd

## Context

The accelerator needs a repeatable, environment-scoped deployment strategy for:
- Provisioning shared infrastructure (AKS, Cosmos DB, Redis, Event Hubs, ACR, etc.)
- Deploying 22 services (1 CRUD + 21 agents) to AKS in the correct order
- Supporting both local developer workflows and CI/CD pipelines
- Maintaining separation of concerns: scaffolding tools vs deployment orchestration

Previously, the CLI (`cli.py`) handled both scaffolding and deployment orchestration.
This conflated two concerns and created maintenance burden for deployment logic that
should live in the platform tooling.

### Requirements

- **Ordered rollout**: CRUD service must deploy before agent services
- **Parallel agent deployment**: 21 agents deploy concurrently for speed
- **Environment isolation**: dev, staging, prod with separate config
- **OIDC authentication**: No stored secrets for Azure credentials in CI
- **Idempotent**: Re-running deployment does not cause failures
- **Local parity**: Developers can run the same deployment commands locally

## Decision

**Adopt Azure Developer CLI (azd) as the sole deployment and provisioning tool.
Restrict the Python CLI (`cli.py`) to scaffolding utilities only.
Use GitHub Actions for CI/CD with ordered rollout.**

### Architecture

```
┌──────────────────────────────────────────────────┐
│ GitHub Actions Workflow (.github/workflows/       │
│                         deploy-azd.yml)           │
│                                                   │
│  ┌─────────┐    ┌────────────┐    ┌────────────┐ │
│  │provision │───▶│deploy-crud │───▶│deploy-agents│ │
│  │(azd      │    │(azd deploy │    │(21 services │ │
│  │provision)│    │ --service  │    │ in parallel │ │
│  │          │    │ crud-svc)  │    │ matrix)     │ │
│  └─────────┘    └────────────┘    └────────────┘ │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ azure.yaml (project definition)                   │
│                                                   │
│  services:                                        │
│    crud-service:       host: aks                  │
│    crm-campaign-*:     host: aks                  │
│    ecommerce-*:        host: aks                  │
│    inventory-*:        host: aks                  │
│    logistics-*:        host: aks                  │
│    product-mgmt-*:     host: aks                  │
│                                                   │
│  Each service uses Helm predeploy hooks:          │
│    render-helm.ps1 / render-helm.sh               │
│    → helm template → .kubernetes/rendered/{svc}/  │
│    → azd applies rendered manifests               │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│ cli.py (scaffolding only)                         │
│                                                   │
│  generate-bicep       Generate Bicep modules      │
│  generate-dockerfile  Generate Dockerfiles         │
│                                                   │
│  No deployment, provisioning, or orchestration.   │
└──────────────────────────────────────────────────┘
```

### Deployment Flow

#### 1. Provisioning (azd provision)

```bash
azd env set deployShared true -e dev
azd env set deployStatic true -e dev
azd env set environment dev -e dev
azd env set location eastus2 -e dev
azd provision -e dev
```

Provisions: AKS (3 pools), ACR, PostgreSQL (CRUD), Cosmos DB (agent warm memory), Redis,
Event Hubs (5 topics), Key Vault, APIM, AI Foundry, VNet (5 subnets), NSGs, Private DNS
Zones, App Insights.

#### 2. CRUD-First Deployment

```bash
azd deploy --service crud-service -e dev
```

CRUD must be available before agents because agents call CRUD REST endpoints
for transactional operations (products, orders, cart).

#### 3. Parallel Agent Deployment

```bash
azd deploy --all -e dev
```

Or individually:

```bash
azd deploy --service ecommerce-catalog-search -e dev
```

In CI, the 21 agent services deploy in a GitHub Actions matrix (parallel, fail-fast: false).

### Helm Predeploy Hooks

Each service in `azure.yaml` declares a predeploy hook that renders Helm charts
before azd applies them:

```yaml
hooks:
  predeploy:
    windows:
      shell: pwsh
      run: ../../../.infra/azd/hooks/render-helm.ps1 -ServiceName crud-service
    posix:
      shell: sh
      run: ../../../.infra/azd/hooks/render-helm.sh crud-service
```

The hook:
1. Runs `helm template` with service-specific values against `.kubernetes/chart/`
2. Writes rendered YAML to `.kubernetes/rendered/{service}/manifest.yaml`
3. azd picks up the rendered path from `k8s.deploymentPath` and applies it

### Environment Variables

Stored in `.azure/{env}/.env` and injected at deploy time:

```bash
K8S_NAMESPACE=holiday-peak
IMAGE_PREFIX=ghcr.io/azure-samples      # or ACR login server
IMAGE_TAG=latest
KEDA_ENABLED=false
```

### GitHub Actions Workflow

The deployment model uses environment entrypoints plus a reusable core:

- **Dev entrypoint** (`.github/workflows/deploy-azd-dev.yml`) — supports push-triggered and manual development deployments
- **Prod entrypoint** (`.github/workflows/deploy-azd-prod.yml`) — runs only for stable release tags after release/lineage validation
- **Reusable core** (`.github/workflows/deploy-azd.yml`) — invoked through `workflow_call` and not used as a direct operator entrypoint
- **OIDC federation** — federated identity for Azure login (no client secrets)
- **Ordered jobs**: provision → deploy-crud → deploy-ui (optional) → deploy-agents
- **Parallel agent matrix** — all agents deploy concurrently in the agents phase
- **Seed policy** — demo data seeding is run locally by operators, outside CI/CD deployment workflows

Manual trigger examples:

```bash
gh workflow run deploy-azd-dev.yml -f location=eastus2 -f projectName=holidaypeakhub -f imageTag=latest -f deployStatic=true
```

Seeding behavior:

- The demo seeder uses deterministic IDs with upsert semantics, so re-runs do not duplicate seeded entities.
- Reducing configured seed counts does not remove previously seeded higher-index entities.

Required repository secrets:
- `AZURE_CLIENT_ID` — Service principal / managed identity client ID
- `AZURE_TENANT_ID` — Azure AD tenant
- `AZURE_SUBSCRIPTION_ID` — Target subscription

## Consequences

### Positive

- **Single source of truth**: `azure.yaml` defines all 22 services and their deployment config
- **Ordered rollout**: CRUD deploys first, agents follow — prevents dependency failures
- **Environment scoping**: azd environments isolate dev/staging/prod config
- **Local parity**: Same `azd deploy` command works locally and in CI
- **Separation of concerns**: CLI stays lightweight (scaffolding only)
- **OIDC security**: No stored Azure credentials in GitHub
- **Parallelism**: 21 agents deploy concurrently in CI, reducing total deploy time

### Negative

- **azd dependency**: Teams must install azd locally
- **Helm template indirection**: Predeploy hooks add a step vs direct `helm install`
- **No rollback built-in**: azd does not provide `azd rollback`; use `kubectl rollout undo` instead
- **Matrix job cost**: 21 parallel GitHub Actions runners consume billable minutes

### Risk Mitigation

- **azd installation**: Automated via `winget install Microsoft.Azd` or `Azure/setup-azd@v1` in CI
- **Rollback**: Document `kubectl rollout undo` procedure in operations README
- **CI cost**: Use `fail-fast: false` to avoid wasting partial runs; optimize runner size

## Alternatives Considered

### CLI-Based Deployment Orchestration

The original approach where `cli.py` contained `deploy`, `deploy-all`, and `provision` commands.

- **Pros**: Single tool, Python-native
- **Cons**: Reimplements azd functionality, hard to maintain, no OIDC support, no environment scoping

### Helm-Only (No azd)

Direct `helm install` / `helm upgrade` for each service.

- **Pros**: Standard K8s tooling, native `helm rollback`
- **Cons**: No infrastructure provisioning, no environment management, manual ordering required,
  no integration with Bicep provisioning flow

### Terraform + ArgoCD

Infrastructure with Terraform, GitOps deployment with ArgoCD.

- **Pros**: GitOps best practice, automatic drift detection
- **Cons**: Two separate tools to learn, ArgoCD control plane adds cost, overengineered for
  22-service accelerator, Bicep infra already committed

### Azure DevOps Pipelines

Use Azure DevOps instead of GitHub Actions.

- **Pros**: Tighter Azure integration, pipeline agents in VNet
- **Cons**: Repository is on GitHub, context switching, less community support for OIDC federation

## Related ADRs

- [ADR-002: Azure Services](adr-002-azure-services.md) — Service stack selection
- [ADR-009: AKS Deployment](adr-009-aks-deployment.md) — AKS, Helm, and KEDA details
