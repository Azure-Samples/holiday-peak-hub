# Wave0 Dependency Audit Remediation

**Issue**: [#372](https://github.com/Azure-Samples/holiday-peak-hub/issues/372)  
**Owner**: Platform Quality / Platform Engineering  
**Last Updated**: 2026-04-30

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
- Added frontend dependency coverage in `.github/workflows/dependency-audit.yml` via `yarn audit --level high` in `apps/ui`.
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
2. Keep dependency-audit workflow enabled as a PR gate recommendation for `main` branch governance (Python + frontend).

## Dependabot Throughput Policy (Issue #609)

### Grouping and PR cap

- Dependabot is configured to use grouped `uv` updates across `/lib/src` and `/apps/*/src` with `group-by: dependency-name`.
- Dependabot open version-update pull requests are capped (`uv`: 12, `npm`: 6) to prevent queue saturation.

### Safe auto-merge policy

- Eligible: patch/minor dependency updates with green `lint`, `test`, and `dependency-audit` checks.
- Excluded: major version updates, security exceptions, and dependency updates that require manual migration steps.
- Required traceability: merged dependency PRs must include test evidence in the PR body.

### Backlog target and monitoring

- Baseline open Dependabot PRs (2026-04-02): `39`.
- Current open Dependabot PRs (post-policy cleanup, 2026-04-02): `0`.
- Target backlog: `<= 12` open Dependabot PRs (sustained cap).
- Weekly monitoring command:

```bash
gh pr list --state open --author app/dependabot --limit 200 --json number --jq 'length'
```
