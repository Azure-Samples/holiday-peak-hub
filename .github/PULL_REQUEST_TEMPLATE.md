<!--
  Pull Request template — Holiday Peak Hub
  See `.github/copilot-instructions.md` for repo-wide standards and
  `docs/governance/five-second-test.md` for the audience-router merge gate.
-->

## Summary

<!-- One paragraph: what changed and why. Link the issue being closed. -->

Closes #

## Acceptance criteria

<!-- Copy the criteria from the linked issue and check each one off. -->

- [ ] …

## Architecture constraints

<!-- ADRs, instructions files, and READMEs the change must respect. -->

- ADR-???: …

## Verification

<!-- Commands run, environments tested, screenshots/logs as needed. -->

- [ ] `yarn lint` (UI) / `python -m pylint …` (backend)
- [ ] `yarn build` (UI) / `python -m pytest` (backend)
- [ ] `yarn test` (UI) / contract tests (lib)

---

## 5-second test results

> **Required when this PR modifies any of:** `apps/ui/app/page.tsx`,
> `apps/ui/app/layout.tsx`, `apps/ui/app/(retailer)/**`,
> `apps/ui/app/(builder)/**`, `apps/ui/app/(deploy)/**`,
> `apps/ui/components/shared/**`, or `apps/ui/styles/tokens/**`.
> Skip this section otherwise — leave it blank or delete it.
>
> Procedure: see [docs/governance/five-second-test.md](../docs/governance/five-second-test.md).
> Show each respondent the affected page for ~5 seconds, then ask the two
> questions below. Anonymise responses (e.g. "retailer-A", "internal-B").

**Audience-router IA merge gate (ADR-034 §7 / Issue #1014)**

### Where would you click first?

- retailer-A: …
- retailer-B: …
- retailer-C: …
- internal-A: …
- internal-B: …
- internal-C: …

### What does this site offer?

- retailer-A: …
- retailer-B: …
- retailer-C: …
- internal-A: …
- internal-B: …
- internal-C: …

### Verdict

- [ ] **Pass** — at least one CTA per audience was named, and ≥ 5 of 6
      respondents described the offering in their own words within 5 seconds
      without bias toward a single audience.
- [ ] **Fail** — see notes below; revise IA before merge.

Notes / follow-ups: …

---

## Axe / a11y

- [ ] `yarn workspace ui test:a11y` passes (WCAG 2.2 AA, zero violations)
- [ ] No new colour pair below 4.5:1 contrast (3:1 for ≥ 18 pt / 14 pt bold)

## Risk & rollback

<!-- Blast radius, feature flags, rollback procedure if applicable. -->

- Blast radius: …
- Rollback: …
