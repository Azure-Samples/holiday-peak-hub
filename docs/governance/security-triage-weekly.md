# Weekly Security Triage Report

**Owner**: Platform Engineering  
**Cadence**: Weekly (Monday)  
**Last Updated**: 2026-04-30

## Severity Burn-down

| Week | Dependabot High | CodeQL High | Total High | Target High |
| --- | --- | --- | --- | --- |
| 2026-04-02 | 6 | 3 | 9 | 0 |

## Resolved Alert Evidence

| Week | Alert | Resolution PR | Validation |
| --- | --- | --- | --- |
| 2026-04-02 | Pending first wave after grouped dependency policy merge | TBC | TBC |

## Weekly Update Procedure

- Query alert counts:

```bash
gh api --paginate repos/Azure-Samples/holiday-peak-hub/dependabot/alerts?state=open --jq '.[].security_advisory.severity'
gh api --paginate repos/Azure-Samples/holiday-peak-hub/code-scanning/alerts?state=open --jq '.[].rule.security_severity_level'
```

- Update the `Severity Burn-down` and `Resolved Alert Evidence` tables.
- Link each resolved alert to a merged PR and validation output.
- Carry forward any unresolved high alerts in docs/governance/security-exception-register.md with owner and expiry.
