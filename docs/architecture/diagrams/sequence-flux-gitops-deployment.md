# Sequence Diagram: Flux CD GitOps Deployment

This diagram illustrates the GitOps deployment pipeline using Flux CD as implemented in ADR-017.

## Deployment Patterns

### Phase 2: HelmRelease (target state, pilot: ecommerce-catalog-search)

Services migrated to Phase 2 use Flux HelmRelease CRDs that render the shared Helm chart in-cluster.

1. **PR Merge** → Developer merges HelmRelease changes to `main`
2. **CI Build** → GitHub Actions builds and pushes container images to ACR
3. **HelmRelease Update** → Developer updates image tag in `.kubernetes/releases/agents/<service>.yaml`
4. **Flux Reconciliation** → Kustomize Controller applies HelmRelease CRD → Helm Controller renders chart in-cluster
5. **Health Check** → Flux validates rollout health
6. **Self-Healing** → Flux auto-remediates drift from desired state

### Phase 1: Rendered YAML (legacy, 25 services)

Services not yet migrated use the original pattern where CI renders Helm to static YAML.

1. **PR Merge** → Developer merges to `main`
2. **CI Build** → GitHub Actions builds and pushes container images to ACR
3. **Manifest Render** → `render-helm.sh` generates static YAML, CI commits to Git
4. **Flux Reconciliation** → Kustomize Controller applies rendered YAML to cluster

## Phase 2 Sequence Diagram (HelmRelease)

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
    participant FK as Flux Kustomize Controller
    participant FH as Flux Helm Controller
    participant AKS as AKS Cluster
    participant NS as K8s Namespace

    Dev->>GH: Merge PR to main
    GH->>CI: Trigger deploy-azd.yml

    Note over CI: Step 1: Build & Push
    CI->>CI: Detect changed services (matrix filter)
    CI->>ACR: docker push (changed images only)
    ACR-->>CI: Image digest

    Note over CI: Step 2: Update HelmRelease
    CI->>GH: Update image tag in .kubernetes/releases/agents/<service>.yaml
    CI->>GH: Commit [skip ci]

    Note over FK,NS: Step 3: GitOps Reconciliation
    FK->>GH: Poll for changes (interval: 5m)
    GH-->>FK: New HelmRelease detected
    FK->>FH: Apply HelmRelease CRD

    Note over FH: Step 4: In-Cluster Helm Rendering
    FH->>GH: Fetch chart from .kubernetes/chart/
    FH->>FH: helm install/upgrade with inline values
    FH->>NS: Apply rendered resources to target namespace
    NS-->>FH: Resources created/updated

    Note over FH: Step 5: Health Check
    FH->>NS: Watch rollout status
    NS-->>FH: Pods ready, health probes passing

    alt Rollout Healthy
        FH->>FH: Mark HelmRelease Ready
    else Rollout Failed
        FH->>FH: Rollback to previous Helm revision
        FH->>GH: Create alert (webhook)
    end

    Note over FK,NS: Ongoing: Drift Detection
    loop Every reconciliation interval
        FH->>NS: Compare Helm release vs actual state
        alt Drift detected
            FH->>NS: Re-apply Helm release
            Note over FH: Self-healing remediation
        end
    end
```

## Phase 1 Sequence Diagram (Rendered YAML — Legacy)

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

## Namespace Isolation (ADR-026)

Services are deployed to two isolated namespaces per ADR-026:

| Namespace | Services | Network Policy |
|-----------|----------|----------------|
| `holiday-peak-crud` | crud-service (1 service) | Allow: UI ingress, agent egress |
| `holiday-peak-agents` | All 26 agent services (eCommerce, CRM, Inventory, Logistics, Product Mgmt, Search, Truth Layer) | Allow: CRUD, Event Hubs, AI Search, Cosmos DB |

## Related

- [ADR-017: Helm Deployment Strategy](../adrs/adr-017-deployment-strategy.md)
- [ADR-026: Namespace Isolation](../adrs/adr-026-namespace-isolation-strategy.md)
- [Infrastructure README](../../../.infra/README.md)
