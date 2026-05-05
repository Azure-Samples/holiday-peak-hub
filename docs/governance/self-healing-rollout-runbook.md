# Self-Healing Rollout Plan and Operator Runbook

**Last Updated**: 2026-04-30

> Part of the Autonomous Agent Surface Self-Healing epic (#657).
> Governing ADR: [ADR-025](../architecture/adrs/adr-025-self-healing-boundaries.md)
> RBAC: [Self-Healing RBAC Matrix](self-healing-rbac-matrix.md)

## Feature Flags

Self-healing is controlled entirely via environment variables — no image redeployment required to enable or disable.

| Flag | Type | Default | Scope |
|------|------|---------|-------|
| `SELF_HEALING_ENABLED` | bool | `false` | Master kill-switch |
| `SELF_HEALING_DETECT_ONLY` | bool | `false` | Observe mode (detect + classify, never remediate) |
| `SELF_HEALING_RECONCILE_ON_MESSAGING_ERROR` | bool | `false` | Opt-in for messaging surface remediation |
| `SELF_HEALING_MAX_RETRIES` | int | `2` | Maximum recovery retry attempts per incident |
| `SELF_HEALING_COOLDOWN_SECONDS` | float | `5.0` | Minimum wait between retry attempts |
| `SELF_HEALING_SURFACE_MANIFEST_JSON` | JSON | (default manifest) | Custom surface contract override |

### Per-service enablement

Each service reads flags from its own environment. To enable self-healing for a single service without affecting others:

```yaml
# In Helm values or AKS ConfigMap for a specific service
env:
  - name: SELF_HEALING_ENABLED
    value: "true"
  - name: SELF_HEALING_DETECT_ONLY
    value: "true"  # Start in observe mode
```

## Rollout Milestones

### Stage 1: Observe (detect-only)

| Step | Action | Go/No-Go Criteria |
|------|--------|--------------------|
| 1.1 | Enable `SELF_HEALING_ENABLED=true` and `SELF_HEALING_DETECT_ONLY=true` for **one canary service** (e.g., `ecommerce-catalog-search`) | Service starts without errors |
| 1.2 | Monitor `/self-healing/status` endpoint for 48h | Incidents detected match expected surface failure patterns |
| 1.3 | Review incident classifications via `/self-healing/incidents` | False positive rate < 5% of detected incidents |
| 1.4 | Expand to 3 additional services | Same criteria as 1.2–1.3 |
| 1.5 | Expand to all services in dev environment | No spurious escalations in 72h |

**Go criteria for Stage 2**: Zero false-positive auto-classifications in 72h, manual review of all incident categories confirms accuracy.

### Stage 2: Remediate (single surface)

| Step | Action | Go/No-Go Criteria |
|------|--------|--------------------|
| 2.1 | Set `SELF_HEALING_DETECT_ONLY=false` for canary service | First remediation succeeds and passes verification |
| 2.2 | Trigger a controlled APIM misconfig (dev only) | Incident auto-detected, remediated, verified, and closed within 60s |
| 2.3 | Monitor for 48h in dev | Remediation success rate > 95%, no human intervention needed |
| 2.4 | Enable messaging remediation (`SELF_HEALING_RECONCILE_ON_MESSAGING_ERROR=true`) for canary | Messaging binding reset succeeds |
| 2.5 | Expand to all services in dev | No escalations for known-recoverable failure classes |

**Go criteria for Stage 3**: Full dev environment with all surfaces remediating, zero prohibited-action attempts, all incidents auditable.

### Stage 3: Production canary

| Step | Action | Go/No-Go Criteria |
|------|--------|--------------------|
| 3.1 | Enable detect-only in staging/production for canary cohort | No performance degradation (p99 latency unchanged) |
| 3.2 | Enable full remediation in staging for canary cohort | Controlled failure injection succeeds |
| 3.3 | Enable full remediation in production for canary cohort (5 services) | 72h clean run with zero false positives |
| 3.4 | Expand to all production services | All services self-healing enabled |

**Go criteria**: Platform engineering sign-off, security review checklist passed ([RBAC matrix](self-healing-rbac-matrix.md)), alerting integration confirmed.

## Emergency Disable Procedure

If self-healing causes unexpected behavior in any environment:

### Immediate (< 1 minute)

1. Set `SELF_HEALING_ENABLED=false` on the affected service(s) via environment override:
   ```bash
   kubectl set env deployment/<service-name> SELF_HEALING_ENABLED=false -n holiday-peak-agents
   ```
2. Verify the service responds normally via `/health` and `/ready`.

### Partial disable (keep detection, stop remediation)

```bash
kubectl set env deployment/<service-name> SELF_HEALING_DETECT_ONLY=true -n holiday-peak-agents
```

### Global disable (all services)

```bash
kubectl set env deployment --all SELF_HEALING_ENABLED=false -n holiday-peak-agents
```

### Post-disable triage

1. Collect diagnostic context: `GET /self-healing/incidents?limit=50`
2. For escalated incidents, call `escalation_payload(incident_id)` via the kernel to get full audit trail
3. Review the audit records for unexpected action sequences
4. File an incident report with the collected data

## Observability

### Endpoints per service

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/self-healing/status` | GET | Kernel config, manifest, counters |
| `/self-healing/incidents` | GET | List incidents (newest-first, optional `?state=` filter) |
| `/self-healing/reconcile` | POST | Trigger manual reconciliation for open incidents |

### Key metrics to monitor

| Metric | Source | Alert threshold |
|--------|--------|-----------------|
| Incident detection rate | `/self-healing/status` → `incidents_total` | > 10 new incidents/hour sustained |
| Open incident count | `/self-healing/status` → `incidents_open` | > 5 open incidents per service |
| Remediation success rate | Audit trail analysis | < 90% success rate over 24h |
| Escalation rate | Count of `incident_escalated` audit events | > 3 escalations/hour |
| Max-retries-exhausted rate | Count of `max_retries_exhausted` escalations | Any occurrence warrants investigation |

### Integration with Azure Monitor

Once the services are instrumented with Application Insights:
- Emit custom events for `incident_detected`, `incident_closed`, `incident_escalated`
- Track `time_to_detect` (signal timestamp → detection) and `time_to_remediate` (detection → closure)
- Set up alert rules for `max_retries_exhausted` and escalation rate spikes

## Failure Triage Paths

| Symptom | Likely cause | Triage steps |
|---------|-------------|-------------|
| High incident detection rate | Upstream infrastructure change (APIM policy update, AKS ingress reconfiguration) | Check recent deployments, verify APIM/AKS config matches manifest |
| All incidents escalating | Action handlers returning failure | Check handler logs, verify Azure RBAC roles per [RBAC matrix](self-healing-rbac-matrix.md) |
| No incidents detected | Feature flag disabled or service not receiving surface errors | Verify `SELF_HEALING_ENABLED=true`, check `/self-healing/status` |
| Remediation succeeded but service still unhealthy | Root cause is not surface misconfiguration (e.g., code bug) | Disable self-healing, escalate to engineering |
| Cooldown blocking reconcile | Previous incident set `_cooldown_until` in the future | Wait for cooldown to expire or manually call `/self-healing/reconcile` with `incident_id` |
