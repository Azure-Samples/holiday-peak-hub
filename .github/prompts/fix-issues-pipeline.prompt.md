---
name: "Fix Issues Pipeline"
description: "End-to-end issue resolution: deep investigation, coordinated fix, GitHub issue creation, branch, PR, merge, and cleanup."
agent: "TechLeadOrchestrator"
argument-hint: "Describe the problem: error messages, logs, symptoms, affected services, or paste a screenshot. Include any reproduction steps or environment details."
---

Investigate and resolve the described issue through a fully tracked GitHub workflow. Every fix must be persisted via issue, branch, PR, merge, and cleanup.

## Phase 1: Deep Investigation

1. **Symptom Capture** — Restate the problem clearly:
   - What is broken? What is the expected vs. actual behavior?
   - Which services, endpoints, or components are affected?
   - User impact severity: P1 (outage), P2 (degraded), P3 (cosmetic), P4 (minor)

2. **Evidence Gathering** — Use workspace tools directly to:
   - Read error logs, stack traces, and configuration files
   - Trace the code path from entry point to failure
   - Check recent changes (git log, diffs) that may have introduced the issue
   - Identify affected files, modules, and their dependencies

3. **Hypothesis Formation** — List the top 3 most likely root causes ranked by probability. For each:
   - State the hypothesis
   - Identify evidence that would confirm or refute it
   - Name the specialist agent best suited to investigate

4. **Specialist Investigation** — Invoke the appropriate agents via `#runSubagent` to confirm the root cause:
   - `PlatformEngineer` — infrastructure, CI/CD, deployment, networking, DNS, K8s, Flux, env vars
   - `PythonDeveloper` — Python stack traces, async bugs, adapter errors, SDK issues
   - `TypeScriptDeveloper` — frontend errors, API proxy issues, TypeScript type failures
   - `RustDeveloper` — Rust panics, ownership, linker, or build failures
   - `SystemArchitect` — cross-service integration failures, event flow breaks, architectural mismatches
   - Relevant Azure specialist — cloud resource health, connectivity, configuration drift

5. **Root Cause Confirmation** — Document:
   - The confirmed root cause and full causal chain
   - Why existing tests or monitoring did not catch it
   - The minimal set of changes required to fix it

## Phase 2: GitHub Issue Creation

1. **Create Issue** — Open a new GitHub issue using `gh issue create` with:
   - Title: `[Bug] <concise problem summary>`
   - Body containing:
     - **Problem**: Clear description of the failure
     - **Root Cause**: Findings from Phase 1
     - **Impact**: Severity, affected services, user impact
     - **Proposed Fix**: Summary of changes required
     - **Acceptance Criteria**: Checklist of conditions that must be true when resolved
   - Labels: `bug` and any domain-specific labels (e.g., `infrastructure`, `agent`, `frontend`)
2. **Record** the issue number for all subsequent steps.

## Phase 3: Branch & Implementation

1. **Create Branch** — From the default branch (`main`), create:
   - `bug/<issue-number>-<short-description>` (per ADR-022 branch naming convention)

2. **Implement Fix** — Delegate to the appropriate specialist agents via `#runSubagent`:

   | Change Type | Agent | Validation |
   |---|---|---|
   | Python code | `PythonDeveloper` | pytest, mypy, lint (ruff/pylint) |
   | TypeScript/React | `TypeScriptDeveloper` | tsc --noEmit, ESLint, Vitest |
   | Rust code | `RustDeveloper` | cargo check, cargo clippy, cargo test |
   | Infrastructure / CI | `PlatformEngineer` | IaC validate, actionlint, dry-run |
   | K8s manifests | `PlatformEngineer` | manifest lint, rendered manifest update |
   | UI/accessibility | `UIDesigner` | WCAG 2.2 AA audit |
   | Architecture impact | `SystemArchitect` | ADR compliance, integration contract review |

3. **Verify Fix** — Before committing:
   - Run all affected tests and confirm they pass
   - Confirm no regressions in unrelated areas
   - Verify the original failure scenario no longer reproduces

4. **Commit & Push** — Commit with a message referencing the issue:
   - Format: `fix: <description> (#<issue-number>)`
   - Push the branch to origin

## Phase 4: Pull Request

1. **Create PR** — Open a PR targeting `main` with:
   - Title matching the commit message
   - Body referencing `Closes #<issue-number>`
   - Summary of root cause, changes made, and verification steps
2. **Review Gate** — Invoke `PRReviewer` via `#runSubagent` to verify:
   - [ ] All CI checks pass
   - [ ] Test coverage is maintained or improved
   - [ ] No security regressions
   - [ ] Architecture sign-off (if cross-service changes)
   - [ ] Acceptance criteria from the issue are satisfied

## Phase 5: Merge, Close & Cleanup

1. **Merge** — Once the PR is approved and all checks pass:
   - Squash-merge into `main`
   - Ensure the merge commit references the issue

2. **Post-Merge Verification** — Invoke `PlatformEngineer` via `#runSubagent` to:
   - Confirm the deployment pipeline picks up the change (Flux reconciliation, CI/CD)
   - Verify health checks pass with the fix applied
   - Confirm the original failure no longer reproduces in the live environment

3. **Close Issue** — Close the GitHub issue with a resolution comment:
   - Link to the merged PR
   - Confirmation that the fix is deployed and verified
   - Any follow-up items or monitoring recommendations

4. **Delete Branch** — Remove the feature branch after merge:
   - `git push origin --delete bug/<issue-number>-<short-description>`

5. **Prevention** — Delegate to `PlatformEngineer` via `#runSubagent` to recommend:
   - Additional tests to prevent regression
   - Monitoring or alerting improvements
   - Documentation updates if the issue revealed a gap

## Completion Criteria

- [ ] Root cause identified and documented
- [ ] GitHub issue created with full context
- [ ] Fix implemented on a dedicated branch
- [ ] PR created, reviewed, and all checks green
- [ ] PR merged to `main`
- [ ] Issue closed with resolution comment
- [ ] Branch deleted
- [ ] Post-merge verification confirms fix in production
- [ ] Prevention recommendations delivered
