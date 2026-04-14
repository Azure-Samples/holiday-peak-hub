# Repository Hygiene Cleanup Runbook

**Version**: 1.0  
**Last Updated**: 2026-04-12  
**Audience**: Repository maintainers and admins

## Purpose

Use this runbook to perform repository hygiene maintenance in one controlled operation:

- Close stale or superseded GitHub Issues and Pull Requests.
- Prune local and remote branches so only `main` remains.
- Document any intentionally included files that are outside the primary operation scope.

## Scope and Safety

This runbook is intentionally destructive for branch history and active work queues.

- Execute only with explicit maintainer approval.
- Do not run during active release windows.
- Export a snapshot of open Issues/PRs before cleanup for traceability.

## Preconditions

1. Local checkout is on `main` and up to date.
2. GitHub CLI is installed and authenticated.
3. Operator has permission to close Issues/PRs and delete remote branches.

```bash
git checkout main
git pull --ff-only origin main
gh auth status
```

## Step 1: Snapshot Current Work Queues

Capture open work items before cleanup:

```bash
gh pr list --state open --limit 200 --json number,title,headRefName,baseRefName,author

gh issue list --state open --limit 200 --json number,title,author
```

Store snapshots in a temporary local note or deployment log for audit evidence.

## Step 2: Clean Up Pull Requests

Close all open PRs that are out-of-date, superseded, or intentionally deferred.

PowerShell example:

```powershell
$prs = gh pr list --state open --limit 200 --json number | ConvertFrom-Json
foreach ($pr in $prs) {
  gh pr close $pr.number --comment "Repository hygiene cleanup: closing backlog PRs before branch reset to main-only."
}
```

## Step 3: Clean Up Issues

Close all open Issues that are no longer actionable in the current execution wave.

PowerShell example:

```powershell
$issues = gh issue list --state open --limit 200 --json number | ConvertFrom-Json
foreach ($issue in $issues) {
  gh issue close $issue.number --reason "not planned" --comment "Repository hygiene cleanup: backlog reset and re-triage from main baseline."
}
```

## Step 4: Keep Only Main Branch Locally

Delete every local branch except `main`.

```powershell
git checkout main
$localBranches = git branch --format='%(refname:short)' | Where-Object { $_ -ne 'main' }
foreach ($branch in $localBranches) {
  git branch -D $branch
}
```

## Step 5: Keep Only Main Branch on Origin

Delete every remote branch except `origin/main`.

```powershell
$remoteBranches = git for-each-ref --format='%(refname:short)' refs/remotes/origin |
  Where-Object { $_ -ne 'origin/main' -and $_ -ne 'origin/HEAD' }

foreach ($remote in $remoteBranches) {
  $name = $remote -replace '^origin/', ''
  git push origin --delete $name
}
```

## Step 6: Verification

```bash
git branch
git branch -r
gh pr list --state open --limit 50
gh issue list --state open --limit 50
```

Expected result:

- Local branches: only `main`
- Remote branches: only `origin/main`
- Open PRs: 0
- Open Issues: 0

## Out-of-Scope File Inclusion Policy

When the cleanup operation also touches files outside the primary target area (for example generated lockfiles, cross-cutting docs, or governance indexes), keep them in the same PR only if all conditions below are met:

1. The extra file is required to keep the repository consistent after cleanup.
2. The change is mechanical and low-risk.
3. The PR description includes an explicit section named `Out-of-Scope Included Files` listing each additional file and rationale.

If these conditions are not met, split the extra file updates into a separate PR.

## Rollback Guidance

- Branch deletions can be recovered only if branch refs are known.
- Keep the snapshot from Step 1 to recreate critical branches if needed.
- Reopen issues/PRs manually only when they remain relevant after re-triage.
