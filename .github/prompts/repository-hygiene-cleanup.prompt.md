---
name: "Repository Hygiene Cleanup"
description: "Execute full repository hygiene: snapshot work queues, close stale PRs/issues, prune local and remote branches, verify clean state."
agent: "TechLeadOrchestrator"
argument-hint: "Optionally specify which steps to run (e.g. 'PRs only', 'branches only') or say 'full cleanup' for the complete runbook."
---

Execute the repository hygiene cleanup runbook defined in `docs/governance/repository-hygiene-cleanup.md`.

## Pre-flight

1. Read the canonical runbook at `docs/governance/repository-hygiene-cleanup.md` for the authoritative procedure.
2. Confirm the local checkout is on `main` and up to date with `origin/main`.
3. Verify `gh auth status` is authenticated.

## Execution

Follow the runbook steps in order:

1. **Snapshot** — Capture open PRs and Issues (`gh pr list`, `gh issue list`) as audit evidence.
2. **Close PRs** — Close all open PRs with a hygiene comment. Use `--delete-branch` for PRs owned by this repo.
3. **Close Issues** — Close all open Issues with `--reason "not planned"` and a hygiene comment.
4. **Prune local branches** — Delete every local branch except `main`.
5. **Prune remote branches** — Delete every remote branch except `origin/main`. Skip branches from external forks.
6. **Verification** — Confirm: local branches = `main` only, remote branches = `origin/main` only, open PRs = 0, open Issues = 0.

## Safety

- Ask for explicit confirmation before closing Issues (PRs are lower risk since branches are ephemeral).
- If any open PR has CI passing and is ready to merge, flag it for merge-first before closing.
- Keep the Step 1 snapshot available for rollback reference.

## Post-cleanup

Report a summary table with counts: PRs closed, Issues closed, local branches deleted, remote branches deleted, final verification status.
