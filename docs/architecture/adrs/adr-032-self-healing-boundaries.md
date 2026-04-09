# ADR-032: Self-Healing Boundaries, Risk Tiers, and Prohibited Actions

| Field        | Value                              |
|--------------|------------------------------------|
| **Status**   | Accepted                           |
| **Date**     | 2026-04-09                         |
| **Epic**     | #657                             |
| **Issue**    | #661                             |
| **Deciders** | Platform Engineering, Architecture |

## Context

The platform operates 27 agent microservices exposed through REST API, APIM, AKS ingress, MCP, and Event Hub messaging surfaces. Surface-level misconfigurations (stale APIM routes, ingress selector drift, messaging auth changes) cause agent downtime that is recoverable without code changes but requires manual intervention today.

To reduce MTTR for non-code incidents, we introduced a shared `SelfHealingKernel` in `holiday_peak_lib.self_healing` that follows a detect → classify → remediate → verify → escalate lifecycle. This ADR formalizes the governance boundaries, risk tiers, and prohibited actions that constrain autonomous remediation.

## Decision

### 1. Action Risk Tiers

All remediation actions are classified into three risk tiers:

| Tier | Label | Execution | Approval | Examples |
|------|-------|-----------|----------|----------|
| T1 | **Auto** | Immediate, autonomous | None — kernel executes when confidence ≥ threshold | `reconcile_api_surface_contract`, `refresh_mcp_contract_cache` |
| T2 | **Gated** | Autonomous with pre-check | Kernel validates precondition (e.g., edge manifest matches expected state) before execution | `sync_apim_route_config`, `refresh_aks_ingress_bindings`, `reset_messaging_consumer_bindings`, `reset_messaging_publisher_bindings` |
| T3 | **Manual-only** | Never autonomous | Human operator via runbook | Image rollback, namespace deletion, secret rotation, scaling changes |

The tier assignment is encoded in the kernel's `_allowed_actions` allowlist (T1 + T2 only) and `_FORBIDDEN_ACTION_TOKENS` blocklist (T3). The blocklist uses substring matching on action names to cover all 6 prohibited categories listed below.

### 2. Prohibited Actions (Hard Blocklist)

The following action classes are **permanently forbidden** from autonomous execution:

| Blocked action class | Rationale |
|---------------------|-----------|
| Image restore / redeploy | Risk of running untested or incompatible container images |
| Code redeploy | Requires CI/CD pipeline with test gates |
| Namespace / resource deletion | Destructive and non-reversible |
| Secret or certificate rotation | Requires coordinated rollout across consumers |
| Horizontal/vertical scaling changes | Cost and capacity implications require human judgment |
| Database schema or migration changes | Data integrity risk |

Enforcement: The `_FORBIDDEN_ACTION_TOKENS` set in `SelfHealingKernel._assert_action_allowed()` rejects any action name containing blocked tokens. New blocked categories must be added to this set.

### 3. Confidence Thresholds for Auto-Remediation

| Signal type | Confidence gate |
|-------------|----------------|
| HTTP surface (4xx/5xx from known endpoints) | Status code in `_SELECTED_RECOVERABLE_5XX` (500, 502, 503, 504) or 4xx range |
| Messaging surface | `failure_category` in `_RECOVERABLE_MESSAGING_FAILURE_CATEGORIES` (configuration, authentication, authorization, throttled, transient) |
| Compensation failure | **Never auto-remediate** — escalate immediately (compensation failures indicate logic errors, not surface misconfig) |
| Unknown surface / unclassified | Escalate — no autonomous action permitted |

### 4. Escalation Policy and Incident Severity Mapping

| Incident outcome | Escalation action |
|------------------|-------------------|
| Non-recoverable classification | Immediate escalation with `reason: non_recoverable_classification` |
| Detect-only mode active | Classify but do not remediate; escalate with `reason: detect_only_mode` |
| Messaging opt-in disabled | Classify but do not remediate messaging incidents; escalate with `reason: messaging_remediation_opt_in_disabled` |
| No allowlisted actions available | Escalate with `reason: no_allowlisted_actions` |
| Remediation executed but verification failed | Escalate with `reason: verification_failed` |
| Maximum retry attempts exhausted | Escalate with `reason: max_retries_exhausted` and `attempts` count |
| Action handler raises error | Record failure in audit trail; escalate if all actions fail |

Escalation today is audit-trail-only (logged in `Incident.audit`). Integration with Azure Monitor alerts and PagerDuty is deferred to #671 (rollout and observability).

### 5. Feature Flag Governance

| Flag | Default | Purpose |
|------|---------|---------|
| `SELF_HEALING_ENABLED` | `false` | Master kill-switch. When `false`, `handle_failure_signal()` returns `None`. |
| `SELF_HEALING_DETECT_ONLY` | `false` | Observe mode. Detects and classifies but never remediates — all recoverable incidents escalate. |
| `SELF_HEALING_RECONCILE_ON_MESSAGING_ERROR` | `false` | Opt-in for messaging surface auto-remediation. When `false`, messaging incidents are classified but always escalated without remediation. |
| `SELF_HEALING_MAX_RETRIES` | `2` | Maximum recovery retry attempts per incident before escalation. |
| `SELF_HEALING_COOLDOWN_SECONDS` | `5.0` | Minimum wait between retry attempts for a single incident. |
| `SELF_HEALING_SURFACE_MANIFEST_JSON` | (default) | Custom surface contract override as JSON string. |

Rollout sequence: `DETECT_ONLY=true` first → monitor false-positive rate → enable full remediation per surface.

### 6. State Machine Constraints

Valid incident state transitions:

```
DETECTED → CLASSIFIED → REMEDIATING → VERIFIED → CLOSED
                ↘ ESCALATED ↗         ↘ ESCALATED
                     ↘ REMEDIATING (re-attempt after human review)
```

- Only forward transitions allowed (no CLOSED → DETECTED).
- `ESCALATED → REMEDIATING` is the only backward transition, gated by explicit `reconcile()` call.
- Maximum 200 tracked incidents per kernel instance (oldest evicted via LRU).

## Consequences

### Benefits
- All autonomous actions are bounded by an explicit allowlist — no remediation can occur outside the approved set.
- Feature flags enable gradual rollout with immediate kill-switch.
- Full audit trail per incident supports post-incident review and compliance.
- Prohibited-action enforcement is structural (token matching), not just policy documentation.

### Risks
- Current action handlers are stubs (return success without real infrastructure calls). Strategy packs (#665, #666, #667) must implement actual remediation logic.
- Escalation is log-only today — requires alerting integration (#671) to be operationally useful.
- Confidence classification is based on HTTP status codes and failure categories, not ML-based anomaly detection. False positives are possible for edge cases.

### Trade-offs
- **Safety over speed**: The allowlist + forbidden-token approach may require code changes to approve new action types, even when they are objectively safe.
- **In-memory state**: Incidents are not persisted across restarts. Warm/cold memory integration is deferred.

## Alternatives Considered

1. **External policy engine (OPA/Gatekeeper)**: Would provide richer policy expression but adds operational complexity and latency for a runtime that must react quickly to surface failures.
2. **ML-based classification**: Deferred — the current status-code + category heuristics cover the known misconfiguration classes. ML can be layered later when we have sufficient incident data.
3. **Fully manual remediation**: Status quo — rejected because it leaves MTTR unbounded for infrastructure misconfigurations that agents could safely fix.

## References

- `holiday_peak_lib.self_healing.kernel` — runtime implementation
- `holiday_peak_lib.self_healing.models` — incident domain models
- `holiday_peak_lib.self_healing.manifest` — surface contract loader
- [ADR-023](adr-023-enterprise-resilience-patterns.md) — Enterprise resilience patterns
- [ADR-027](adr-027-apim-agc-edge.md) — APIM + AGC edge architecture
- [Self-Healing RBAC Matrix](../../governance/self-healing-rbac-matrix.md) — RBAC roles and security controls
- [Self-Healing Rollout Runbook](../../governance/self-healing-rollout-runbook.md) — Rollout milestones and operator procedures
- Epic #657 — Autonomous Agent Surface Self-Healing
