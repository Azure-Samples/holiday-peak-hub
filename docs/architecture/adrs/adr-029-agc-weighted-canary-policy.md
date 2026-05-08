# ADR-029: AGC Weighted Canary Policy with Automatic Rollback

**Status**: Accepted
**Date**: 2026-05-08
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: deployment, canary, agc, observability, sre
**References**: [ADR-008](adr-008-aks-deployment.md), [ADR-017](adr-017-deployment-strategy.md), [ADR-021](adr-021-apim-agc-edge.md), [ADR-028](adr-028-continuous-agent-evaluation.md)

## Context

Application Gateway for Containers (AGC) is the canonical AKS edge for the platform (ADR-021), and Flux GitOps drives every rollout (ADR-017). Several services already run weighted routes through AGC, but the canary discipline is informal: weight ladders, hold durations, exit gates, and rollback windows are inconsistent across services and across release channels.

R1 (the Microsoft Agent Framework cutover, tracked separately) deploys 27 services across 8 bounded contexts. Without a pinned canary policy, each bounded-context cutover would relitigate the same operational questions. Worse, a fast-failure deploy could spend minutes at 5–25 % traffic before a human noticed.

This ADR formalizes the policy, pins the schema in Helm values, and mandates an **automatic rollback floor** for fast-failure scenarios.

## Decision

### 1. Mandatory Weight Ladder

Every Flux-deployed service follows a four-step canary ladder:

| Step | Weight on new version | Hold | Auto-rollback window |
|---|---|---|---|
| 0 | 0 % | n/a | n/a |
| 1 | 5 % | 15 min | first 90 s |
| 2 | 25 % | 15 min | first 90 s |
| 3 | 50 % | 15 min | first 90 s |
| 4 | 100 % | 30 min steady | first 90 s post-cutover |

After step 4 holds for 30 minutes without breach, the previous version's pods are scaled to 0 and removed from the AGC route map.

### 2. Exit Gates per Step

For each step:

1. Wait `holdSeconds` (default 900).
2. Query gate metrics over the hold window:
   - **5xx error rate** delta vs. baseline ≤ 0.5 percentage points.
   - **P95 latency** delta vs. baseline ≤ 10 %.
   - **Eval baseline** (services with continuous eval per ADR-028): score within `maxDeltaPercent` (default 5 %).
3. All gates pass → advance to next step.
4. Any gate fails outside the rollback window → halt; oncall decides hold, manual rollback, or roll forward.
5. Any gate fails **inside the first 90 s of the step** → automatic rollback to previous step weight; oncall notified post-fact.

### 3. Helm Values Schema (pinned)

Every service chart MUST declare a `canary` block matching this schema:

```yaml
canary:
  enabled: true
  steps: [5, 25, 50, 100]
  holdSeconds: 900
  rollbackWindowSeconds: 90
  gates:
    errorRate:
      enabled: true
      maxDeltaPercentagePoints: 0.5
    latencyP95:
      enabled: true
      maxDeltaPercent: 10
    eval:
      enabled: true   # only meaningful for services with eval baselines
      baselineSource: continuous-eval
      maxDeltaPercent: 5
  observability:
    dashboardUrl: <App Insights workbook URL>
    alertGroup: holiday-peak-hub-oncall
```

Drift from this schema fails the chart build via `scripts/ci/validate_canary_helm_values.py`.

### 4. Automatic Rollback Controller

A canary controller (Flagger or equivalent) runs in the cluster and:

- Steps the AGC route weights via the AGC ARM API or the Gateway API custom resources.
- Reads gate metrics from Azure Monitor / App Insights via OTEL exporters.
- Decides hold / advance / rollback per step deterministically (idempotent decisioning — same metric inputs produce the same conclusion).
- Emits a structured transition event on every state change.
- Has a watchdog: if the controller does not emit a transition event within `rollbackWindowSeconds × 1.5`, oncall is paged.

### 5. Observability Contract

Every canary transition emits a structured event with these OTEL span attributes (per ADR-031):

- `agc.canary.from_weight` (int)
- `agc.canary.to_weight` (int)
- `agc.canary.service` (string)
- `agc.canary.namespace` (string)
- `agc.canary.step_outcome` ∈ `advanced` | `held` | `rolled_back`
- `agc.canary.rollback_reason` (string, optional)

The runbook at `docs/ops/runbooks/agc-canary-rollout.md` documents trigger conditions, dashboard URLs, manual override procedure, and the post-mortem template.

## Consequences

### Positive

- Uniform canary discipline across all 27 services; bounded-context cutovers (R1) inherit the policy.
- Fast-failure deploys are auto-recovered within 90 s without human intervention.
- Eval-aware canary integrates ADR-028 directly: a regression in eval score halts the ramp.
- Helm schema validation catches drift at chart-build time, not at runtime.
- Structured transition events feed App Insights workbooks for trend analysis.

### Negative

- Adds a controller dependency in the cluster (Flagger or equivalent). Operational footprint and one more thing to monitor.
- Eval gate requires services to expose their continuous-eval baseline ID; services without baselines cannot benefit from the eval-aware ladder.
- 90-s rollback window may produce false positives on noisy metrics; tuning is per-service.

### Risks

| Risk | Mitigation |
|---|---|
| Auto-rollback fires on metric noise (false positive). | Gate threshold tuned to baseline + measurement noise (0.5 pp on error rate is well above floor noise). 90 s window is short enough that one-shot transients rarely clear the threshold. |
| Auto-rollback fails (controller dies, AGC API rate-limits). | Watchdog pages oncall when no transition event within `rollbackWindowSeconds × 1.5`. |
| Eval gate too sensitive — fails on legitimate behavior shifts. | Eval gate uses `maxDeltaPercent` (relative), not absolute. Baselines refresh nightly per ADR-028. |
| Helm schema drift between services. | CI step `scripts/ci/validate_canary_helm_values.py` rejects drift; required check on PR. |
| Single-region failure scope (no cross-region failover during canary). | Documented limitation. Multi-region canary is a future ADR. |

## Alternatives Considered

### Alternative A — Manual canary with runbook only

Rejected. Human-in-the-loop on every step inflates rollout duration and creates inconsistency across services. The 90-s automatic rollback floor is the safety net manual rollouts cannot provide.

### Alternative B — All-at-once deploys with feature flags

Rejected. Feature flags shift complexity into application code and require flag cleanup discipline that has historically failed in this repo. Canary at the traffic layer keeps deploys reversible without code changes.

### Alternative C — Argo Rollouts instead of Flagger

Considered. Both are viable. Decision deferred to platform-engineering choice during implementation; the ADR pins the **policy** (ladder, gates, schema), not the controller brand. Replacing the controller is a non-ADR change as long as the policy is preserved.

## Implementation

| Component | File / Location | Change |
|---|---|---|
| ADR | `docs/architecture/adrs/adr-029-agc-weighted-canary-policy.md` | This file |
| Runbook | `docs/ops/runbooks/agc-canary-rollout.md` | New — trigger conditions, dashboards, oncall procedure, post-mortem template |
| Helm schema validator | `scripts/ci/validate_canary_helm_values.py` | New — fails build on schema drift |
| Service Helm charts | `infra/charts/<service>/values.yaml` | Add `canary` block matching schema |
| Flux Kustomization patches | `infra/flux/<channel>/patches/canary.yaml` | Pin per-channel overrides (`dev`, `staging`, `prod`) |
| Controller | Cluster add-on (Flagger candidate) | Deployed via Flux; emits transition events |
| OTEL spans | per ADR-031 | `agc.canary.*` attributes on transitions |

## Verification

- **Synthetic-success run**: deploy a known-good build of one service; verify ladder progresses 5 → 25 → 50 → 100 cleanly within ~75 minutes total.
- **Synthetic-chaos run**: deploy a deliberately-broken build (latency injection, error injection); verify automatic rollback within ≤ 90 s of step 1 breach; verify oncall alert fired; verify dashboard reflects the rollback.
- **No-flapping check**: one breach within 90 s triggers exactly one rollback, not a rollback loop. Validated by replaying a metric trace through the controller.
- **Eval-aware canary**: at least one service with a continuous-eval baseline runs through the ladder; eval gate exercised in both success and breach paths.

## Pattern References

- **Canary Release** — microservices.io
- **Bulkhead + Circuit Breaker** — microservices.io. The 90-s window is the bulkhead; per-step gates are circuit breakers.
- **Observability** — Azure Well-Architected Framework, Operational Excellence pillar.

## References

- [Application Gateway for Containers documentation](https://learn.microsoft.com/azure/application-gateway/for-containers/)
- [Flagger](https://flagger.app/)
- [ADR-008 — AKS with Helm, KEDA, and Canary Deployments](adr-008-aks-deployment.md)
- [ADR-017 — Deployment Strategy: azd Provisioning + Flux CD GitOps](adr-017-deployment-strategy.md)
- [ADR-021 — APIM + AGC as the Canonical AKS Edge](adr-021-apim-agc-edge.md)
- [ADR-028 — Continuous Agent Evaluation](adr-028-continuous-agent-evaluation.md)
- [ADR-031 — OTEL Span Attributes Contract for Retail Agents](adr-031-otel-span-attributes-contract.md)
