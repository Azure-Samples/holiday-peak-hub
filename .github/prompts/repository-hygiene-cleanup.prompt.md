---
name: "Repository Hygiene Cleanup"
description: "Execute repository hygiene: snapshot work queues, close only incorporated PRs/issues with evidence, prune eligible branches, verify clean state."
agent: "TechLeadOrchestrator"
argument-hint: "Optionally specify which steps to run (e.g. 'incorporated issues only', 'branches only') or say 'full cleanup' for the complete runbook."
---

Execute the repository hygiene cleanup runbook defined in `docs/governance/repository-hygiene-cleanup.md`.

Important: this workflow does **not** bulk-abandon work. A PR or Issue may be closed only when its change/report is already incorporated into `main`, superseded by incorporated work, or explicitly abandoned by the maintainer with evidence recorded in the closure comment.

## Pre-flight

1. Read the canonical runbook at `docs/governance/repository-hygiene-cleanup.md` for the authoritative procedure.
2. Confirm the local checkout is on `main` and up to date with `origin/main`.
3. Verify `gh auth status` is authenticated.

## Execution

Follow the runbook steps in order:

1. **Snapshot** — Capture open PRs and Issues (`gh pr list`, `gh issue list`) as audit evidence.
2. **Classify incorporation** — For every PR/Issue, verify whether the work is already represented in `main` and capture the evidence.
3. **Close PRs** — Close only PRs with no effective diff, PRs superseded by incorporated work, or PRs explicitly abandoned by the maintainer. Use an evidence comment. Use `--delete-branch` only for eligible repo-owned branches.
4. **Close Issues** — Close only Issues whose acceptance criteria are incorporated into `main`, superseded by incorporated work, or explicitly abandoned by the maintainer. Use an evidence comment; reserve `--reason "not planned"` for abandoned or obsolete work.
5. **Prune local branches** — Delete local branches except `main` only after confirming their work is merged, incorporated elsewhere, or explicitly abandoned. Preserve dirty local work before switching branches.
6. **Prune remote branches** — Delete eligible remote branches except `origin/main`. Skip branches from external forks and non-target remotes.
7. **Verification** — Confirm final local branches, target remote branches, open PRs, and open Issues. Open PRs/issues may remain if they are not yet incorporated into `main`.

## Safety

- Ask for explicit confirmation before closing Issues, closing PRs, or deleting branches.
- If any open PR has a non-empty diff against `main`, do not close it as incorporated. If CI is passing and the change is desired, flag it as merge-first.
- If an Issue is only partially scaffolded or documented as future/preview work, do not close it as incorporated.
- Keep the Step 1 snapshot available for rollback reference.

## Post-cleanup

Report a summary table with counts: PRs closed with incorporation evidence, Issues closed with incorporation evidence, PRs/Issues left open, local branches deleted, remote branches deleted, and final verification status.
