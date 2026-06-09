# ADR-017: Deployment Strategy - azd Provisioning + Flux CD GitOps

**Status**: Accepted (Revised)  
**Date**: 2026-02  
**Updated**: 2026-04-28 — Consolidated Flux CD deployment decision into unified deployment ADR. Infrastructure provisioning via `azd provision`; application deployment via Flux CD.  
**Updated**: 2026-05-21 — Phase 2 completed: rolled out HelmRelease-driven reconciliation to all 27 AKS services (1 CRUD + 26 agents). Removed the `commit-rendered-manifests` workflow seam that pushed bot commits to protected `main` (rejected by `main-governance-baseline` ruleset, GH013). Flux now reconciles `.kubernetes/releases/{crud,agents}` exclusively.  
**Deciders**: Architecture Team, Ricardo Cataldi  
**Tags**: infrastructure, deployment, ci-cd, azd, helm, aks, gitops, flux, helmrelease

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

CRUD must deploy before agents because it provisions the transactional data layer,
Event Hub connections, and Kubernetes services that agents reference via cross-namespace
DNS (ADR-026). Agents do not call CRUD REST endpoints directly (ADR-024).

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

### Evaluation Workflow Integration (Amended: 2026-04)

ADR-028 adds evaluation evidence to PR and deployment governance without changing the deployment source of truth. The current evaluation workflow is `.github/workflows/eval-advisory.yml`, whose workflow name is `agent-eval-advisory`. It discovers the pilot evaluation scope, runs `scripts/ci/run_agent_evaluation.py` for changed pilot agents, writes normalized `.foundry-results/*.json`, publishes job summaries, and uploads evaluation artifacts.

`agent-eval-advisory` is intentionally advisory and non-required. It must remain outside required branch-protection checks until `docs/governance/README.md` is explicitly revised to promote it. There is no `eval-gate.yml` or `eval-continuous.yml` workflow in the current repository snapshot, so deployment governance must reference the existing advisory workflow rather than stale gate names.

PR reviewers use evaluation artifacts as architecture and quality evidence when prompts, datasets, routing, or evaluation framework code changes. Deployment workflows remain governed by the azd + Flux path in this ADR; evaluation evidence can block a PR by human review policy, but it does not independently deploy, roll back, rename workflows, or bypass `lint` / `test` branch-protection baselines.

## Consequences

### Positive

- **Single source of truth**: `azure.yaml` defines all 22 services and their deployment config
- **Ordered rollout**: CRUD deploys first, agents follow — prevents dependency failures; agents do not call CRUD directly (ADR-024)
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
- [ADR-008: AKS Deployment](adr-008-aks-deployment.md) — AKS, Helm, and KEDA details

## Operational Recovery

### Output Recovery Mechanism

When ARM deployment state is `Failed` (e.g. `RoleAssignmentExists` conflicts mark the
deployment as Failed despite all resources being fully provisioned), `azd env refresh`
returns no values. The `Validate and recover provisioned outputs` step in `deploy-azd.yml`
queries Azure directly for missing outputs.

**Recovered resource categories** (ordered as in the workflow):

| Category | Keys recovered | Recovery method |
|----------|---------------|-----------------|
| PostgreSQL | `POSTGRES_HOST`, `POSTGRES_ADMIN_USER`, `POSTGRES_DATABASE`, `POSTGRES_AUTH_MODE`, `POSTGRES_USER` | `az postgres flexible-server list` |
| Cosmos DB | `COSMOS_ACCOUNT_URI`, `COSMOS_DATABASE` | `az cosmosdb list` |
| Key Vault | `KEY_VAULT_URI` | `az keyvault list` |
| Redis | `REDIS_HOST` | `az redis list` |
| Event Hubs | `EVENT_HUB_NAMESPACE` | `az eventhubs namespace list` |
| App Insights | `APPLICATIONINSIGHTS_CONNECTION_STRING` | `az monitor app-insights component list` |
| Storage | `BLOB_ACCOUNT_URL` | `az storage account list` |
| AI Search | `AI_SEARCH_NAME`, `AI_SEARCH_ENDPOINT`, `AI_SEARCH_INDEX`, `AI_SEARCH_VECTOR_INDEX`, `AI_SEARCH_INDEXER_NAME`, `EMBEDDING_DEPLOYMENT_NAME`, `AI_SEARCH_AUTH_MODE` | `az search service list` + defaults |
| AI Services | `AI_SERVICES_NAME` | `az cognitiveservices account list` |
| AI Project | `PROJECT_NAME`, `PROJECT_ENDPOINT` | `az resource list` + naming convention |
| **AGC** | `AGC_SUPPORT_ENABLED`, `AGC_GATEWAY_CLASS`, `AGC_FRONTEND_REFERENCE`, `AGC_CONTROLLER_DEPLOYMENT_MODE`, `AGC_SUBNET_ID`, `AGC_CONTROLLER_IDENTITY_NAME`, `AGC_CONTROLLER_IDENTITY_CLIENT_ID`, `AGC_FRONTEND_HOSTNAME` | `az network vnet subnet show`, `az identity show`, `az network alb list/frontend list` |

**AGC recovery notes**:
- Requires `alb` CLI extension (`az extension add --name alb`)
- `AGC_FRONTEND_HOSTNAME` may be empty if the ALB controller has not yet reconciled; treated as non-fatal
- Deterministic keys (`AGC_GATEWAY_CLASS`, `AGC_FRONTEND_REFERENCE`, `AGC_CONTROLLER_DEPLOYMENT_MODE`) are hardcoded constants

### RoleAssignment Idempotency

Standalone `RoleAssignment` resources in `shared-infrastructure.bicep` can produce
`RoleAssignmentExists` conflicts on re-deployment, marking the ARM deployment as `Failed`.
Mitigations:
- 4 workload identity → AI Services role assignments use empty-principal guards (`if (!empty(...))`)
- 2 AI Search → Cosmos roles remain standalone due to circular dependency (AI Search principal from AI Foundry)
- All ARM-API role assignments specify `principalType: 'ServicePrincipal'` to prevent AAD graph race conditions
- `guid()` seeds must remain stable across deployments — verify with `az deployment sub what-if` before changing

---

## Part 2: Flux CD GitOps for AKS Deployment

### Context

The platform deploys 27+ services to AKS using `helm template` + `kubectl apply` via azd (Part 1). This approach lacks release management, drift detection, atomic deploys, and Portal visibility. CNCF GitOps Principles and Azure WAF Operational Excellence recommend pull-based reconciliation for production Kubernetes at this scale.

### Decision

Adopt Flux CD via the AKS GitOps extension (`microsoft.flux`) as the deployment mechanism for all AKS services. Retain `azd provision` for infrastructure. CI pipeline builds images, updates values, and commits to Git. Flux reconciles.

#### Phase 1 (Completed): Rendered YAML + Flux Kustomize

- `render-helm.sh` generates per-service static YAML from Helm chart
- CI commits rendered manifests to `.kubernetes/rendered/`
- Flux Kustomize Controller reconciles rendered manifests to cluster
- **Limitation**: 560-line render-helm.sh duplicates Helm values logic; rendered YAML in app repo creates dual source-of-truth; merge conflicts; no branch deployment path; no native rollback

#### Phase 2 (In Progress): Flux HelmRelease — In-Cluster Rendering

Migrate from CI-rendered YAML to Flux HelmRelease CRDs that render Helm charts in-cluster. This eliminates the render-commit-reconcile cycle and enables native Helm release management.

##### Architecture

```
Phase 1: CI renders Helm → commits YAML to .kubernetes/rendered/ → Flux Kustomize applies
Phase 2: CI pushes image to ACR → Flux HelmRelease renders in-cluster from chart → applies
```

##### Implementation

- **HelmRelease CRDs** per service at `.kubernetes/releases/agents/`
- **Chart source**: Shared Helm chart at `.kubernetes/chart/` via existing GitRepository (`holiday-peak-gitops`)
- **Values inline**: Each HelmRelease contains all service configuration (env vars, resources, probes, node selectors) — no ConfigMap indirection
- **Namespace model**: HelmReleases live in `flux-system` (required by `--no-cross-namespace-refs=true` on Helm Controller), deploy resources to `holiday-peak-agents` or `holiday-peak-crud` via `spec.targetNamespace`
- **Release naming**: Explicit `spec.releaseName` matching the service name to preserve resource naming conventions
- **Migration path**: Incremental — each service migrates by removing its `all.yaml` reference from the rendered kustomization and adding a HelmRelease file to `.kubernetes/releases/agents/`
- **Integration**: The existing Kustomization (`holiday-peak-gitops-holiday-peak-agents`) already has patches to inject `sourceRef` into HelmRelease resources — Phase 2 was designed into the infrastructure from the start

##### Directory Structure

```
.kubernetes/
├── chart/                              # Shared Helm chart (unchanged)
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── releases/
│   └── agents/
│       ├── kustomization.yaml          # Lists all agent HelmRelease files
│       └── ecommerce-catalog-search.yaml  # Pilot HelmRelease
└── rendered/
    └── agents/
        └── kustomization.yaml          # References both rendered YAML and ../../releases/agents
```

##### Migration Sequence (per service)

1. Create `<service>.yaml` HelmRelease in `.kubernetes/releases/agents/`
2. Remove `../<service>/all.yaml` reference from `.kubernetes/rendered/agents/kustomization.yaml`
3. Add service to `.kubernetes/releases/agents/kustomization.yaml`
4. Commit to Git → Flux Kustomize Controller applies HelmRelease → Helm Controller renders chart
5. Verify deployment, service, and routing

##### Pilot Validation (2026-04-20)

- `ecommerce-catalog-search` successfully migrated to HelmRelease
- Helm Controller installed chart `holiday-peak-service@0.1.0`
- All resource names preserved (Deployment, Service, ServiceAccount, HTTPRoute)
- E2E test: 200 OK, 5 results, correct image and env vars deployed
- Timeout env vars (`INTELLIGENT_PIPELINE_TIMEOUT_SECONDS=120`, etc.) confirmed

##### Phase 2 Completion (2026-05-21)

Pattern A (Flux HelmRelease + in-cluster Helm rendering) is the canonical AKS
deployment surface for the entire product. Trigger was the `commit-rendered-manifests`
job in `deploy-azd.yml` repeatedly failing to push bot-generated rendered manifests
to `refs/heads/main` (`main-governance-baseline` ruleset, GitHub `GH013`).
Bypass-actor and orphan-branch alternatives were rejected as anti-patterns.

What landed:

- **27 HelmReleases** in git: 1 CRUD (`.kubernetes/releases/crud/crud-service.yaml`),
  26 agents (`.kubernetes/releases/agents/<service>.yaml`). Generator script preserves
  every env var, resource limit, AGC route, command/args override, and UAMI binding
  read from the previously deployed cluster state.
- **Bicep `fluxConfig`** switched from `.kubernetes/rendered/{crud,agents}` to
  `.kubernetes/releases/{crud,agents}`. CRUD kustomization runs first; agents
  kustomization depends on it.
- **Workflow `deploy-azd.yml`**: removed `commit-rendered-manifests` job and rewired
  `wait-flux-reconciliation` to depend on `deploy-crud` / `deploy-agents` directly.
  No workflow ever pushes back to `main`.
- **Image tag policy**: HelmRelease YAML carries the immutable image tag for the
  current desired state. New deploys still build + push to ACR via `azd deploy`,
  and the existing kubectl-apply path rolls the new image. Within 5 minutes Flux
  reconciles the HelmRelease and may revert if the image tag in the YAML is older
  — image automation closes this gap (see Phase 2b).

Why this resolves the protected-branch problem permanently:

- The helm-controller renders the chart in-cluster on every reconciliation. There
  is no rendered YAML in git, so no bot commit to `main` is ever required to
  reflect a deploy.
- The HelmRelease YAML is the single source of truth for desired state. It is
  edited via normal PRs, which clears the ruleset.

#### Phase 2b (Next): Image Automation

- Flux `ImageRepository` + `ImagePolicy` + `ImageUpdateAutomation` for ACR tag updates.
- For protected branches, image-update commits arrive as auto-merging PRs (PR-bridge
  pattern) instead of direct pushes — same protection model as human edits.
- Eliminates the residual drift window where Flux can revert a freshly applied
  image to the older tag still recorded in the HelmRelease YAML.
- Branch deployment support via HelmRelease targeting different sourceRef.

##### Attempt 1 (PR #1097, reverted by issue #1099)

A first pass implemented the image-tag bridge as a GHA job named
`open-image-tag-bump-pr` embedded inside the reusable `deploy-azd.yml`. The
job consumed `tested-image-*` artifacts produced by `build-aks-images`, wrote
new tags into the 27 HelmRelease YAML files, and opened a single PR per deploy
via `gh pr create`. The intent matched Phase 2b's PR-bridge property, but the
implementation conflated three concerns that should remain separate:

1. **Deploy orchestration** (build → push → reconcile) belongs to `deploy-azd.yml`.
2. **Image promotion** (tag selection, PR authorship) belongs to Flux's
   image-reflector / image-automation controllers, which run in-cluster and
   were designed for this exact problem.
3. **Protected-branch policy** (no bot pushes to `main`) is satisfied by the
   Notification Controller writing to a feature branch and opening a PR — not
   by GHA owning the bridge.

The PR also introduced a silent **regression**: the new job declared
`permissions: pull-requests: write`, but the 27 per-service entrypoints grant
only `id-token | contents | issues: write` on their `uses:` job. GitHub
Actions enforces that nested-workflow permissions can only be maintained or
reduced — never elevated — and rejects ill-formed callees with
`startup_failure` at the orchestrator **before any runner is allocated**.
`actionlint` and `yaml.safe_load` cannot see this defect because it is a
cross-file semantic rule. Every dispatched deploy across all 27 services
short-circuited in ~7 seconds with no logs, and the regression sat undetected
for ~2 days.

##### Decision (post-mortem)

- The `open-image-tag-bump-pr` job is removed from `deploy-azd.yml`.
- The 27 HelmRelease YAML re-pins and the `scripts/ci/update_helmrelease_image.py`
  helper introduced alongside it are kept — they remain useful for manual
  promotion and for the next implementation attempt.
- The proper Phase 2b implementation uses Flux's own components:
  - `ImageRepository` per ACR repo (one per service) scanning for new tags.
  - `ImagePolicy` selecting the newest immutable digest-pinned tag.
  - `ImageUpdateAutomation` writing changes to a feature branch via the
    in-cluster `git` credential, with `push.branch` distinct from
    `checkout.branch` so the protected-branch ruleset never sees a direct push.
  - `Receiver` + `Provider` (GitHub) in the Notification Controller opening
    the bridge PR. Auto-merge is enabled on the PR via repo policy.
- A new CI gate (`scripts/ci/lint_workflow_permissions.py` run by
  `.github/workflows/lint-actions.yml`) statically validates that every
  caller's `permissions:` map is a superset of every callee's per-job
  `permissions:`. This catches the exact class of bug `actionlint` cannot.

##### Lessons learned

- Reusable-workflow permission caps must be validated at PR time, not at
  dispatch time. The fix: a custom Python linter that diff'es caller/callee
  permission maps and runs in CI on every workflow change.
- Embedding cross-cutting CD concerns inside a 3,708-line reusable workflow
  produces blast radius proportional to its size. The next attempt at
  Phase 2b stays out of `deploy-azd.yml` and lives entirely as Flux CRDs.
- Silent CI rot is a Tier-1 SLO miss. Pair this ADR with the alerting in
  `docs/ops/deploy-watchdog.md` so the next regression triggers a page,
  not a month of unnoticed startup_failures.

#### Why Flux over Argo CD

- Native AKS portal integration (`az k8s-extension`)
- Azure Policy compliance definitions for `Microsoft.KubernetesConfiguration`
- Lower resource footprint (~200 Mi vs ~1 Gi)
- Microsoft-supported as part of AKS

### Consequences (Flux CD)

**Positive**: Drift detection, self-healing, atomic deploys, release history via Git, Portal visibility, reduced CI cost, 5-15 min disaster recovery RTO. Phase 2 adds: native Helm rollback, in-cluster rendering (no render-helm.sh dependency), cleaner Git history (no rendered YAML commits), self-documenting HelmRelease values.

**Negative**: Learning curve for Flux CRDs, dual-management during migration, ~200 Mi in-cluster memory, `azd deploy` decoupled from app deployment. Phase 2 adds: HelmRelease must live in `flux-system` namespace (cross-namespace ref restriction).
