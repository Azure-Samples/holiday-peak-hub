# ADR-009: AKS with Helm, KEDA, and Canary Deployments

**Status**: Accepted  
**Date**: 2024-12  
**Updated**: 2026-02  
**Deciders**: Architecture Team, Ricardo Cataldi

## Context

Need container orchestration with:
- Auto-scaling based on load (CPU, queue depth, custom metrics)
- Zero-downtime deployments
- Resource isolation per service (CRUD vs Agent workloads)
- Observability (logs, metrics, traces)
- Private cluster support for production environments
- azd-driven deployment workflow for consistency

## Decision

**Deploy on Azure Kubernetes Service with Helm charts, KEDA for scaling, and weight-based canary deployments.**

## Implementation Status (2026-03-18)

- **Implemented**: AKS remains the deployment target, with Helm-based rendering, azd deployment orchestration, and KEDA templates present in `.kubernetes/chart`.
- **Implemented in part**: Ordered rollout and environment-scoped deployment workflows are active in GitHub Actions.
- **Superseded in ingress details**: North-south ingress assumptions from this ADR are now governed by [ADR-027](adr-027-apim-agc-edge.md), which sets APIM -> AGC -> AKS as canonical.
- **Deferred/diverged**: Service-mesh-level canary traffic control is not a universal runtime baseline across all services.

### Components
- **AKS**: Managed Kubernetes control plane (Azure RBAC enabled, OIDC issuer profile)
- **Helm 3**: Package manager for K8s manifests (template + apply workflow)
- **KEDA**: Event-driven auto-scaling (scale based on Event Hub lag, custom metrics)
- **azd**: Azure Developer CLI for provisioning and service deployment
- **ACR**: Azure Container Registry for image storage (AcrPull via Managed Identity)

## Implementation

### Helm Chart Structure

```
.kubernetes/chart/
├── Chart.yaml            # Chart metadata (holiday-peak-service v0.1.0)
├── values.yaml           # Default values (image, replicas, probes, KEDA, canary)
└── templates/
    ├── _helpers.tpl       # Template helpers (fullname)
    ├── deployment.yaml    # Pod spec with liveness/readiness probes
    ├── service.yaml       # ClusterIP service (port 80 → 8000)
    └── keda.yaml          # KEDA ScaledObject (conditional on keda.enabled)
```

### Node Pools

AKS provisions **three dedicated node pools** with taints for workload isolation:

| Pool | Mode | Taint | Workloads | Autoscale (dev) | Autoscale (prod) |
|------|------|-------|-----------|-----------------|------------------|
| `system` | System | *(none)* | K8s system components | 1–3 | 1–5 |
| `agents` | User | `workload=agents:NoSchedule` | 21 agent services | 2–10 | 2–20 |
| `crud` | User | `workload=crud:NoSchedule` | CRUD service | 1–5 | 1–10 |

All pools use `Standard_D8ds_v5` VMs with Azure CNI networking.

### Deployment Workflow

Services deploy via azd with Helm predeploy hooks:

1. **azd** invokes the predeploy hook (`render-helm.ps1` / `render-helm.sh`)
2. Hook runs `helm template` against `.kubernetes/chart/` with service-specific values
3. Rendered manifests are written to `.kubernetes/rendered/{service}/`
4. **azd** applies the rendered manifests to the AKS cluster via `kubectl apply`

```bash
# Deploy CRUD first (must exist before agents)
azd deploy --service crud-service -e dev

# Deploy all agents in parallel
azd deploy --all -e dev
```

### KEDA Scaling

Scale based on:
- Event Hub lag (for async consumer agents)
- Custom metrics (e.g., Redis queue length)

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: inventory-health-check
spec:
  scaleTargetRef:
    name: inventory-health-check
  pollingInterval: 30
  minReplicaCount: 1
  maxReplicaCount: 5
  triggers:
    - type: azure-eventhub
      metadata:
        connection: EventHubConnection
        eventHubName: inventory-events
        consumerGroup: $Default
        blobContainer: keda-checkpoints
        storageConnection: StorageConnection
```

### Canary Deployment

Weight-based canary via Helm values (canary label + traffic weight):

```yaml
# values.yaml excerpt
canary:
  enabled: true
  weight: 10   # 10% traffic to canary pods
```

The deployment template applies a `canary: "true"` label when enabled.
Traffic splitting is managed at the service mesh or ingress layer.

### Private Cluster Access (Production)

Production clusters disable public network access. Use `az aks command invoke`
to run kubectl commands through the Azure control plane:

```bash
az aks command invoke \
  --resource-group holidaypeakhub-prod-rg \
  --name holidaypeakhub-prod-aks \
  --command "kubectl get pods -n holiday-peak"
```

### CI/CD Integration

The GitHub Actions workflow (`.github/workflows/deploy-azd.yml`) enforces ordered rollout:

1. **provision** — `azd provision` for infrastructure
2. **deploy-crud** — CRUD service first (other services depend on it)
3. **deploy-agents** — 21 agent services in parallel matrix

Authentication uses OIDC federation (no stored secrets for Azure credentials).

## Consequences

**Positive**:
- Workload isolation via node pool taints
- Event-driven autoscaling with KEDA
- Ordered deployment (CRUD → agents) prevents dependency failures
- azd provides repeatable, environment-scoped deployments
- Private cluster support for production security

**Negative**:
- K8s complexity, resource overhead, YAML maintenance
- Three node pools increase base cost
- Private cluster requires `az aks command invoke` or VPN for debugging
- Helm template + apply is less interactive than `helm install`

## Related ADRs

- [ADR-002: Azure Services](adr-002-azure-services.md) — AKS and ACR selection
- [ADR-021: azd-First Deployment](adr-021-azd-first-deployment.md) — CI/CD and deployment strategy
