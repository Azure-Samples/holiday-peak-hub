# Incident Response Baseline

## Purpose

Defines the minimum operational response standard for all Holiday Peak Hub incidents.

## Severity Levels

| Severity | Description | Target Initial Response |
|---|---|---|
| Sev 1 | Production outage or critical customer-impacting failure | 15 minutes |
| Sev 2 | Major degradation with workaround available | 30 minutes |
| Sev 3 | Localized issue or non-critical degradation | 4 hours |
| Sev 4 | Low-priority defect or documentation/process issue | 1 business day |

## Roles

- **Incident Commander (IC)**: Owns coordination and decision flow
- **Service Owner**: Owns technical diagnosis and mitigation
- **Communications Owner**: Publishes status updates
- **Scribe**: Captures timeline, actions, and decisions

## Standard Flow

1. **Declare incident** with severity and impacted scope.
2. **Create timeline** with first detection timestamp and triggering signal.
3. **Contain impact** (degrade gracefully, disable non-critical paths, rollback as needed).
4. **Mitigate and verify** technical fix using production-safe checks.
5. **Communicate status** at fixed cadence until recovery is confirmed.
6. **Close incident** only after recovery metrics stabilize.
7. **Publish post-incident review** with root cause and preventive actions.

## Communication Cadence

- **Sev 1**: every 15 minutes
- **Sev 2**: every 30 minutes
- **Sev 3/4**: at major milestone updates

## Required Artifacts

- Incident title and unique identifier
- Start/end timestamps (UTC)
- Impacted services and customer impact statement
- Root cause summary
- Corrective actions with owners and due dates

## Escalation Rules

- Escalate to platform and architecture leads when:
  - SLA/SLO breach is likely
  - data integrity is at risk
  - repeated incident pattern is detected

## Links

- Architecture playbooks index: `docs/architecture/playbooks/README.md`
- Architecture compliance review: `docs/architecture/architecture-compliance-review.md`
- Governance overview: `docs/governance/README.md`
