# Governance and Compliance Guidelines

**Version**: 2.1
**Last Updated**: 2026-04-06
**Owner**: Architecture Team

## Overview

This folder is the governance source of truth for engineering standards, runtime controls, and deployment policy.

## Governance Documents

### [Frontend Governance](frontend-governance.md)
**Audience**: Frontend engineers  
**Scope**: Next.js, React, TypeScript, ESLint, security, performance

### [Backend Governance](backend-governance.md)
**Audience**: Backend/API/Agent engineers  
**Scope**: Python/FastAPI, agent patterns, adapters, memory, testing

### [Infrastructure Governance](infrastructure-governance.md)
**Audience**: DevOps/SRE/Cloud engineers  
**Scope**: Azure IaC, AKS/SWA deployment, CI/CD and environment gates

### [Wave0 Dependency Audit](dependency-audit-wave0.md)
**Audience**: Platform/DevSecOps engineers  
**Scope**: pip-audit baseline evidence, remediation status, and vulnerability exception tracking

### [Repository Hygiene Cleanup Runbook](repository-hygiene-cleanup.md)
**Audience**: Repository maintainers and admins  
**Scope**: Issue/PR cleanup operations and branch pruning to main-only

### [Security Exception Register](security-exception-register.md)
**Audience**: Platform/DevSecOps engineers  
**Scope**: Time-boxed exception records for unresolved high-severity alerts with owner/expiry tracking

### [Weekly Security Triage Report](security-triage-weekly.md)
**Audience**: Platform/DevSecOps engineers  
**Scope**: Weekly high-severity burn-down metrics and resolution evidence links

## Repository Source-of-Truth Map

| Governance topic | Canonical source | Notes |
| --- | --- | --- |
| Governance policy baseline | `docs/governance/README.md` | This index and enforcement model |
| Hygiene cleanup operations | `docs/governance/repository-hygiene-cleanup.md` | Runbook for issue/PR backlog reset and branch pruning |
| Frontend standards | `docs/governance/frontend-governance.md` | UI/runtime coding and quality rules |
| Backend/agent standards | `docs/governance/backend-governance.md` | API/agent architecture and test rules |
| Infrastructure/deployment policy | `docs/governance/infrastructure-governance.md` | IaC, pipeline, and runtime deployment controls |
| Architecture entrypoint | `docs/architecture/README.md` | Architecture navigation and design artifacts |
| Operational documentation index | `docs/README.md` | Cross-domain docs catalog and navigation |
| Agent registry map | `.github/agents/data/team-mapping.md` | Canonical registry for available specialist agents |

## Code-Aligned Baselines

- **Python baseline**: 3.13+ (`lib/src/pyproject.toml`, app `src/pyproject.toml` files)
- **Frontend baseline**: Next.js 16 canary + React 19 + TypeScript strict (`apps/ui/package.json`, `apps/ui/tsconfig.json`)
- **Lint/format baseline (backend)**: `pylint`, `black`, `isort` (`pyproject.toml`)
- **Lint baseline (frontend)**: ESLint 8 (`apps/ui/.eslintrc.json`)
- **Coverage baseline**: 75% repo minimum; package-level stricter thresholds allowed (some modules enforce 80%)

## Environment Policy Summary

Detailed policy is defined in [Infrastructure Governance](infrastructure-governance.md#environment-policy-matrix).

- **dev**: `deploy-azd-dev.yml` (main push + manual dispatch)
- **dev protected live validation**: `protected-dev-live-agent-readiness.yml` (trusted `workflow_run` after successful dev deploy on `main`, plus manual dispatch and schedule; uses the `dev` GitHub Environment boundary for environment-scoped OIDC inputs)
- **prod**: `deploy-azd-prod.yml` (stable tag only, release + lineage gates)
- **staging**: reserved for future environment expansion; currently no dedicated entrypoint workflow

## Protected Live Validation Policy

- `.github/workflows/protected-dev-live-agent-readiness.yml` is the only approved privileged live validation workflow for the dev environment.
- The workflow is bound to the GitHub Environment `dev` with environment-scoped `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID` values for Azure OIDC login.
- Allowed triggers are `workflow_run` after successful `deploy-azd-dev (entrypoint)` runs on `main`, `workflow_dispatch`, and `schedule`.
- Repository code establishes the privileged workflow and environment-scoped secret boundary. The `dev` environment must remain configured with selected-branch deployment protection on `main`.
- The workflow must not run on `pull_request`, `pull_request_target`, or other untrusted contributor contexts because it reaches live Azure resources behind a privileged environment boundary.

## Enforcement Model

### Automated

- PR/build automation via GitHub Actions workflows under `.github/workflows/`
- Deployment gates via `deploy-azd-dev.yml`, `deploy-azd-prod.yml`, and reusable `deploy-azd.yml`
- Protected dev live validation via `protected-dev-live-agent-readiness.yml` using the `dev` environment boundary and OIDC-only Azure auth
- Weekly security burn-down artifact via `security-triage-report.yml`
- Lint/test tasks exposed in workspace (`lint`, `format`, `test`)

### Manual

- Architecture review for ADR-impacting changes
- Security/compliance review for identity, secrets, and data-access changes
- Post-incident review for Sev1/Sev2 issues

## Main Branch Protection Policy

`main` is PR-only and must not accept direct pushes from standard contributor or automation paths.

- Require pull request before merge
- Require conversation resolution (approval count is configurable; currently set to 0 for solo maintainer mode)
- Require strict required checks (branch up-to-date + named required checks)
- Minimize bypass actors to explicit break-glass identities only
- Revalidate protections after any GitHub ruleset/permission change

### Required checks baseline for `main`

- Required checks should be limited to `lint` and `test` in strict mode to reduce merge queue pressure while preserving core quality gates.
- Additional workflows (for example CodeQL and non-blocking governance audits) remain recommended but should not be configured as required merge checks unless explicitly approved.
- `protected-dev-live-agent-readiness` is an operational workflow with privileged environment access and must not be configured as a required PR or merge-queue check.

## Verification Procedure (PR-only governance)

Use both checks below for governance hardening and drift detection:

1. Docs reference validation (local + CI)
	- `python scripts/ops/check_markdown_links.py --roots docs/governance docs/architecture/README.md`
	- Fails on unresolved internal markdown links in governance docs and architecture entrypoint docs.
	- `grep -RInE "OPERATIONAL-WORKFLOWS\.md|REPOSITORY-SURFACES\.md|governance-map\.md" .github/agents`
	- CI fails if stale canonical governance reference tokens appear in tracked agent docs.

2. Main protection audit (manual/CI)
	- `python scripts/ops/audit_main_governance.py --repo <owner/repo> --required-check lint --required-check test --min-approvals 0 --require-conversation-resolution`
	- Validates PR-only controls for `main`:
	  - pull request rule present
	  - configured minimum required approvals (currently 0 for solo maintainer mode)
	  - conversation resolution required
	  - required status checks configured in strict mode
	  - force pushes blocked
	  - branch deletion blocked
	  - bypass actors minimized to explicit allowlist

#### Admin enforcement command (GitHub API)

For repositories using branch protection (instead of organization-level rulesets), an admin can enforce the baseline with:

`gh api -X PUT repos/<owner>/<repo>/branches/main/protection -H "Accept: application/vnd.github+json" --input <payload.json>`

Where `<payload.json>` sets strict required checks to `lint` and `test` and keeps PR-only protections enabled.

### Current External Governance Gap

- Ruleset/protection enforcement itself is controlled by repository admin permissions and cannot be remediated by branch code changes alone.
- If audit fails because no active `main` ruleset/protection exists, treat as an external admin blocker and attach audit output as evidence in issue/PR records.

### Validation Evidence

For governance hardening changes, capture and retain:

- Failed direct push attempt to `main`
- Failed non-exempt automation direct update to `main`
- Successful merge through fully gated PR path

## Related Architecture References

- [Architecture Overview](../architecture/architecture.md)
- [ADR Index](../architecture/ADRs.md)
- [Architecture Compliance Review](../architecture/architecture-compliance-review.md)
- [Operational Playbooks](../architecture/playbooks/README.md)

## Governance Principles

1. **Secure by default** (OIDC, Key Vault, least privilege)
2. **Deploy by policy** (environment-gated workflows)
3. **Document what is enforced** (code and docs stay aligned)
4. **Favor automation over convention**
5. **Continuously reconcile drift between docs and implementation**
