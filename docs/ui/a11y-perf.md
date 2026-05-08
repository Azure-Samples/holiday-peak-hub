# UI accessibility & performance gates

This file is the registry of automated quality gates applied to the UI surface.
It is updated whenever a gate is added, tightened, or made advisory. Gates
implement the acceptance criteria of [Issue #1060](https://github.com/Azure-Samples/holiday-peak-hub/issues/1060)
and the WCAG 2.2 AA + Core Web Vitals discipline of
[ADR-035 §55](../architecture/adrs/adr-035-ui-design-system.md#55-quality-gates-axe-core--lighthouse-ci--wcag-22-aa--core-web-vitals).

> **Honest beats marketing.** Lab targets in CI are tighter than field targets
> in production. Field targets are recalibrated against P75 RUM data after the
> first 30 days; deltas are amended into ADR-035 with a changelog entry.

## Gate registry

| Gate | What it does | Where it runs | Mode (v1) | Source of truth |
|------|--------------|---------------|-----------|-----------------|
| **axe-core route-group** | Renders `/`, `/retailers/*`, `/builders/*`, `/deploy/*`, `/docs/*` and fails on any "serious" or "critical" finding | `apps/ui/tests/a11y/audienceRouter.test.tsx` (Jest + jest-axe) | **strict** (PR-blocking, F1 cleanup complete) | Issue #1014 (merged) |
| **WCAG 2.2 AA token contrast** | Asserts every system-token pair (warm + cool + neutral, light + dark) at ≥ 4.5:1 body / ≥ 3:1 large text + UI borders | this doc + `tests/unit/tokens.test.ts` (sampling) | **strict** (manual update on token PR) | this file `docs/ui/a11y.md`, ADR-035 §55 QR-2 |
| **Reduced-motion zeroing** | `@media (prefers-reduced-motion: reduce)` zeros `--motion-fast/-base/-emphasized` to 0.01ms and zeros animation/transition durations globally | `apps/ui/app/globals.css` (CSS); `tests/unit/cssArchitecture.test.ts` (assertion) | **strict** | Issue #1058 (merged) + this issue #1060 |
| **`:focus-visible` ring** | `:focus-visible` rule consumes `--sys-focus-ring`; ESLint forbids `outline-none` in audience routes without override | `apps/ui/app/globals.css` (CSS); `apps/ui/.eslintrc.json` (lint) | **strict** | Issue #1058 (merged) + this issue #1060 |
| **Touch-target audit** | Interactive elements ≥ 24×24 CSS px (WCAG 2.5.8 — new in 2.2). At v1, manual audit per archetype documented in `docs/ui/a11y.md`. Playwright assertion follows when Playwright is wired. | manual + this doc | **advisory** (manual at v1) | Issue #1060 AC §6 |
| **Bundle budget** | Per-route gzipped JS ≤ targets (`/` ≤ 150 KB, `/retailers/*` ≤ 200 KB, `/builders/*` ≤ 200 KB, `/deploy/*` ≤ 250 KB) | `.github/workflows/ui-bundle-budget-gate.yml` runs `apps/ui/scripts/check-bundle-budgets.mjs` | **advisory** (PR-comment, exit 0) at v1 — flips to **strict** when the dependency-trim follow-up lands | `apps/ui/budgets.json`; Issue #1060 AC §7 |
| **Lighthouse CI** | LCP ≤ 2.0 s lab, CLS ≤ 0.05 lab, TBT ≤ 200 ms (lab proxy for INP), a11y category ≥ 0.9 | `.github/workflows/ui-lighthouse.yml` runs `@lhci/cli autorun` against `next start` | **advisory** (warn-only) at v1 | `apps/ui/lighthouserc.json`; Issue #1060 AC §8 |
| **Web Vitals (RUM)** | `useReportWebVitals` reports LCP / INP / CLS / TTFB / FCP from production to App Insights | `apps/ui/app/web-vitals.tsx` mounted in root layout | **strict** (release-checklist gate when AppInsights connection string is set) | Issue #1060 AC §10 |
| **Cookie posture** | `/`, `/retailers`, `/builders`, `/deploy` set zero non-essential cookies. App Insights uses 1st-party / sessionStorage 24h. | manual review per release | **strict** | Issue #1060 AC §13 |
| **RTL groundwork** | Spacing utilities use logical properties (`ps-*`/`pe-*`/`ms-*`/`me-*`); `pl-*`/`pr-*` warned. RTL acceptance is v2. | ESLint advisory rule (follow-up) | **advisory** (warning) at v1 | Issue #1060 AC §12 |

## Why advisory at v1?

Issue #1060 explicitly states that bundle and Lighthouse gates **activate after
the F1 dependency cleanup ships** (otherwise every PR fails on existing
bloat). The home `/` floor is currently 167.6 KB gzipped just from
`rootMainFiles + polyfillFiles`; the audience pages add ~300 KB on top from
legacy d-board globals that the route layout transitively imports. Until the
dependency-trim follow-up trims that path, the gates run in advisory mode and
post a PR comment with the delta. The strict thresholds are wired (run via
`--mode=strict` or `BUDGETS_STRICT=1`); the workflow flip is a one-line change.

## How to flip a gate to strict

1. Run `node scripts/check-bundle-budgets.mjs --mode=strict` locally and confirm
   all four audience routes pass.
2. Update `.github/workflows/ui-bundle-budget-gate.yml` to remove `--mode=advisory`
   and let the script's default exit code fail the workflow.
3. Add a commit note: "ui-bundle-budget-gate: flip to strict (resolves #<id>)".
4. The Lighthouse gate flips by changing assertion levels in
   `apps/ui/lighthouserc.json` from `"warn"` to `"error"`.

## Targets — lab vs. field

| Metric | Lab target (CI) | Field target (App Insights P75) | Recalibrated |
|--------|----------------:|--------------------------------:|--------------|
| LCP | ≤ 2.0 s | ≤ 2.5 s | After 30 days RUM |
| INP (proxy: TBT in lab) | TBT ≤ 200 ms | INP ≤ 200 ms | After 30 days RUM |
| CLS | ≤ 0.05 | ≤ 0.1 | After 30 days RUM |
| FCP | ≤ 2.0 s | n/a | n/a |
| Speed Index | ≤ 3.0 s | n/a | n/a |

Lab targets are intentionally tighter than field targets so that CI failures
catch regressions before they reach P75 production traffic. The field targets
are the contractual truth for the platform; if RUM data after 30 days requires
loosening, file an amendment to ADR-035 §55.

## Bundle budget audience routes

| Route segment | v1 budget (gzipped JS) | Current (Nov 2025) | Delta |
|---------------|-----------------------:|-------------------:|------:|
| `/` | 150 KB | ~167 KB | +17 KB |
| `/retailers/*` | 200 KB | ~470 KB | +270 KB |
| `/builders/*` | 200 KB | ~470 KB | +270 KB |
| `/deploy/*` | 250 KB | ~470 KB | +220 KB |

The current numbers reflect the legacy d-board CSS / chunk graph that the root
layout imports unconditionally. The dependency-trim follow-up lifts the
audience routes out of that path entirely (their layouts use only the system-token
imports + tree-shakeable molecule chunks). Demo / admin / legacy routes are
un-budgeted at v1 — they live in their own route groups and do not affect the
audience surface.

## Web Vitals reporter

`apps/ui/app/web-vitals.tsx` is mounted in the root layout. It reads
`window.appInsights.trackEvent` if AppInsights is loaded; otherwise it
no-ops in production and emits `console.debug` in development. Loading
AppInsights via `next/script strategy="afterInteractive"` is a release-
checklist gate, not a v1 codebase gate (the connection string is environment-
dependent).

## Manual touch-target audit

Until Playwright is wired (follow-up), the touch-target gate is a manual
checklist. Run it on each PR that ships an audience-route component:

- All buttons, links, form controls in audience routes have a minimum
  bounding box of 24×24 CSS px.
- Buttons that act as primary CTAs prefer 44×44 (Microsoft Trust standard).
- Spacing between adjacent interactive targets ≥ 8 CSS px.

The cluster molecules (`AgentCardCluster`, `DocsCardCluster`,
`CodeBlockCluster`, `DeployStepCluster`) own their grid spacing and have
been manually audited at the system breakpoints (320, 768, 1280).

## See also

- ADR-035 §55 — quality gates contract
- ADR-034 — audience-segmented IA (the routes these gates target)
- `docs/ui/a11y.md` — WCAG 2.2 AA token-contrast table (companion file)
- `docs/ui/css-architecture.md` — globals.css discipline (Issue #1058)
- `docs/ui/ux-patterns.md` — archetype contract (Issue #1059)
