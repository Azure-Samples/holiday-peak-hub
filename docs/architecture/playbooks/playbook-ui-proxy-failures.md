# UI Proxy Failures Playbook

## Scope

Operational response for UI proxy failures in `apps/ui/app/api/[...path]/route.ts` where users see `502` bursts or degraded fallback behavior.

This playbook preserves existing payload contracts and APIM-first routing policy semantics.

## Trigger conditions and detection metrics

Primary triggers:

- Sustained `502` rate on critical UI endpoints exceeds threshold.
- Spike in proxy failure events grouped by `failureKind`.

Required telemetry dimensions for triage:

- `failureKind`
- `upstreamPath`
- `sourceKey`
- `status`
- `fallbackUsed`

Alert thresholds:

- Warn: `502` rate >= 3% over 10 minutes, request count >= 30.
- Critical: `502` rate >= 8% over 5 minutes, request count >= 50.

## Triage sequence

1. Confirm incident scope.
   - Identify impacted endpoint groups from `upstreamPath`.
   - Validate whether failures are isolated to critical endpoints from issue #546 contract set.
2. Segment by failure class.
   - Group by `failureKind` and rank by event volume.
   - Check whether `fallbackUsed=true` is absorbing user impact.
3. Run class-specific checks.

### Class A: config failures

Signals:

- `failureKind=config`
- `sourceKey` missing or unset
- Immediate `502` without upstream call evidence

Checks:

- Validate UI runtime env aliases are present and non-empty.
- Confirm deployment slot/environment contains expected APIM base URL values.

### Class B: policy failures

Signals:

- `failureKind=policy`
- Base URL present but rejected by proxy policy

Checks:

- Verify configured proxy target matches APIM host policy (`*.azure-api.net`) unless explicit local-dev override is enabled.
- Confirm no recent config drift introduced non-APIM endpoints.

### Class C: network failures

Signals:

- `failureKind=network`
- Proxy fetch exceptions, no upstream status code
- Catalog reads (`/api/products`, `/api/categories`) may enter this class after a 10 second per-attempt proxy timeout aborts a stalled upstream call before falling back to `200` with `[]`.

Checks:

- Validate DNS resolution and outbound connectivity from UI runtime to APIM endpoint.
- Check firewall/NSG/egress policy changes in preceding deployment window.

### Class D: upstream failures

Signals:

- `failureKind=upstream`
- Upstream status present and often `502`

Checks:

- Inspect APIM backend health and recent policy changes.
- Correlate with AGC/AKS service health and backend dependency failures.

## Mitigation steps

1. Config/policy class:
   - Restore APIM gateway URL aliases in UI environment configuration.
   - Redeploy UI runtime to apply corrected variables.
2. Network class:
   - Roll back or fix blocking network policy.
   - Validate APIM reachability from UI runtime after change.
3. Upstream class:
   - Engage owning API/agent service team.
   - Execute backend recovery runbooks and APIM smoke validation.
4. During mitigation:
   - Monitor `fallbackUsed` volume to ensure degraded mode remains explicit and temporary.

## Prevention actions

- Add non-prod synthetic probes for critical `/api/*` endpoints with per-endpoint `502` ratio tracking.
- Gate releases on proxy policy conformance and environment alias completeness checks.
- Track weekly trend of `failureKind` distribution and fallback usage to identify recurring drift.

## Escalation path and ownership

- Primary owner: Platform Engineering (incident coordination).
- Secondary owner: Frontend platform (UI runtime configuration).
- Upstream owner: API/agent domain team when `failureKind=upstream` dominates.

Escalate to Sev2 when:

- Critical threshold is breached for >15 minutes, or
- More than two critical endpoint groups are impacted simultaneously.

## Implementation snippets (KQL templates)

Use these as templates in Application Insights / Log Analytics, adapting table names to deployed schema.

```kusto
let lookback = 15m;
requests
| where timestamp > ago(lookback)
| where url has "/api/"
| extend status = tostring(resultCode)
| extend failureKind = tostring(customDimensions.failureKind)
| extend upstreamPath = tostring(customDimensions.upstreamPath)
| extend sourceKey = tostring(customDimensions.sourceKey)
| extend fallbackUsed = tostring(customDimensions.fallbackUsed)
| summarize total=count(), failures=countif(status == "502") by upstreamPath, failureKind, sourceKey, fallbackUsed
| extend failureRate = iff(total == 0, 0.0, todouble(failures) / todouble(total))
| order by failures desc
```

```kusto
let lookback = 30m;
requests
| where timestamp > ago(lookback)
| where url has "/api/"
| extend upstreamPath = tostring(customDimensions.upstreamPath)
| extend fallbackUsed = tostring(customDimensions.fallbackUsed)
| summarize requests=count(), fallbackCount=countif(fallbackUsed == "true") by upstreamPath, bin(timestamp, 5m)
| order by timestamp desc
```

## Non-prod verification plan

Run the following controlled tests in `dev` before promoting alert rules:

1. Config failure injection.
   - Remove proxy env aliases and call a critical endpoint.
   - Verify `failureKind=config` and `status=502` telemetry.
2. Policy failure injection.
   - Point proxy target to non-APIM URL with policy override disabled.
   - Verify `failureKind=policy` and threshold behavior under repeated traffic.
3. Network failure injection.
   - Apply temporary egress deny from UI runtime to APIM or force a stalled upstream response beyond the 10 second catalog-read timeout.
   - Verify `failureKind=network` and critical alert trigger timing.
4. Upstream failure injection.
   - Force APIM/backend to return `502` on one critical endpoint.
   - Verify `failureKind=upstream`, `upstreamStatus=502`, and escalation routing.
5. Fallback verification.
   - Force fallback-enabled route upstream `404/5xx`.
   - Verify success response with fallback marker and no false `502` paging.
