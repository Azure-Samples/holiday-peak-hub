# ADR-009: AKS with Helm, KEDA, and Canary Deployments

**Status**: Accepted  
**Date**: 2024-12

## Context

Need container orchestration with:
- Auto-scaling based on load (CPU, queue depth, custom metrics)
- Zero-downtime deployments
- Resource isolation per service
- Observability (logs, metrics, traces)

## Decision

**Deploy on Azure Kubernetes Service with Helm charts, KEDA for scaling, and Flagger for canary deployments.**

### Components
- **AKS**: Managed Kubernetes control plane
- **Helm**: Package manager for K8s manifests
- **KEDA**: Event-driven auto-scaling (scale to zero)
- **Flagger**: Progressive delivery (canary, blue/green)

## Implementation

### Helm Chart Structure
```
.kubernetes/chart/
├── templates/
│   ├── deployment.yaml   # Pod spec
│   ├── service.yaml      # ClusterIP service
│   ├── ingress.yaml      # NGINX ingress
│   ├── scaledobject.yaml # KEDA triggers
│   └── canary.yaml       # Flagger canary
└── values.yaml           # Config per env
```

### KEDA Scaling
Scale based on:
- Event Hub lag (for async consumers)
- HTTP queue depth (for API services)
- Custom metrics (e.g., Redis queue length)

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: inventory-health-check
spec:
  scaleTargetRef:
    name: inventory-health-check
  triggers:
    - type: azure-eventhub
      metadata:
        consumerGroup: inventory-group
        unprocessedEventThreshold: '100'
```

### Canary Deployment
Flagger gradually shifts traffic (10% → 50% → 100%) while monitoring error rates.

## Consequences

**Positive**: Auto-scaling, progressive delivery, reduced ops burden  
**Negative**: K8s complexity, resource overhead, YAML maintenance

## Related ADRs
- [ADR-002: Azure Services](adr-002-azure-services.md)
