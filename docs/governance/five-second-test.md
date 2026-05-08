# Five-Second Test Merge Gate

**Owner**: Architecture Team
**Scope**: Pull requests that touch the audience-router information architecture
**Origin**: ADR-034 §7 ("Validation"), Issue #1014
**Last updated**: 2026-04-09

## Purpose

The Holiday Peak Hub home is an **audience router**, not a marketing landing.
Per [ADR-034](../architecture/adrs/adr-034-information-architecture-audience-segmentation.md)
the home page must give a retailer or a builder enough information in five
seconds to (1) know which lane is for them and (2) describe what the platform
offers. If the IA fails that test, the audience router has stopped routing.

This document defines the merge gate that protects that property.

## When the gate applies

The gate is **mandatory** for any pull request whose diff touches at least one
of the following paths:

| Path                                | Why it matters                                  |
| ----------------------------------- | ----------------------------------------------- |
| `apps/ui/app/page.tsx`              | Home is the router itself                       |
| `apps/ui/app/layout.tsx`            | Top-level chrome / nav frames every page        |
| `apps/ui/app/(retailer)/**`         | Retailer lane copy, headings, CTAs              |
| `apps/ui/app/(builder)/**`          | Builder lane copy, headings, CTAs               |
| `apps/ui/app/(deploy)/**`           | Deploy lane is the funnel for both audiences    |
| `apps/ui/components/shared/**`      | `SectionShell`, `LaneSwitch`, `HomeSplitHero`   |
| `apps/ui/styles/tokens/**`          | Palette / type / spacing affect both audiences  |

The `.github/CODEOWNERS` file enforces reviewer assignment automatically — see
the path table at the top of that file. Branch protection on `main` should be
configured to require CODEOWNERS approval on these paths (org-level admin
task; tracked in Issue #1014 follow-up).

The gate is **not** required for pure backend, infra, docs, or non-IA UI
changes (e.g. agent-detail pages, internal dashboards).

## Reviewer pools

Two GitHub teams in `Azure-Samples` review IA changes. They must be balanced
across personas so the home does not drift toward a single audience over
time.

### `@Azure-Samples/holiday-peak-retailer-personas`

- Membership: people who can credibly speak for the retailer audience —
  retail product owners, merchandising leads, store-ops folks, partner SEs
  embedded with retail customers.
- Review responsibility: confirms the retailer lane reads as a business-value
  story (outcomes, ROI, evidence) — not as an architecture pitch.

### `@Azure-Samples/holiday-peak-internal-personas`

- Membership: people who can credibly speak for the internal/builder audience —
  platform engineers, architects, FTEs evaluating the framework, MS field
  engineers running deploy demos.
- Review responsibility: confirms the builder lane reads as a technical
  reference (architecture, ADRs, telemetry, deployment posture) — not as a
  marketing page.

> **Bootstrap state**: until both teams are populated, the repository default
> reviewers cover the gate. Owners may request specific persona reviewers in
> the PR comments. Convert to enforced team review once each pool has ≥ 3
> members.

## Procedure

For every PR that triggers the gate, the author runs the test against the
**rendered preview deployment** (or `yarn workspace ui dev` locally).

1. Pick **6 respondents**: ideally 3 retailer-aligned + 3 internal-aligned.
   They must NOT have seen the change before.
2. For each affected page, show the respondent the page for **~5 seconds**,
   then hide it.
3. Ask the two questions, in this order, recording the first answer:
   - **Q1 — "Where would you click first?"**
   - **Q2 — "What does this site offer?"**
4. Anonymise responses as `retailer-A` / `internal-B` / etc.
5. Paste results into the PR description's **5-second test results** section
   (the template at `.github/PULL_REQUEST_TEMPLATE.md` includes the form).

## Pass / fail rubric

The PR **passes** the gate when **all** of the following hold:

- ≥ 5 of 6 respondents named at least one CTA from their own audience lane.
- ≥ 5 of 6 respondents described the offering in their own words without
  asking a clarifying question.
- No respondent answered Q2 with a value-judgement that conflicts with their
  audience (e.g. a retailer respondent describing the site as "a Python
  framework"). One outlier is tolerated; two is a fail.
- Both audience CTAs were named at least once across the six responses
  (i.e. no audience was invisible).

The PR **fails** the gate when any of the above breaks. On fail, the author
revises copy / layout / hierarchy and re-runs the test before merging.

## CI integration — `ui-axe-core`

A complementary automated gate enforces accessibility:

- Workflow: [.github/workflows/ui-axe-core.yml](../../.github/workflows/ui-axe-core.yml)
- Tests: `apps/ui/tests/a11y/audienceRouter.test.tsx`
- Tool: `axe-core` via `jest-axe`, scoped to WCAG 2.2 AA tags only.
- Pages exercised: home (`HomePage`), `/retailers`, `/builders`, `/deploy` —
  each rendered inside its actual route-group layout so token scoping is
  active.
- Rule set: AA-only via `runOnly.tags = ['wcag2a','wcag2aa','wcag21a','wcag21aa','wcag22aa']`.
  AAA / best-practice findings emit warnings but do not fail.
- Trigger: any PR whose diff touches `apps/ui/**`.

The 5-second test gate and the axe gate are independent — both must pass.

## Reviewer pool activation runbook

1. Open an org-admin issue against `Azure-Samples` requesting the two teams.
2. Seed each team with the people listed in the latest project-status note's
   "IA reviewers" section.
3. Once both teams have ≥ 3 members, enable "Require review from Code Owners"
   in the `main` branch protection rule in this repo.
4. Update this document's **Bootstrap state** note to record activation date.

## Related ADRs / docs

- [ADR-034 — Information architecture, audience segmentation](../architecture/adrs/adr-034-information-architecture-audience-segmentation.md)
- [ADR-035 — UI design system contract](../architecture/adrs/adr-035-ui-design-system-contract.md)
- [Frontend governance](frontend-governance.md)
