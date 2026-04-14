# ADR-033: Migrate to Flux CD for AKS Deployment

**Status**: Accepted
**Date**: 2026-04-11
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: infrastructure, deployment, helm, aks, gitops, flux
**Supersedes**: ADR-021 deployment mechanism (azd provisioning retained)

## Context

The platform deploys 27+ services to AKS using `helm template` + `kubectl apply` via azd (ADR-021). This approach lacks release management, drift detection, atomic deploys, and Portal visibility. CNCF GitOps Principles and Azure WAF Operational Excellence recommend pull-based reconciliation for production Kubernetes at this scale.

## Decision

Adopt Flux CD via the AKS GitOps extension (`microsoft.flux`) as the deployment mechanism for all AKS services. Retain `azd provision` for infrastructure. CI pipeline builds images, updates values, and commits to Git. Flux reconciles.

### Implementation

- Install Flux via AKS extension in Bicep (`Microsoft.KubernetesConfiguration/extensions`)
- Create `Kustomization` source pointing to `.kubernetes/rendered/` directory
- Render-helm.sh continues generating per-service manifests; CI commits them to Git
- Flux Kustomize Controller reconciles rendered manifests to cluster
- `azd deploy` for AKS services becomes a Git commit instead of `kubectl apply`

### Why Flux over Argo CD

- Native AKS portal integration (`az k8s-extension`)
- Azure Policy compliance definitions for `Microsoft.KubernetesConfiguration`
- Lower resource footprint (~200 Mi vs ~1 Gi)
- Microsoft-supported as part of AKS

## Consequences

**Positive**: Drift detection, self-healing, atomic deploys, release history via Git, Portal visibility, reduced CI cost, 5-15 min disaster recovery RTO.

**Negative**: Learning curve for Flux CRDs, dual-management during migration, ~200 Mi in-cluster memory, `azd deploy` decoupled from app deployment.
