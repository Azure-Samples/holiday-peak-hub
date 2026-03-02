# ADR-022: Git Branch Naming Convention

**Status**: Accepted  
**Date**: 2026-03  
**Deciders**: Architecture Team, Ricardo Cataldi  
**Tags**: governance, git, branching, ci-cd

## Context

As the project grows with multiple contributors (human and AI agents), a consistent
branch naming convention is essential to:

- Communicate **intent** (feature, bug fix, hotfix) at a glance.
- Enable **CI/CD workflow filtering** (e.g., deploy only from specific branch prefixes).
- Keep the repository organized and easy to navigate.
- Align automated tooling (GitHub Actions, Copilot agents) with human workflows.

Without a documented standard, branch names have varied across contributors
(`feat/`, `feature/`, `issue/`, ad-hoc names), making it difficult to enforce
automation rules or quickly assess branch purpose.

### Requirements

- Clear mapping between branch type and purpose.
- Every branch traces to an issue or work item.
- Convention must be enforceable by CI and agent tooling.
- Compatible with GitHub Pull Request workflows.

## Decision

**Adopt the branching model described in [digitaljhelms/4287848](https://gist.github.com/digitaljhelms/4287848),
adapted to this repository's conventions (using `main` as the working branch).**

### Branch Types

| Branch Type | Pattern | Branches From | Merges Into | Purpose |
|-------------|---------|---------------|-------------|---------|
| **Stable** | `main` | — | — | Latest delivered development; always deployable |
| **Feature** | `feature/<issue-id>-<short-description>` | `main` | `main` | New capabilities with potentially long lifespan |
| **Issue** | `issue/<issue-id>-<short-description>` | `main` | `main` | Issue-tracked work (features, improvements, tasks) |
| **Bug** | `bug/<issue-id>-<short-description>` | `main` | `main` | Bug fixes for the next deployment |
| **Hotfix** | `hotfix/<issue-id>-<short-description>` | tagged `main` | `main` | Urgent production fixes |
| **Docs** | `docs/<issue-id>-<short-description>` | `main` | `main` | Documentation-only changes |
| **Chore** | `chore/<issue-id>-<short-description>` | `main` | `main` | Maintenance, CI, tooling, dependency updates |

### Naming Rules

1. **Always use lowercase** with hyphens as word separators.
2. **Always include the issue number** after the prefix (e.g., `feature/42-cart-intelligence`).
3. **Keep descriptions short** (2-4 words) but meaningful.
4. **No personal names or dates** in branch names.
5. **Delete branches** after merging via PR — branches are ephemeral.

### Examples

```
feature/55-cart-abandonment-flow
issue/30-ci-agent-tests-no-swallow
bug/78-missing-redis-fallback
hotfix/99-checkout-500-error
docs/101-update-adr-index
chore/110-bump-fastapi-version
```

### Workflow

```
main ──────────────────────────────────────────────────▶
  │                                                  ▲
  ├── feature/42-cart-intelligence ──── PR ───────────┤
  │                                                   │
  ├── bug/78-missing-redis-fallback ── PR ────────────┤
  │                                                   │
  └── hotfix/99-checkout-500-error ── PR ─────────────┘
```

1. **Create** the branch locally from `main` HEAD:
   ```bash
   git checkout -b feature/42-cart-intelligence main
   git push origin feature/42-cart-intelligence
   ```

2. **Periodically rebase or merge** `main` into your branch to stay current:
   ```bash
   git merge main   # or git rebase main
   ```

3. **Open a Pull Request** targeting `main`. Use conventional PR titles.

4. **After merge**, delete the remote branch (GitHub auto-delete is enabled).

### CI/CD Integration

GitHub Actions workflows can filter on branch prefixes:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

The `deploy-azd.yml` workflow triggers only on `main`, ensuring only merged and
reviewed code reaches deployment.

## Consequences

### Benefits

- **Clarity**: Anyone can determine branch purpose from its name.
- **Traceability**: Every branch is linked to an issue number.
- **Automation**: CI can enforce naming via branch protection rules or linting.
- **Agent alignment**: Copilot and AI agents follow the same convention when creating branches.
- **Clean history**: Ephemeral branches are deleted post-merge, keeping the remote tidy.

### Risks / Trade-offs

- Contributors must learn and follow the convention (mitigated by Copilot instructions).
- Existing non-conforming branches are not renamed retroactively.

## Alternatives Considered

### 1. Gitflow (develop + release branches)
- **Rejected**: Too heavyweight for a monorepo with CI/CD on every push to `main`.
  Separate `develop` and `release` branches add complexity without benefit for
  this project's deployment model (azd-first, deploy on merge to `main`).

### 2. Trunk-based development (no feature branches)
- **Rejected**: With 22+ services and multiple contributors, short-lived feature
  branches with PRs provide essential code review and CI gates.

### 3. Free-form naming
- **Rejected**: Already proven problematic — inconsistent names make automation
  and navigation difficult.

## References

- [Git/GitHub branching standards & conventions (digitaljhelms)](https://gist.github.com/digitaljhelms/4287848)
- [A successful Git branching model (nvie)](https://nvie.com/posts/a-successful-git-branching-model/)
- [ADR-021: azd-First Deployment](adr-021-azd-first-deployment.md)
