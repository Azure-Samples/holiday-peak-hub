# holiday-peak-hub — PR Review & Release Engineering Context

Consumed by: **The Gatekeeper** (`pr-evaluator.agent.md`)
Repository: `holiday-peak-hub`

---

## Coordination with Architecture_Patterns Agent

Every PR closure MUST involve the Architecture_Patterns agent. This is non-negotiable.

### Handoff Protocol

1. **Before approving any PR**, invoke or defer to the `Architecture_Patterns` agent to validate:
   - Adherence to ADRs (Architecture Decision Records) in `docs/architecture/adrs/`
   - Correct use of `BaseAdapter`, `BaseRetailAgent`, `AgentBuilder` patterns
   - Event-driven patterns follow ADR-005 and ADR-007 (Saga/Choreography)
   - Connector patterns follow ADR-024 (Connector Registry)
   - Memory tier usage follows ADR-008 and ADR-014
   - MCP tool exposition follows ADR-010
   - Data enrichment guardrails are enforced (no AI-generated content without source data)

2. **Architecture_Patterns agent must confirm**:
   - [ ] No architectural regressions introduced
   - [ ] New patterns align with existing ADRs or propose new ones
   - [ ] Inter-service contracts are preserved
   - [ ] Event schemas maintain backward compatibility

3. **If the Architecture_Patterns agent raises concerns**, the PR MUST NOT be merged until:
   - The concerns are addressed in code
   - The Architecture_Patterns agent re-reviews and approves
   - All updated code passes CI/CD checks again

### Joint Review Checklist

| Area | Reviewer | Criteria |
|------|----------|----------|
| Architecture patterns | Architecture_Patterns agent | ADR compliance, pattern integrity |
| API contracts & schemas | Architecture_Patterns agent | Backward-compatible changes only |
| CI/CD pipeline safety | PR_Evaluation agent | All workflows pass, no regressions |
| Plan fulfillment | PR_Evaluation agent | All tasks from the issue are implemented |
| Test coverage | PR_Evaluation agent | Minimum 75% coverage, no masked failures |
| Merge strategy | PR_Evaluation agent | Safe merge, no force-push, squash when appropriate |

---

## PR Diff Categorization

Categorize changes by domain when reviewing diffs:

| Path pattern | Category | Impact level |
|---|---|---|
| `lib/src/holiday_peak_lib/` | Library changes | Framework-level, high |
| `apps/*/` | App changes | Service-level, medium |
| `.infra/`, `azure.yaml` | Infrastructure changes | Deployment-level, high |
| `.github/workflows/` | CI/CD changes | Pipeline-level, critical |
| `docs/` | Documentation changes | Low but required |
| `*/tests/` | Test changes | Quality-level, required |
| `pyproject.toml`, `*.yml` | Configuration changes | Dependency-level, medium |

---

## CI/CD Workflow Inventory

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **test** | `.github/workflows/test.yml` | push, pull_request | Runs pytest for lib + all apps |
| **lint** | `.github/workflows/lint.yml` | push, pull_request | isort, black, pylint checks |
| **build-push** | `.github/workflows/ci.yml` | push to main | Builds + pushes Docker images to GHCR |
| **deploy-azd** | `.github/workflows/deploy-azd.yml` | workflow_dispatch | Full Azure deployment via azd |
| **deploy-ui-swa** | `.github/workflows/deploy-ui-swa.yml` | workflow_dispatch | UI-only SWA deployment |
| **codeql** | `.github/workflows/codeql.yml` | — | Security analysis |

### Test Pipeline Verification Commands

```bash
# Python Tests (test.yml)
cd lib && pytest tests/ --maxfail=1
pytest apps/*/tests --ignore=apps/ui/tests

# Lint Pipeline (lint.yml)
python -m isort --check-only lib apps
python -m black --check lib apps
python -m pylint lib/src apps/*/src
```

---

## Backward Compatibility — Dependency Chain

```
lib/src/holiday_peak_lib/ → All apps depend on this
apps/crud-service/ → Central hub, other apps may call its REST endpoints
apps/*-agent/ → Agent services, consume lib + adapters
apps/ui/ → Frontend, calls CRUD + agent REST endpoints
```

If `lib/` changes:
- ALL app tests must be re-run
- ALL Docker builds must be verified
- Check that no app imports modules that were renamed/removed

If `apps/crud-service/` changes:
- Verify REST endpoint contracts are preserved
- Verify Event Hub publishing patterns are maintained
- Check downstream agent consumers are compatible

---

## Code Quality Standards

### Python
- PEP 8 compliance — strictly enforced
- Type hints — all public functions typed
- Async patterns — all I/O operations use `async/await`
- Pydantic v2 — models use `ConfigDict` style, not legacy `class Config`
- No `|| true` in CI or test scripts — failures must surface

### Testing
- Unit tests exist for all new functions/classes
- pytest-asyncio used for async test functions
- Mocks used appropriately (no real API calls in unit tests)
- Coverage meets 75% target for changed files
- No test masking — assert statements are meaningful, not `assert True`

### Documentation
- New features documented in `docs/`
- ADRs created for significant architectural decisions
- README updates if public interface changed
- Inline comments only where logic is non-obvious

### Security Review
- No secrets or credentials in code
- Environment variables used for sensitive configuration
- Input validation on all API endpoints
- No SQL injection, XSS, or SSRF vulnerabilities
- Dependencies are up-to-date and have no known CVEs

---

## Merge Strategy

| Scenario | Strategy | Rationale |
|----------|----------|-----------|
| Single coherent feature | Squash and merge | Clean commit history on main |
| Multiple logical commits | Merge commit | Preserve commit granularity |
| Hotfix / single-line fix | Rebase and merge | Linear history |

Default: **Squash and merge** (preferred for feature branches).

### Branch Naming Convention
Follows ADR-022 pattern. Branches are ephemeral — delete after merge.
