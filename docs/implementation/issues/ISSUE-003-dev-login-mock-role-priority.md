# ISSUE-003 — Prioritize non-Azure mock login roles in dev

## Problem
Live dev login appears Microsoft-first and does not reliably surface mock role actions for demos.

## Scope
- Ensure development workflows pass the required env vars for mock auth UI.
- Ensure login page UI prioritizes mock role actions in dev-friendly mode.

## Acceptance Criteria
- [ ] Required workflow env vars are wired for dev UI deploy path.
- [ ] `/auth/login` on dev environment shows mock role options prominently before Microsoft flow when allowed.
- [ ] Existing Microsoft auth path remains available.

## Validation
- Open `https://blue-meadow-00fcb8810.4.azurestaticapps.net/auth/login` and verify role buttons appear first in dev mode.
- Confirm sign-in via both mock role and Microsoft path remains functional.
