# Self-Healing RBAC Matrix and Security Controls

> Part of the Autonomous Agent Surface Self-Healing epic (#657).
> Governing ADR: [ADR-032](../architecture/adrs/adr-032-self-healing-boundaries.md)

## RBAC Matrix for Remediation Identities

Each agent service uses a **workload identity** (Azure Managed Identity) bound to the AKS pod via Federated Credentials. Remediation actions require the minimum Azure RBAC roles listed below.

| Surface | Remediation action | Required Azure role | Scope | Notes |
|---------|-------------------|---------------------|-------|-------|
| APIM | `sync_apim_route_config` | `API Management Service Contributor` | APIM instance resource | Read/write operations and backend configs. Does NOT grant key access. |
| AKS Ingress | `refresh_aks_ingress_bindings` | `Azure Kubernetes Service Cluster User Role` | AKS cluster resource | Allows kubeconfig read and in-cluster ingress/service object patching. |
| Messaging | `reset_messaging_consumer_bindings` | `Azure Event Hubs Data Receiver` | Event Hub namespace | Reconnect/recreate consumer group checkpoint. |
| Messaging | `reset_messaging_publisher_bindings` | `Azure Event Hubs Data Sender` | Event Hub namespace | Reconnect producer client. |
| MCP | `refresh_mcp_contract_cache` | None (in-process) | Local process | Refreshes in-memory MCP tool registry cache. No Azure RBAC needed. |
| API | `reconcile_api_surface_contract` | None (in-process) | Local process | Refreshes route registration from surface manifest. No Azure RBAC needed. |

### Denied roles (never assign to remediation identities)

| Role | Reason |
|------|--------|
| `Owner` / `Contributor` (subscription or RG) | Over-privileged — violates least privilege |
| `Azure Kubernetes Service Cluster Admin Role` | Would allow destructive cluster operations |
| `API Management Service Operator Role` | Would allow service-level operations (scaling, network changes) |
| `Key Vault Administrator` | Secret/cert rotation is a prohibited action class |

## Policy Engine Enforcement

The `SelfHealingKernel` enforces deterministic allow/deny outcomes:

1. **Allowlist**: Only actions in `_allowed_actions` can execute. Registration of any action not in this set raises `PermissionError`.
2. **Denylist**: Any action name containing tokens in `_FORBIDDEN_ACTION_TOKENS` is rejected with `PermissionError` regardless of allowlist membership. The token set covers 6 prohibited categories: image operations (`restore_image`, `image_restore`, `redeploy_image`, `image_redeploy`, `image_rollback`), code redeploy (`redeploy_code`, `code_redeploy`, `code_deploy`), resource deletion (`delete_namespace`, `namespace_delete`, `delete_resource`), secret rotation (`rotate_secret`, `secret_rotate`, `rotate_cert`, `cert_rotate`), scaling (`scale_up`, `scale_down`, `scale_out`, `scale_in`, `autoscale`), and DB migration (`migrate_schema`, `schema_migrate`, `run_migration`).
3. **Determinism**: The same input always produces the same policy decision. No probabilistic or ML-based gating.

### Action classification

| Action | Tier | Auto-execute | Precondition check |
|--------|------|-------------|-------------------|
| `reconcile_api_surface_contract` | T1 (Auto) | Yes | None |
| `refresh_mcp_contract_cache` | T1 (Auto) | Yes | None |
| `sync_apim_route_config` | T2 (Gated) | Yes | Manifest edge reference must include APIM |
| `refresh_aks_ingress_bindings` | T2 (Gated) | Yes | Manifest edge reference must include AKS_INGRESS |
| `reset_messaging_consumer_bindings` | T2 (Gated) | Yes | Failure category must be in recoverable set |
| `reset_messaging_publisher_bindings` | T2 (Gated) | Yes | Failure stage must be `publish` |

## Audit Logging Contract

Every remediation action emits structured audit records:

```json
{
  "timestamp": "2026-04-09T12:00:00Z",
  "state": "remediating",
  "event": "action_executed",
  "details": {
    "action": "sync_apim_route_config",
    "success": true,
    "details": {
      "surface": "apim"
    }
  }
}
```

The audit trail captures:
- **Actor**: `service_name` on the incident (the agent workload identity)
- **Intent**: `incident_class` and `recoverable` flag from classification
- **Command**: `action` name from the allowlist
- **Result**: `success` boolean and structured `details`

Records are stored in `Incident.audit` (in-memory) and available via `/self-healing/incidents` endpoint.

## Security Review Checklist

Before enabling self-healing in any environment, verify:

- [ ] Workload identity has only the minimum RBAC roles listed in the matrix above
- [ ] No subscription-level or resource-group-level `Contributor`/`Owner` roles assigned
- [ ] `SELF_HEALING_ENABLED` environment variable is explicitly set (not relying on default)
- [ ] `SELF_HEALING_DETECT_ONLY=true` has been run for at least one deploy cycle to validate detection accuracy
- [ ] Audit records are being captured (verify via `/self-healing/status` endpoint)
- [ ] Forbidden action tokens are not bypassed by action naming conventions
- [ ] No custom action handlers are registered outside the PR + code review process
- [ ] Incident eviction policy (`max_incidents=200`) is appropriate for the service's incident volume
- [ ] Messaging remediation opt-in (`SELF_HEALING_RECONCILE_ON_MESSAGING_ERROR`) is deliberate
- [ ] Emergency disable procedure is documented and tested (set `SELF_HEALING_ENABLED=false` via env override)
