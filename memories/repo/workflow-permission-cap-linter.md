# Workflow permission-cap linter (`scripts/ci/lint_workflow_permissions.py`)

## What it enforces
GitHub Actions rule: in a `workflow_call` chain, callee permissions can only be **maintained or reduced** by the caller. Violations → `startup_failure` before runner allocation.

## How effective permissions are computed (CRITICAL)
For each callee job, effective permissions = **per-job `permissions:` if present, else workflow-level `permissions:`**. The linter MUST seed the required-set from callee workflow-level perms; per-job maps override per-key. This was missing pre-PR #1100 and caused a false-negative on `deploy-azd-truth.yml`.

## Caller-side fallback
Same semantics: caller workflow-level `permissions:` are the fallback for jobs that omit `permissions:`. Already implemented.

## Failure mode if you miss the fallback
- Linter passes locally + in PR CI
- GitHub orchestrator rejects with `startup_failure` (7s run, no logs)
- Looks identical to a transient queue issue
- PR #1097 → 2 days undetected → issue #1099

## Tests
`scripts/ci/tests/test_lint_workflow_permissions.py` — 5 cases:
1. Caller grants required perms → pass
2. Caller missing `pull-requests: write` (PR #1097 regression) → flag
3. Caller `contents: read` vs callee per-job `contents: write` → flag
4. Callee with no per-job perms → pass
5. **Callee workflow-level `contents: write` (no per-job override), caller `contents: read` → flag** ← prevents recurrence of deploy-azd-truth.yml class

## Operational notes
- Required check `Permission-cap lint (cross-file nested-workflow rule)` in `.github/workflows/lint-actions.yml`
- Emits `::error file=...::` GitHub annotations, exit 1 on violation
- `actionlint` used with `-shellcheck=` to disable shellcheck (catches unrelated pre-existing SC2034/SC2129/SC2153)
