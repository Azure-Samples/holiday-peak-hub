# Security Exception Register

**Owner**: Platform Engineering  
**Last Updated**: 2026-04-30

This register is the time-boxed exception ledger for open high-severity security alerts that are not yet closed at merge time.

## Open High-Severity Exceptions

| Alert(s) | Source | Component | Mitigation Plan | Owner | Expiry |
| --- | --- | --- | --- | --- | --- |
| CodeQL #10, #11 | Code scanning | apps/ui/lib/services/semanticSearchService.ts | Hostname validation remediation merged; post-merge CodeQL scan confirmed closure. | UI Platform Team | ~~2026-04-16~~ Resolved |
| CodeQL #12 | Code scanning | apps/ui/lib/hooks/useIntelligentSearch.ts | Secure randomness fallback remediation merged; post-merge CodeQL scan confirmed closure. | UI Platform Team | ~~2026-04-16~~ Resolved |
| Dependabot #412 | Dependabot | apps/ui/yarn.lock (lodash) | Resolve via grouped UI dependency update policy and verify with dependency-audit workflow evidence. | Frontend Maintainers | 2026-04-30 <!-- TODO: verify current Dependabot status --> |
| Dependabot #22 | Dependabot | apps/ui/yarn.lock (flatted) | Resolve via grouped UI dependency update policy and verify with dependency-audit workflow evidence. | Frontend Maintainers | 2026-04-30 <!-- TODO: verify current Dependabot status --> |
| Dependabot #17, #18, #19 | Dependabot | apps/ui/yarn.lock (minimatch) | Resolve via grouped UI dependency update policy and verify with dependency-audit workflow evidence. | Frontend Maintainers | 2026-04-30 <!-- TODO: verify current Dependabot status --> |
| Dependabot #7 | Dependabot | apps/crud-service/src/uv.lock (ecdsa) | Track upstream fix availability; keep exception until patched release is available and validated. | Platform Engineering | 2026-06-30 |

## Evidence Commands

```bash
gh api --paginate repos/Azure-Samples/holiday-peak-hub/dependabot/alerts?state=open&severity=high
gh api --paginate repos/Azure-Samples/holiday-peak-hub/code-scanning/alerts?state=open&severity=high
```
