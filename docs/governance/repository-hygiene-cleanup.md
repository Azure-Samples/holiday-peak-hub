# Repository Hygiene Cleanup Runbook

**Version**: 1.1
**Last Updated**: 2026-06-09
**Audience**: Repository maintainers and admins

## Purpose

Use this runbook to perform repository hygiene maintenance in one controlled operation:

- Close GitHub Issues and Pull Requests only when their report or change has already been incorporated into `main`, or when there is explicit maintainer approval to mark them obsolete.
- Prune local and remote branches so only `main` remains.
- Document any intentionally included files that are outside the primary operation scope.

## Scope and Safety

This runbook is intentionally destructive for branch history and work-queue metadata.

- Execute only with explicit maintainer approval.
- Do not run during active release windows.
- Export a snapshot of open Issues/PRs before cleanup for traceability.
- Do not treat open work as disposable backlog. Closing is allowed only with evidence that the work is already in `main`, superseded by an incorporated equivalent, or explicitly abandoned by the maintainer.
- Do not delete branches that contain unmerged, unincorporated, or currently dirty local work.

## Preconditions

1. Local checkout is on `main` and up to date.
2. GitHub CLI is installed and authenticated.
3. Operator has permission to close Issues/PRs and delete remote branches.
4. Local working tree is clean, or any dirty work has been committed, stashed, or explicitly preserved outside the branch-pruning operation.

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

## Step 2: Determine Incorporation Eligibility

Classify every open PR and Issue before changing state.

### Pull Request Eligibility

An open PR is eligible for hygiene closure only when at least one condition is true:

1. The PR has no effective diff against `main`.
2. The same change was merged through another PR or commit already reachable from `main`.
3. The maintainer explicitly says to abandon it despite an open diff.

If a PR still has a meaningful diff and CI is passing, flag it as a **merge-first candidate**. Do not close it as hygiene.

PowerShell evidence helper:

```powershell
$prs = gh pr list --state open --limit 200 --json number,title,headRefName,mergeable,isDraft | ConvertFrom-Json
foreach ($pr in $prs) {
  $diffFiles = @(gh pr diff $pr.number --name-only 2>$null)
  $status = if ($diffFiles.Count -eq 0) { "incorporated-or-empty-diff" } else { "open-diff-review-or-merge-first" }
  [pscustomobject]@{
    Number = $pr.number
    Title = $pr.title
    Status = $status
    DiffFiles = $diffFiles.Count
    Mergeable = $pr.mergeable
  }
}
```

### Issue Eligibility

An open Issue is eligible for hygiene closure only when its acceptance criteria are represented in `main` with evidence, such as:

- a merged PR or commit hash that implements it;
- files on `main` that directly implement or document the requested behavior;
- project status documentation that states the issue is complete;
- a superseding issue/ADR/PR that is already incorporated into `main`.

References alone are not sufficient when the file text says the work is only scaffolded, preview-only, or gated for a future phase. In that case, leave the Issue open or update it with the partial-completion evidence.

Evidence helper:

```powershell
$issues = gh issue list --state open --limit 200 --json number,title | ConvertFrom-Json
foreach ($issue in $issues) {
  $logHits = @(git log origin/main --oneline --grep="#$($issue.number)" --all-match)
  $fileHits = @(git grep -n -F "#$($issue.number)" origin/main -- docs .github apps README.MD CHANGELOG.md 2>$null)
  [pscustomobject]@{
    Number = $issue.number
    Title = $issue.title
    CommitReferences = $logHits.Count
    FileReferences = $fileHits.Count
  }
}
```

## Step 3: Clean Up Pull Requests

Close only PRs classified as incorporated, superseded by incorporated work, or explicitly abandoned by the maintainer. Every closure comment must name the evidence.

PowerShell example:

```powershell
$eligiblePrs = @(
  # Fill from Step 2 after evidence review.
  # Example: @{ number = 123; evidence = "incorporated by PR #456 / commit abc123" }
)

foreach ($pr in $eligiblePrs) {
  gh pr close $pr.number --comment "Repository hygiene cleanup: closing because this PR is already incorporated in main. Evidence: $($pr.evidence)."
}
```

## Step 4: Clean Up Issues

Close only Issues classified as incorporated into `main`, superseded by incorporated work, or explicitly abandoned by the maintainer. Prefer closing incorporated work as completed when supported by the GitHub UI/CLI. Use `--reason "not planned"` only for maintainer-approved abandoned or obsolete work, not for work that actually shipped.

PowerShell example:

```powershell
$eligibleIssues = @(
  # Fill from Step 2 after evidence review.
  # Example: @{ number = 123; reason = "completed"; evidence = "implemented by PR #456 / commit abc123" }
)

foreach ($issue in $eligibleIssues) {
  if ($issue.reason -eq "not planned") {
    gh issue close $issue.number --reason "not planned" --comment "Repository hygiene cleanup: closing as obsolete. Evidence: $($issue.evidence)."
  } else {
    gh issue close $issue.number --comment "Repository hygiene cleanup: closing because this issue is incorporated in main. Evidence: $($issue.evidence)."
  }
}
```

## Step 5: Keep Only Main Branch Locally

Delete local branches only after confirming they do not contain unmerged or unpreserved work. If the current branch has dirty changes, preserve them before switching branches.

```powershell
git checkout main
$localBranches = git branch --format='%(refname:short)' | Where-Object { $_ -ne 'main' }
foreach ($branch in $localBranches) {
  git branch -D $branch
}
```

## Step 6: Keep Only Main Branch on Origin

Delete remote branches only when the associated work is already merged, incorporated elsewhere, or explicitly abandoned by the maintainer. Skip branches from external forks and non-target remotes.

```powershell
$remoteBranches = git for-each-ref --format='%(refname:short)' refs/remotes/origin |
  Where-Object { $_ -ne 'origin/main' -and $_ -ne 'origin/HEAD' }

foreach ($remote in $remoteBranches) {
  $name = $remote -replace '^origin/', ''
  git push origin --delete $name
}
```

## Step 7: Verification

```bash
git branch
git branch -r
gh pr list --state open --limit 50
gh issue list --state open --limit 50
```

Historical target result for a full, maintainer-approved cleanup procedure:

- Local branches: only `main`
- Remote branches: only `origin/main`
- Open PRs: 0
- Open Issues: 0

> This document describes a hygiene target state, not a command to abandon active work. The live repository may intentionally have open PRs and issues when they are not yet incorporated into `main`.

## Out-of-Scope File Inclusion Policy

When the cleanup operation also touches files outside the primary target area (for example generated lockfiles, cross-cutting docs, or governance indexes), keep them in the same PR only if all conditions below are met:

1. The extra file is required to keep the repository consistent after cleanup.
2. The change is mechanical and low-risk.
3. The PR description includes an explicit section named `Out-of-Scope Included Files` listing each additional file and rationale.

If these conditions are not met, split the extra file updates into a separate PR.

## Rollback Guidance

- Branch deletions can be recovered only if branch refs are known.
- Keep the snapshot from Step 1 to recreate critical branches if needed.
- Reopen issues/PRs manually when closure evidence was wrong, incomplete, or later superseded by new findings.
