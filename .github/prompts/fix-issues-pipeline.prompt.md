---
name: "Fix Issues Pipeline"
description: "End-to-end issue fix pipeline: deep investigation with specialist agents, GitHub issue creation, branch + PR workflow, merge monitoring, and cleanup."
agent: "TechLeadOrchestrator"
argument-hint: "Describe the problem: symptoms, error messages, affected components, reproduction steps, and any logs or screenshots."
---

Run the full fix-issues pipeline for the described problem:

## Phase 1 — Deep Investigation

1. **Symptom Analysis** — Restate the problem clearly. Identify affected components, user impact, and severity.

2. **Hypothesis Formation** — List the top 3 most likely root causes ranked by probability.

3. **Evidence Gathering** — For each hypothesis, invoke the appropriate specialist via `#runSubagent`:
   - `PlatformEngineer` — CI/CD failures, infrastructure, environment, dependency, and deployment issues (invoke first for platform-related symptoms)
   - `PythonDeveloper` — Python stack traces, async bugs, type errors, test failures
   - `RustDeveloper` — Rust panics, ownership issues, compilation failures
   - `TypeScriptDeveloper` — TypeScript type errors, React rendering, bundle or build issues
   - `SystemArchitect` — cross-service integration failures, architectural mismatches, data flow issues
   - `UIDesigner` — UI rendering, accessibility regressions, layout/styling issues

4. **Root Cause Isolation** — Narrow to the confirmed root cause. Document the full causal chain with file/function evidence.

5. **Fix Design** — Decompose the fix into agent-assignable tasks with clear scope, acceptance criteria, and dependencies.

## Phase 2 — GitHub Issue Creation

6. **Open a GitHub Issue** describing the confirmed problem:
   - **Title**: concise summary of the root cause
   - **Body** must include:
     - Problem statement with evidence from Phase 1
     - Root cause analysis summary
     - Acceptance criteria checklist (each criterion independently verifiable)
     - Affected files and components
     - Risks and dependencies
   - Apply appropriate labels (e.g., `bug`, `fix`, affected service names)

## Phase 3 — Branch, Implement, and PR

7. **Create a Fix Branch** from `main`:
   - Follow repository branch naming convention: `bug/<issue-number>-<short-description>`
   - Keep the branch scoped exclusively to the issue

8. **Implement the Fix** — Delegate each sub-task to the appropriate specialist via `#runSubagent`:
   - `PlatformEngineer` for CI/CD, infra, or environment fixes
   - `PythonDeveloper` for Python code and test fixes
   - `RustDeveloper` for Rust code fixes
   - `TypeScriptDeveloper` for TypeScript/React fixes
   - `UIDesigner` for UI/accessibility fixes
   - Ensure every change includes or updates unit and integration tests
   - Run tests locally to confirm the fix before committing

9. **Commit and Push** — Stage, commit with a descriptive message referencing the issue (`Fixes #<number>`), and push the branch.

10. **Open a Pull Request** targeting `main`:
    - Title references the issue number
    - Description links back to the issue and summarizes changes
    - Include verification evidence (test results, before/after comparison)

## Phase 4 — Validation and Merge

11. **PR Validation** — Monitor CI checks and review feedback:
    - If checks fail, diagnose and apply fixes in the same branch
    - Re-push and re-validate until all checks pass
    - Invoke `PlatformEngineer` via `#runSubagent` for CI/infrastructure failures

12. **Merge to Main** — Once all checks pass and the PR is approved, merge using the repository merge strategy.

13. **Post-Merge Monitoring** — Watch post-merge workflows and deployments:
    - If regressions appear, open follow-up fixes in the same pipeline
    - Confirm the fix is live and the original problem is resolved

## Phase 5 — Cleanup

14. **Close the Issue** — Close the GitHub issue with merge evidence (PR link, commit SHA).

15. **Delete the Remote Branch** — Remove the merged fix branch from the remote.

16. **Local Cleanup** — Switch to `main`, pull latest, delete the local branch, and confirm `git status` is clean.

## Delivery

Produce a final execution report containing:

| Section | Content |
|---------|---------|
| **Root Cause** | Confirmed cause with evidence chain |
| **Issue** | GitHub issue number and link |
| **Branch** | Branch name used |
| **PR** | PR number, link, and merge status |
| **Tests** | Test results and coverage evidence |
| **Monitoring** | Post-merge workflow/deployment status |
| **Cleanup** | Branch deletion and issue closure confirmation |
