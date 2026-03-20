# Wave0 Dependency Audit Remediation

**Issue**: [#372](https://github.com/Azure-Samples/holiday-peak-hub/issues/372)  
**Owner**: Platform Quality / Platform Engineering  
**Last Updated**: 2026-03-19

## Baseline Evidence

Issue baseline reproduction command:

```bash
python -m pip_audit
```

Wave0 baseline observed in issue #372:

- `15` known vulnerabilities in `12` packages
- Representative vulnerable packages: `black`, `cryptography`, `flask`, `pillow`, `urllib3`, `werkzeug`

## Remediation Applied

- Added CI workflow `.github/workflows/dependency-audit.yml` to run `pip-audit` on every PR/push to `main`.
- Updated lint toolchain minimum version to `black[jupyter]>=26.3.1` in:
  - `.github/workflows/lint.yml`
  - `lib/src/pyproject.toml`
  - `apps/crud-service/src/pyproject.toml`
- Added report artifact upload (`pip-audit-report.json`) for traceable security evidence.

## Current Scan Status

Repository-scoped clean environment scan after remediation:

- Command: `python -m pip_audit --ignore-vuln CVE-2024-23342`
- Result: `No known vulnerabilities found, 1 ignored`

## Temporary Exception Register

| Vulnerability | Package | Status | Rationale | Owner | Expiry |
| --- | --- | --- | --- | --- | --- |
| `CVE-2024-23342` | `ecdsa==0.19.1` | Temporary exception | No upstream fixed version published at audit time; transitive dependency path requires upstream release before safe upgrade. | Platform Engineering | 2026-06-30 |

## Follow-up Actions

1. Re-check `ecdsa` on each dependency audit run and remove ignore immediately when fixed version is available.
2. Keep dependency-audit workflow enabled as a PR gate recommendation for `main` branch governance.
