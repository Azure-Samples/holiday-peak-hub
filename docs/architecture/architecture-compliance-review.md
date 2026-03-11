# Architecture Compliance Review (Branch)

**Branch**: `chore/999-deploy-pipeline-followup`  
**Date**: 2026-03-11  
**Reviewer**: Architecture pass (Copilot)

## Scope

- ADR conformance checks for deployment, branching, resilience, adapter boundaries, and truth-layer architecture
- Architecture documentation consistency (canonical vs duplicated docs)
- Operational playbook coverage against governance policies
- Pipeline policy alignment in GitHub Actions workflows

## ADR Conformance Matrix

| ADR | Expected Rule | Current State | Result | Notes |
|---|---|---|---|---|
| ADR-021 | `azd`-first deployment with ordered orchestration | `deploy-azd-dev.yml` and `deploy-azd-prod.yml` call reusable `deploy-azd.yml` | ✅ | Entrypoint model is aligned; reusable workflow is used as engine |
| ADR-021 | OIDC-based Azure auth | `deploy-azd.yml` uses `azure/login@v2` and federated `azd auth login` | ✅ | No static Azure credential secret usage |
| ADR-021 | CRUD-first then agent deployment | Reusable deploy pipeline contains staged jobs and changed-service detection | ✅ | Ordered deployment intent preserved |
| ADR-022 | Branch naming `<prefix>/<issue>-<description>` | Branch `chore/999-deploy-pipeline-followup` | ✅ | Prefix and issue-id rule compliant |
| ADR-023 | Circuit breaker + bulkhead + rate limiter for integrations | Patterns documented in architecture and implemented in framework utilities | ✅ | Playbooks include operational handling for failures and latency |
| ADR-025 | Product Truth Layer with HITL and writeback | Truth services and docs present (`truth-ingestion`, `truth-hitl`, `truth-export`) | ✅ | Architecture docs updated to canonical service names |

## Policy Conformance Findings

### Deployment policy

- ✅ Dev/prod entrypoint split is implemented (`deploy-azd-dev.yml`, `deploy-azd-prod.yml`)
- ✅ Prod pipeline includes release and lineage gates
- ✅ Reusable core workflow remains parameterized for environment-specific deployments
- ⚠️ `deploy-azd.yml` contains repeated setup blocks (duplicate `kubelogin` and env setup sections); this does not break policy but increases maintenance risk

### Architecture documentation quality

- ✅ Canonical architecture sources retained (`architecture.md`, `components.md`, `ADRs.md`, `diagrams/`)
- ✅ Duplicated implementation narratives removed from `docs/architecture` root
- ✅ References updated to component-level docs for CRUD and frontend details
- ✅ Broken operations reference covered with an explicit incident response playbook

### Playbooks vs governance

- ✅ Existing playbooks use common triage/mitigation/prevention structure
- ✅ Added explicit severity, ownership, and escalation workflow via incident-response baseline
- ✅ Index now identifies required metadata and execution expectations

## Actions Applied in This Review

1. Consolidated architecture root documentation to canonical sources.
2. Added this compliance review as an auditable architecture artifact.
3. Tightened playbook index and created baseline incident response playbook.
4. Removed redundant architecture files that replicated canonical content.
5. Updated references in docs to preserve navigation after consolidation.

## Recommended Follow-ups

1. Refactor duplicated sections inside `.github/workflows/deploy-azd.yml` into a single setup block.
2. Add a CI docs-link checker for `docs/**` to prevent future broken references.
3. Add a quarterly architecture conformance checklist update tied to ADR revisions.
