# Sequence Diagram: Flux CD GitOps Deployment

This diagram illustrates the GitOps deployment pipeline using Flux CD as implemented in ADR-033 (PR #785, #792).

## Flow Overview

1. **PR Merge** → Developer merges to `main`
2. **CI Build** → GitHub Actions builds and pushes container images to ACR
3. **Manifest Update** → Rendered Kubernetes manifests committed to manifests branch
4. **Flux Reconciliation** → Flux detects changes and applies to AKS clusters
5. **Health Check** → Flux validates rollout health before proceeding
6. **Self-Healing** → Flux auto-remediates drift from desired state

## Sequence Diagram

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
sequenceDiagram
    actor Dev as Developer
    participant GH as GitHub (main)
    participant CI as GitHub Actions
    participant ACR as Azure Container Registry
    participant Manifests as Manifests Branch
    participant Flux as Flux CD Controller
    participant AKS as AKS Cluster
    participant NS as K8s Namespace

    Dev->>GH: Merge PR to main
    GH->>CI: Trigger deploy-azd.yml

    Note over CI: Step 1: Build & Push
    CI->>CI: Detect changed services (matrix filter)
    CI->>ACR: docker push (changed images only)
    ACR-->>CI: Image digest

    Note over CI: Step 2: Render Manifests
    CI->>CI: helm template (per service)
    CI->>Manifests: Commit rendered YAML

    Note over Flux,NS: Step 3: GitOps Reconciliation
    Flux->>Manifests: Poll for changes (interval: 1m)
    Manifests-->>Flux: New manifest detected

    Flux->>Flux: Validate YAML schema
    Flux->>AKS: kubectl apply (dry-run)
    AKS-->>Flux: Dry-run OK

    Note over Flux: Step 4: Namespace-Isolated Deploy
    Flux->>NS: Apply to target namespace
    NS-->>Flux: Resources created/updated

    Note over Flux: Step 5: Health Check
    Flux->>NS: Watch rollout status
    NS-->>Flux: Pods ready, health probes passing

    alt Rollout Healthy
        Flux->>Flux: Mark reconciliation success
    else Rollout Failed
        Flux->>NS: Rollback to previous revision
        NS-->>Flux: Rollback complete
        Flux->>GH: Create alert (webhook)
    end

    Note over Flux,NS: Ongoing: Drift Detection
    loop Every reconciliation interval
        Flux->>NS: Compare desired vs actual state
        alt Drift detected
            Flux->>NS: Re-apply desired state
            Note over Flux: Self-healing remediation
        end
    end
```

## Namespace Isolation (ADR-034)

Services are deployed to two isolated namespaces per ADR-034:

| Namespace | Services | Network Policy |
|-----------|----------|----------------|
| `holiday-peak-crud` | crud-service (1 service) | Allow: UI ingress, agent egress |
| `holiday-peak-agents` | All 26 agent services (eCommerce, CRM, Inventory, Logistics, Product Mgmt, Search, Truth Layer) | Allow: CRUD, Event Hubs, AI Search, Cosmos DB |

## Related

- [ADR-033: Helm Deployment Strategy](../adrs/adr-033-helm-deployment-strategy.md)
- [ADR-034: Namespace Isolation](../adrs/adr-034-namespace-isolation-strategy.md)
- [Infrastructure README](../../../.infra/README.md)
