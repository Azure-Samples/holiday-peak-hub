# ADR-033: Migrate to Flux CD for AKS Deployment

**Status**: Accepted (Phase 2 in progress)
**Date**: 2026-04-11 (Phase 2: 2026-04-20)
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: infrastructure, deployment, helm, aks, gitops, flux, helmrelease
**Supersedes**: ADR-021 deployment mechanism (azd provisioning retained)

## Context

The platform deploys 27+ services to AKS using `helm template` + `kubectl apply` via azd (ADR-021). This approach lacks release management, drift detection, atomic deploys, and Portal visibility. CNCF GitOps Principles and Azure WAF Operational Excellence recommend pull-based reconciliation for production Kubernetes at this scale.

## Decision

Adopt Flux CD via the AKS GitOps extension (`microsoft.flux`) as the deployment mechanism for all AKS services. Retain `azd provision` for infrastructure. CI pipeline builds images, updates values, and commits to Git. Flux reconciles.

### Phase 1 (Completed): Rendered YAML + Flux Kustomize

- `render-helm.sh` generates per-service static YAML from Helm chart
- CI commits rendered manifests to `.kubernetes/rendered/`
- Flux Kustomize Controller reconciles rendered manifests to cluster
- **Limitation**: 560-line render-helm.sh duplicates Helm values logic; rendered YAML in app repo creates dual source-of-truth; merge conflicts; no branch deployment path; no native rollback

### Phase 2 (In Progress): Flux HelmRelease — In-Cluster Rendering

Migrate from CI-rendered YAML to Flux HelmRelease CRDs that render Helm charts in-cluster. This eliminates the render-commit-reconcile cycle and enables native Helm release management.

#### Architecture

```
Phase 1: CI renders Helm → commits YAML to .kubernetes/rendered/ → Flux Kustomize applies
Phase 2: CI pushes image to ACR → Flux HelmRelease renders in-cluster from chart → applies
```

#### Implementation

- **HelmRelease CRDs** per service at `.kubernetes/releases/agents/`
- **Chart source**: Shared Helm chart at `.kubernetes/chart/` via existing GitRepository (`holiday-peak-gitops`)
- **Values inline**: Each HelmRelease contains all service configuration (env vars, resources, probes, node selectors) — no ConfigMap indirection
- **Namespace model**: HelmReleases live in `flux-system` (required by `--no-cross-namespace-refs=true` on Helm Controller), deploy resources to `holiday-peak-agents` or `holiday-peak-crud` via `spec.targetNamespace`
- **Release naming**: Explicit `spec.releaseName` matching the service name to preserve resource naming conventions
- **Migration path**: Incremental — each service migrates by removing its `all.yaml` reference from the rendered kustomization and adding a HelmRelease file to `.kubernetes/releases/agents/`
- **Integration**: The existing Kustomization (`holiday-peak-gitops-holiday-peak-agents`) already has patches to inject `sourceRef` into HelmRelease resources — Phase 2 was designed into the infrastructure from the start

#### Directory Structure

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

#### Migration Sequence (per service)

1. Create `<service>.yaml` HelmRelease in `.kubernetes/releases/agents/`
2. Remove `../<service>/all.yaml` reference from `.kubernetes/rendered/agents/kustomization.yaml`
3. Add service to `.kubernetes/releases/agents/kustomization.yaml`
4. Commit to Git → Flux Kustomize Controller applies HelmRelease → Helm Controller renders chart
5. Verify deployment, service, and routing

#### Pilot Validation (2026-04-20)

- `ecommerce-catalog-search` successfully migrated to HelmRelease
- Helm Controller installed chart `holiday-peak-service@0.1.0`
- All resource names preserved (Deployment, Service, ServiceAccount, HTTPRoute)
- E2E test: 200 OK, 5 results, correct image and env vars deployed
- Timeout env vars (`INTELLIGENT_PIPELINE_TIMEOUT_SECONDS=120`, etc.) confirmed

### Phase 2b (Future): Image Automation

- Flux `ImageRepository` + `ImagePolicy` + `ImageUpdateAutomation` for ACR tag updates
- Eliminates CI committing image tags; Flux watches ACR directly
- Branch deployment support via HelmRelease targeting different sourceRef

### Why Flux over Argo CD

- Native AKS portal integration (`az k8s-extension`)
- Azure Policy compliance definitions for `Microsoft.KubernetesConfiguration`
- Lower resource footprint (~200 Mi vs ~1 Gi)
- Microsoft-supported as part of AKS

## Consequences

**Positive**: Drift detection, self-healing, atomic deploys, release history via Git, Portal visibility, reduced CI cost, 5-15 min disaster recovery RTO. Phase 2 adds: native Helm rollback, in-cluster rendering (no render-helm.sh dependency), cleaner Git history (no rendered YAML commits), self-documenting HelmRelease values.

**Negative**: Learning curve for Flux CRDs, dual-management during migration, ~200 Mi in-cluster memory, `azd deploy` decoupled from app deployment. Phase 2 adds: HelmRelease must live in `flux-system` namespace (cross-namespace ref restriction).
