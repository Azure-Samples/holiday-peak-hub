# ISSUE-004 — Mobile navbar hamburger visibility regression

## Problem
Mobile navigation hamburger is reported as missing/non-visible in live demo.

## Scope
- Audit navbar render path and mobile breakpoints.
- Fix visibility/contrast/stacking conditions preventing hamburger from appearing.

## Acceptance Criteria
- [ ] Hamburger button is visible at mobile width on all primary pages.
- [ ] Button opens/closes mobile menu reliably.
- [ ] No desktop navigation regressions.

## Validation
- Mobile viewport check on home and category/search pages.
- Playwright check confirms button visibility and menu toggle behavior.
