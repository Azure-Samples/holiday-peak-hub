# ADR-035: UI Design System Contract — Tokens, Components, CSS Architecture, and Quality Gates

**Status**: Accepted (Extends ADR-033 + ADR-034)
**Date**: 2026-05-08
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: frontend, design-system, design-tokens, css, accessibility, performance, quality-gates
**References**: [ADR-011](adr-011-nextjs-app-router.md), [ADR-012](adr-012-atomic-design-system.md) (superseded on component-naming convention only by §3 of this ADR), [ADR-018](adr-018-branch-naming-convention.md), [ADR-033](adr-033-ui-modular-monolith-on-swa.md), [ADR-034](adr-034-audience-segmented-ia.md)

## Status

Accepted. **Extends ADR-033 + ADR-034**; supersedes ADR-012's component-naming convention (atoms / molecules / organisms / templates) for `apps/ui` going forward, while preserving ADR-012's broader atomic-design intent (small primitives compose into complex surfaces with explicit boundaries).

ADR-033 and ADR-034 are accepted and this ADR extends both. Future amendments to either ADR that materially change directory, route-group, or token contracts must update this ADR's Decision (§1, §2, §6) and Implementation tables in the same PR.

## Context

`apps/ui/` is the platform's primary sales surface. ADR-033 pins it as a modular monolith on Azure Static Web Apps with feature isolation under `src/features/<context>/`. ADR-034 pins the audience-segmented information architecture under `(retailer)`, `(builder)`, `(deploy)` route groups and the dual design-token concept (`tokens/{brand,retailer,builder}.css`).

Neither of those ADRs pins **the design-system contract itself**: how tokens are layered and named, what primitives compose into what composites, how CSS is organized, what motion and dark-mode rules apply, or what quality gates must pass before a UI change merges. The user has flagged that previous UI work did not achieve good results. Without a pinned contract, the next attempt regresses to the same failure mode.

This ADR pins that contract. It is the third leg of the three-ADR UI foundation:

| ADR | Pins |
|---|---|
| ADR-033 | Layout + deployment surface (modular monolith on SWA) |
| ADR-034 | Information architecture + audience surface (route groups, dual tokens, 5-second test gate) |
| **ADR-035** (this) | Design-system contract — tokens, components, CSS, quality gates that flow into the dual-token concept ADR-034 introduced |

### Diagnostic of the previous UI attempt

Section 50 of the staging-memory improvement plan (`.tmp/improvement_plan/50-ui-design-system/50-diagnostic-previous-attempt.md`) performed a forensic audit of `apps/ui/` and named ten root causes. Each root cause has been verified against the current `main` filesystem; deviations from the staging-memory text are noted inline.

| ID | Root cause | Evidence on `main` (verified) | Fix gate |
|---|---|---|---|
| **RC-1** | Two Tailwind configs in the same project. | `apps/ui/tailwind.config.ts` (Inter + Ocean Blue / Lime / Cyan + `--hp-*` aliases) and `apps/ui/tailwind.config.js` (Poppins + `#3cb371` green + legacy `collapsed` / `rtl` plugins) both present, with `tailwindcss: 4.2.2` and `@tailwindcss/postcss: ^4.2.2` in `package.json`. Tailwind 4 CSS-first mode means both files are partially ignored, partially honored. | §1, §6 |
| **RC-2** | Three competing color palettes co-exist. | Warm `--hp-*` tokens (`#c73a2a`, `#0d7a70`) in `apps/ui/app/globals.css`; Ocean Blue / Lime / Cyan in `tailwind.config.ts`; legacy `#3cb371` green in `tailwind.config.js`. A single `<Button variant="primary">` resolves unpredictably across PRs. | §1, §2 |
| **RC-3** | Two component libraries claim the same names. | The atomic tree exists at `apps/ui/components/{atoms,molecules,organisms,templates}/` (verified — there is **no** `components/atomic/` parent folder, contrary to the staging-memory text). Companion `apps/ui/components/ATOMIC_README.md` documents the import path `@/components/atomic/atoms/Button` — a path that does **not** exist in the code. The barrel `apps/ui/components/index.ts` re-exports from `./atoms`, `./molecules`, `./organisms`, `./templates` directly. Top-level legacy d-board files (`navbar-1.tsx`, `left-sidebar-1.tsx`, `left-sidebar-2.tsx`, `right-sidebar-1.tsx`) sit alongside the atomic tree as TSX **files** (not folders, contrary to the staging-memory text). The diagnostic mention of a top-level `components/Button.tsx` co-existing with `components/atoms/Button.tsx` was **not** confirmed — only the atoms version exists. The real defect is the docs-vs-code mismatch plus the legacy d-board files at the top level. | §3, §6 |
| **RC-4** | `globals.css` does the work of six files. | `apps/ui/app/globals.css` is ~250 lines covering brand tokens, focus rules, body gradient, selection styles, button utility classes, `.card`, `.input`, `.link`, `.demo-stage`, `.demo-panel`, `.demo-telemetry`, plus a `.dark` override block. `apps/ui/app/layout.tsx` imports nine more CSS files: `main.css`, `layouts/layout-1.css`, `layouts/e-commerce.css`, `animate.css`, `components/left-sidebar-1/styles-{lg,sm}.css`, `components/nprogress.css`, `components/recharts.css`, `components/steps.css`, `components/left-sidebar-3.css`. | §4, §6 |
| **RC-5** | The home page is a dashboard, not a product website. | `apps/ui/app/page.tsx` is `'use client'` and renders `<ExecutiveDemoPage />` (a fictional retail demo cockpit). ADR-034 pins `/` as the audience-router home with two equal-weight CTAs. Current home fails the 5-second test for both audiences. | §6 |
| **RC-6** | The `package.json` identity is still "d-board" with dead-weight dependencies. | `apps/ui/package.json` field `"name": "d-board"` confirmed. All eleven dead-weight dependencies still listed: `@stripe/react-stripe-js`, `@reduxjs/toolkit`, `react-redux`, `recharts`, `react-star-ratings`, `react-popper`, `react-select`, `react-switch`, `nprogress`, `flatted`, `lodash`. | §6 |
| **RC-7** | Motion language is undisciplined. | Inline `cubic-bezier(...)` declarations and per-component duration/easing across the atomic tree. No `--motion-fast` / `--motion-base` / `--motion-emphasized` token system on `main`. | §4 |
| **RC-8** | Dark mode is a class override, not a theming context. | `globals.css` declares `.dark { ... }` re-binding every `--hp-*` token. Atomic components rely on per-component `dark:` Tailwind utilities. `apps/ui/app/layout.tsx` already declares `<meta name="color-scheme" content="light dark" />` but components do not behave as if both schemes are first-class. | §1, §4 |
| **RC-9** | There is no audience-aware token layer. | `main` has zero `--retailer-*` / `--builder-*` system tokens, no route-level theming, no `<RetailerShell>` / `<BuilderShell>` wrappers. ADR-034 introduces the concept; this ADR pins the contract that flows into it. | §1, §2 |
| **RC-10** | No design-system documentation that matches the code. | `components/ATOMIC_README.md` references files (`/docs/ECOMMERCE_UI_PLAN.md`, `/ui/COMPONENT_ANALYSIS.md`, `/ui/SHARED_PATTERNS.md`) that do not exist at those paths. The README is aspirational documentation for a state the code never reached. | §5, §6 |

The pattern is consistent: three template pedigrees (legacy "d-board" admin, Ocean / Lime e-commerce skin, warm `--hp-*` brand) layered without removal, no single-source-of-truth, no quality gates, no token discipline. This ADR pins the contract that prevents the next regression.

## Decision

### 1. Three-layer token architecture (Tailwind 4 CSS-first)

Adopt the standard three-layer token architecture used by Material 3, Adobe Spectrum, and GitHub Primer, expressed in Tailwind 4 CSS-first form:

- **Reference tokens** (Layer 1, raw palette): warm coral / amber family for the retailer audience, cool slate / blue family for the builder audience, neutrals shared. Named `--ref-color-warm-500`, `--ref-color-cool-500`, `--ref-color-neutral-50`, etc. Never consumed directly by components.
- **System tokens** (Layer 2, semantic, theme-aware): `--sys-surface-base`, `--sys-surface-raised`, `--sys-text-primary`, `--sys-text-muted`, `--sys-action-primary`, `--sys-action-primary-hover`, `--sys-feedback-success`, `--sys-focus-ring`, `--sys-motion-fast`, `--sys-motion-base`, `--sys-motion-emphasized`. System tokens reference reference tokens and are theme-aware via `light-dark()` (with a `@supports` / `prefers-color-scheme` fallback for non-Chromium evergreen targets).
- **Component tokens** (Layer 3, optional at v1): `--comp-button-bg`, `--comp-card-padding`, etc. Reference system tokens, never reference tokens directly. Added on demand when a primitive proves it needs an extra slot.

**Naming convention (lint-enforced)**: every custom property is prefixed `--ref-`, `--sys-`, `--comp-`, or one of Tailwind 4's reserved prefixes (`--color-`, `--font-`, `--spacing-`, `--radius-`, `--ease-`, `--motion-`). Any property without one of these prefixes fails PR review (RC-2 fix).

**Tailwind 4 `@theme` CSS-first model is the single source of truth.** Both legacy JS configs (`apps/ui/tailwind.config.ts` and `apps/ui/tailwind.config.js`) are hard-deleted in the cleanup PR (RC-1 fix). The `@theme` block lives in the brand token file imported by `globals.css`; reference tokens become Tailwind utilities (`bg-warm-500`, `text-cool-50`).

**File organization** (extending ADR-034 §3 token-file layout):

```
apps/ui/src/styles/
├── globals.css                 # ≤ 60 lines: imports + cascade-layer order + base reset only
├── tokens/
│   ├── brand.css               # @theme block + reference tokens + audience-neutral system tokens
│   ├── retailer.css            # warm reference tokens + system bindings under [data-audience="retailer"]
│   ├── builder.css             # cool reference tokens + system bindings under [data-audience="builder"]
│   └── CONTRAST.md             # documented contrast ratios per token pair (per ADR-034 §8)
```

This refines ADR-034's `tokens/{brand,retailer,builder}.css` contract by pinning the three-layer naming inside each file. Component tokens, when they appear, live under `tokens/components/<primitive>.css` and are imported only by their primitive.

**Dark mode is theme-aware at the system layer**, not per-component. Components write `background-color: var(--sys-surface-base)` once. No `dark:bg-...` utilities (RC-8 fix). The `prefers-color-scheme` change re-binds tokens at the system layer; components do not see it.

### 2. Audience theming via route-level shells

Audience context is set by route-level shell components that wrap each route group from ADR-034 §2:

- `<RetailerShell>` wraps `(retailer)/layout.tsx` content, sets `data-audience="retailer"` and class `audience-retailer` on its root, imports `tokens/brand.css` + `tokens/retailer.css`.
- `<BuilderShell>` wraps `(builder)/layout.tsx`, sets `data-audience="builder"` + `audience-builder`, imports `tokens/brand.css` + `tokens/builder.css`.
- `<DeployShell>` wraps `(deploy)/layout.tsx`, sets `data-audience="deploy"` + `audience-deploy`, imports `tokens/brand.css` only (deploy is task-focused; neutral tokens per ADR-034 §3).
- `<HomeShell>` wraps `app/page.tsx`, sets `data-audience="home"` + `audience-home`, imports `tokens/brand.css` only.

System tokens select audience-appropriate values via attribute-scoped CSS variables:

```css
/* tokens/retailer.css */
[data-audience="retailer"] {
  --sys-action-primary: var(--ref-color-warm-500);
  --sys-action-primary-hover: var(--ref-color-warm-600);
  --sys-surface-accent: var(--ref-color-warm-50);
}

/* tokens/builder.css */
[data-audience="builder"] {
  --sys-action-primary: var(--ref-color-cool-500);
  --sys-action-primary-hover: var(--ref-color-cool-600);
  --sys-surface-accent: var(--ref-color-cool-50);
}
```

Component primitives **never read the audience**. They consume `var(--sys-action-primary)` and the shell decides what color that resolves to. The shell is the only layer that knows about the audience (RC-9 fix).

**Dual marking**: shells set both the `data-audience` attribute (for CSS selectors) and the matching `audience-<value>` class (for greppability and dev-tools visibility). PR review rejects any attempt to read the audience from a non-shell component.

This refines ADR-034 §3's "data-section attribute that token CSS keys off" mention to specifically `data-audience` + `audience-*` class. Cross-references ADR-034 §3 for the dual design-token concept and ADR-034 §6 for the soft persona detection rules (cookie / `?as=` parameter never gates content).

### 3. Component library contract

**One library, one import path.** The barrel `apps/ui/src/components/index.ts` is the single public surface. Deep imports across tiers are PR-rejected.

**Three tiers, named by responsibility**:

- **`primitives/`** — neutral building blocks. No business logic. No audience awareness. Examples: `Button`, `Link`, `Heading`, `Text`, `Surface` (replaces `Card`), `Stack`, `Cluster`, `Grid`, `Icon`, `Code`, `CodeBlock`, `Badge`, `FocusRing`. Accept `className`. TypeScript types for every prop. No `any`.
- **`composites/`** — opinionated, pattern-named. Compose primitives. Examples: `Hero`, `ValueProp`, `ValuePropGrid`, `Comparator`, `Quote`, `MaturityBadge`, `ConfidenceInterval`, `PricingTable`, `FeatureMatrix`, `CallToAction`, `DocsCard`, `AgentCard`, `DeployStep`. Composites do **not** accept `className`; if a composite needs styling override, the API is wrong. Composites accept `tone` and `density` enums (no more than three values each). Composites declare `maturityBadge` as a prop on every claim-bearing surface (per ADR-034 "no vanity metrics" rule).
- **`shells/`** — exactly four: `RetailerShell`, `BuilderShell`, `DeployShell`, `HomeShell`. Adding a fifth requires amending ADR-034 §1.

**Why these names rather than atoms / molecules / organisms / templates.** The atomic-design metaphor is a literary device, not a contract. The current code uses `apps/ui/components/{atoms,molecules,organisms,templates}/` (atomic-design naming, no `atomic/` parent — contrary to the staging-memory text). The cleanup PR migrates the atomic tree to `apps/ui/src/components/{primitives,composites,shells}/` after the ADR-033 refactor moves `apps/ui/app/` to `apps/ui/src/app/`. ADR-012 ("Atomic Design System for Component Library") is **superseded on the naming convention only**; its broader intent — small primitives compose into complex surfaces with explicit boundaries — is preserved.

**Prop contract discipline**:

1. No `variant` enum with more than four values. If you need five, you have two components.
2. No `style={{}}` inline style on JSX. Inline styles bypass the token contract.
3. `data-testid` and `aria-label` are first-class props on every interactive primitive.
4. No `onClick` on `<div>`. If it clicks, it is a `<button>` or a `<Link>`.
5. `'use client'` is opt-in, declared at the file top with a comment justifying the choice. Default is server component.
6. Server components are the default. The `(demo)` route group (deferred per ADR-034 out-of-scope) keeps client-only libraries (Stripe, Recharts) out of the marketing surface bundle.

**TypeScript types are exported alongside every primitive and composite.** No `any`. Discriminated unions are used for composites with multiple shapes (e.g., `Hero` with `kind: 'audience-router' | 'audience-page' | 'docs'`).

**Legacy hard-deletes** (in the cleanup PR before any new component lands):

- Top-level legacy d-board files: `apps/ui/components/navbar-1.tsx`, `left-sidebar-1.tsx`, `left-sidebar-2.tsx`, `right-sidebar-1.tsx` (TSX files at the components root, verified).
- Legacy layout folders: `apps/ui/layouts/layout-1/`, `apps/ui/layouts/e-commerce/`, `apps/ui/layouts/centered/`, `apps/ui/layouts/centered-form/` (and `apps/ui/layouts/index.tsx`).
- Stale documentation: `apps/ui/components/ATOMIC_README.md` (replaced by the contract pinned here and by per-primitive README files written during the migration).

**Storybook is deferred** until the new library stabilizes, per Section 50 README "Out of scope." ADR-034 §3's "mandatory dual-Storybook screenshots" obligation activates only after this ADR's library lands.

### 4. CSS architecture

**`globals.css` is theme + base only**, ≤ 60 lines (CI hard-fail at 80 to allow a small buffer). It contains imports, cascade-layer declaration, and a minimal reset. No component classes. No vendor stylesheets. No `.demo-*` blocks (RC-4 fix).

**Cascade layer order** (declared at the top of `globals.css`):

```css
@layer reset, theme, base, components, utilities, app;
```

The `app` layer carries primitive overrides only (rare). Tailwind 4 owns `theme`, `base`, `components`, `utilities`. Our `reset` runs first; our `app` runs last.

**Component styles are Tailwind utilities first.** CSS Modules co-located with the primitive (`Button/Button.module.css`) are allowed only when Tailwind utilities cannot express the rule (e.g., `CodeBlock` complex pseudo-elements). Composites do **not** get module CSS; if they need it, the answer is to add a primitive. Module CSS files declare a single class matching the file basename. CSS-in-JS (styled-components, emotion, vanilla-extract) is rejected — it is incompatible with server components by default.

**Vendor stylesheets are imported only in the route segments that need them.** `nprogress`, `recharts`, `steps`, `left-sidebar-*` CSS files imported globally in `apps/ui/app/layout.tsx` today (verified) move to local imports inside the `(demo)` route group when the demo is restored, or are deleted with the demo (RC-4 fix). The marketing surface (`/`, `/retailers/*`, `/builders/*`, `/deploy/*`) imports zero vendor stylesheets at the global level.

**Motion contract — three durations, two named easings + one spring**:

```css
@theme {
  --motion-fast: 120ms;        /* hover, ripple, micro-feedback */
  --motion-base: 200ms;        /* state changes, entry / exit */
  --motion-emphasized: 320ms;  /* page-level transitions, overlays */

  --ease-base: cubic-bezier(0.2, 0, 0, 1);
  --ease-emphasized: cubic-bezier(0.05, 0.7, 0.1, 1);
  --ease-spring: linear(0, 0.5 30%, 1 60%, 0.95 75%, 1);
}
```

Components consume `duration-fast | duration-base | duration-emphasized` Tailwind utilities mapped to tokens. Inline `cubic-bezier(...)` declarations fail PR review (RC-7 fix).

**`@media (prefers-reduced-motion: reduce)` overrides ALL motion tokens to ~0ms** in `globals.css`. The override zeroes duration; it does not hide elements (loading spinners stay visible but stop spinning). CI smoke test asserts no animations remain in a `prefers-reduced-motion` snapshot.

**Logical CSS properties** (`padding-inline`, `margin-inline-start`, etc.) for all spacing utilities, anticipating RTL support in a future v2 without component rewrites. Tailwind 4 already favors `ps-*`, `pe-*`, `ms-*`, `me-*`. Lint warns on physical properties (`pl-*`, `pr-*`).

**Asset policy**:

- Fonts: `next/font/google` for `Inter` and `JetBrains Mono`, both variable. No font ever loaded from a CDN URL.
- Icons: tree-shakable named-import library. The current `react-icons` dependency is replaced (recommendation: `lucide-react`) in the cleanup PR.
- Images: `next/image` for all imagery; AVIF preferred, WebP fallback. Hero images at three sizes (320, 768, 1280).
- SVG illustrations: served from `apps/ui/public/illustrations/`. Brand SVGs accept `currentColor` so they consume `--sys-text-primary` automatically. Illustration components accept a `tone="warm" | "cool" | "neutral"` prop, never raw hex.

### 5. Quality gates

The contract requires CI gates that activate after the cleanup PR sequence (§6) lands. Until then, the gates are advisory and the numbers below are "initial budget, revisited at first cutover" against post-cleanup measurements.

**Bundle budget per route segment (initial; revisited at first cutover)**, gzipped, p95:

| Route | JS budget | Notes |
|---|---|---|
| `/` (home) | ≤ 150 KB | initial budget |
| `/retailers/*` | ≤ 200 KB | initial budget |
| `/builders/*` | ≤ 200 KB | initial budget |
| `/deploy/*` | ≤ 250 KB | includes Entra OBO + stepper state |
| `/docs/*` | governed by Section 42 (mkdocs pipeline) | not enforced here |
| `(demo)` | un-budgeted at v1 | lazy-loaded route group |

CSS budget per route ≤ 30 KB. Hero image budget ≤ 80 KB after AVIF conversion.

**Core Web Vitals targets** (p75, mobile, slow 4G, RUM via App Insights once deployed):

| Metric | Target (good) | Hard fail |
|---|---|---|
| LCP | ≤ 2.0 s | > 4.0 s |
| INP | ≤ 200 ms | > 500 ms |
| CLS | ≤ 0.05 | > 0.25 |

CI uses Lighthouse with TBT (Total Blocking Time) ≤ 200 ms as the lab proxy for INP. Field INP via App Insights is the source of truth post-launch. Targets are recalibrated after 30 days of production traffic.

**Accessibility — WCAG 2.2 AA** for both audience palettes:

- Token-level contrast audit: body text ≥ 4.5 : 1, large text ≥ 3 : 1, UI component borders ≥ 3 : 1, **per audience**. Documented in `apps/ui/src/styles/tokens/CONTRAST.md` (per ADR-034 §8).
- `axe-core` CI gate at the route-group level (retailer, builder, deploy preview environments) — PR-blocking on `serious` or `critical` violations. This satisfies ADR-034 §8's `axe-core` requirement.
- Keyboard pass on every archetype URL: tab order, focus order, Esc / Enter / Space behaviors verified via Playwright.
- WCAG 2.2 new criteria explicitly covered: 2.4.11 (focus not obscured by sticky chrome), 2.4.13 (focus appearance ≥ 2 px outline + 2 px offset), 2.5.7 (no drag-only interactions), 2.5.8 (touch target ≥ 24 × 24 CSS px; ≥ 44 × 44 preferred), 3.2.6 (consistent help — "Contact" link in same footer location).
- `<html lang="en-US">` (already set in `apps/ui/app/layout.tsx`, verified).

**Motion-reduce gate**: `@media (prefers-reduced-motion: reduce)` overrides all motion tokens in `globals.css`. CI smoke test in a `prefers-reduced-motion` snapshot asserts no animations remain (durations ≤ 0.01 ms).

**Focus management**: visible focus on every interactive element. The focus ring is a single system token (`--sys-focus-ring`) consumed via `:focus-visible` or the `<FocusRing>` primitive. No bespoke focus styles per component.

**Cookie inventory**: zero non-essential cookies on `/` and audience landings at v1 (per ADR-034 §6). App Insights uses 1st-party cookie or sessionStorage; privacy notice ships in the footer. Marketing cookies trigger a consent-banner requirement before merge.

### 6. Cleanup contract

The contract above can only activate after the legacy artifacts are removed. The cleanup PR is **net-new** and lands on the same merge train as this ADR's reference work. It does:

1. **Rename `apps/ui/package.json` field `"name"`** from `"d-board"` to `"@hph/ui"` (RC-6 fix).
2. **Audit and remove dead-weight dependencies** with no live consumer on the marketing surface (verified present today): `@stripe/react-stripe-js`, `@reduxjs/toolkit`, `react-redux`, `recharts`, `react-star-ratings`, `react-popper`, `react-select`, `react-switch`, `nprogress`, `flatted`, `lodash`. Demo-only dependencies move to a `(demo)` route group lazy-loaded on demand (RC-6 fix).
3. **Delete legacy d-board files**: top-level `apps/ui/components/{navbar-1,left-sidebar-1,left-sidebar-2,right-sidebar-1}.tsx`; the `apps/ui/layouts/` tree (`centered/`, `centered-form/`, `e-commerce/`, `layout-1/`, `index.tsx`); the global vendor CSS imports in `apps/ui/app/layout.tsx` (RC-3, RC-4 fix).
4. **Hard-delete both legacy Tailwind configs**: `apps/ui/tailwind.config.ts` and `apps/ui/tailwind.config.js`. Replace with the Tailwind 4 `@theme` CSS-first model in `apps/ui/src/styles/tokens/brand.css` (RC-1 fix).
5. **Replace `apps/ui/app/page.tsx`** (currently `<ExecutiveDemoPage />`) with the audience-router `<HomeSplitHero>` from ADR-034 §4. The demo cockpit moves to `/demo` under the `(demo)` route group (deferred) or is deleted (RC-5 fix).
6. **Migrate the atomic tree** from `apps/ui/components/{atoms,molecules,organisms,templates}/` to `apps/ui/src/components/{primitives,composites,shells}/` per the §3 contract. This happens after the ADR-033 refactor moves `apps/ui/app/` to `apps/ui/src/app/`. Remove `apps/ui/components/ATOMIC_README.md` (RC-3, RC-10 fix).
7. **Land the bundle-budget and `axe-core` CI workflows** as net-new artifacts (workflows referenced in §5 do not exist on `main` today).

Until the cleanup PR ships, the contract in §1–§5 is advisory. The design-system contract activates only when the cleanup PR is merged.

## Consequences

### Positive

- Three-layer token architecture eliminates the regression mode where competing palettes (warm `--hp-*`, Ocean Blue, legacy green) co-resolve unpredictably. One naming convention, lint-enforced.
- Dual-audience theming via route-level shells means component primitives stay neutral and reusable; audience switching is a CSS variable rebind, not a component rewrite.
- Server-component default + bundle budget per route segment prevents the next "marketing site shipping a Redux store" failure mode.
- Quality gates (axe-core, bundle-size, motion-reduce, focus, contrast) make the design-system PR review deterministic — allow / reject verdicts rather than taste arguments.
- Cleanup contract makes "paint over the previous attempt" mechanically impossible; legacy artifacts are deleted before new code lands.
- Documentation matches code from day one — ATOMIC_README's docs-vs-code mismatch (RC-10) is replaced by per-primitive README files generated during the migration.
- Future RTL support is feasible without component rewrites because spacing uses logical CSS properties from v1.

### Negative / Trade-offs

- Three-layer token discipline costs more in initial setup than a single-layer flat palette. Mitigated by shipping system + reference at v1; component tokens land on demand.
- `light-dark()` syntax is Baseline 2024; non-Chromium evergreen browsers needed a fallback path (`@supports` + `prefers-color-scheme` media query) until the feature universalizes. Mitigated by a single fallback block at the system layer (~30 lines).
- Migrating the atomic tree (`atoms/` / `molecules/` / `organisms/` / `templates/`) to `primitives/` / `composites/` / `shells/` is a real refactor cost. Mitigated by doing it once, in the cleanup PR sequence, after the ADR-033 refactor establishes the `src/` root.
- Storybook deferral means design-system PRs cannot show side-by-side retailer / builder palette diffs at v1. Mitigated by manual screenshots in the design-token PR description until Storybook lands.
- CI gate count increases (axe-core, bundle-size, link checker, lint, motion-reduce). Mitigated by gates running in parallel; total CI overhead < 90 seconds for typical UI PR.
- Dependency removal (Redux, Stripe, recharts) breaks any internal admin tooling that depends on those packages. Mitigated by moving demo-only deps under the `(demo)` route group with lazy loading.

### Risks and Mitigations

| Risk | Mitigation |
|---|---|
| A future ADR-033 amendment materially changes its §1 directory contract and invalidates this ADR's §1, §2, §6 file paths. | The same PR must update this ADR's file-path references. |
| A future ADR-034 amendment materially changes its §3 token-file layout and invalidates this ADR's §1 file organization. | The same PR must update this ADR's token and file-organization references. |
| `light-dark()` fallback block goes stale as browser support universalizes; the fallback becomes dead code. | Quarterly review of browser support; remove fallback when target audience baseline reaches 100% (estimated 12 months). |
| Bundle budget numbers are forward-looking; first cutover may show real measurements substantially higher or lower. | Numbers tagged "initial budget, revisited at first cutover." Real measurements after cleanup PR set the v1.1 numbers; CI gate enables only after EG-7 verification. |
| `axe-core` CI gate becomes flaky against dynamic content; PRs blocked for unrelated regressions. | Gate runs against static preview environments only; dynamic content (search results, agent responses) is mocked in test fixtures. Failure threshold is `serious` + `critical` only — `moderate` and `minor` are warnings. |
| Migrating the atomic tree breaks consumers (pages currently importing `@/components/atoms/Button`). | Cleanup PR keeps a temporary barrel re-export at the old path during migration; barrel is removed in the same PR after all imports are updated. |
| Dependency removal breaks an undocumented consumer in `apps/ui/`. | `depcheck` (already in devDependencies, verified) audit before removal. Each removed dep gets a one-line PR comment confirming zero internal consumers. |
| `next/font` offline fallback degrades font appearance under restrictive corporate networks. | `adjustFontFallback: true` and a tightly tuned font-fallback metric so layout shift is minimized. CLS budget catches regressions. |
| Cleanup PR is too large to review safely. | Cleanup PR is split into ordered sub-PRs (rename + deps audit; legacy delete; tailwind migration; component-tree migration; CI workflow add); each sub-PR is independently revertible. |
| Tailwind 4 `@theme` CSS-first model evolves and breaks our token file structure. | Tailwind 4 is at 4.2.2 (verified in `apps/ui/package.json`); the `@theme` model is stable in the 4.x line. Pin minor version in `package.json`; review on each Tailwind 4.x minor update. |

## Alternatives Considered

### Alternative A — Single flat palette, no three-layer token architecture

Rejected. The forensic audit established that the previous attempt failed precisely because the project skipped the layering discipline. Without `--ref-` / `--sys-` / `--comp-` separation, the next attempt regresses to RC-2 (three competing palettes co-existing).

### Alternative B — Keep atomic-design naming (atoms / molecules / organisms / templates)

Rejected on naming, accepted on intent. The atomic-design metaphor is preserved (small primitives compose into complex surfaces), but the names (`atoms` / `molecules` / `organisms`) are dropped in favor of responsibility-based names (`primitives` / `composites` / `shells`). This is the §52 locked decision from the improvement plan. ADR-012 is superseded on naming only.

### Alternative C — CSS-in-JS (styled-components, emotion, vanilla-extract)

Rejected. CSS-in-JS in App Router requires extra configuration (registry pattern, hydration mismatch risks) and is incompatible with server components by default. ADR-033 commits to server components for the marketing surface; CSS-in-JS would force client components everywhere.

### Alternative D — Defer the cleanup, paint new tokens over the existing tree

Rejected. The forensic audit noted that this is exactly what produced the failure mode. Painting over multiplies pedigrees; the cost of cleanup is two PRs (cleanup + replacement), versus an indefinite tail of reconciliation PRs.

### Alternative E — One audience, one palette, defer dual theming to v2

Rejected. ADR-034 §1 pins one-brand-two-cognitive-models as a load-bearing contract; deferring it means deferring ADR-034's audience-segmented IA, which has independent value.

## Implementation

> **Implementation enforcement**: this ADR is Accepted on the contract (§1–§6 above), but the cleanup PR (`feat(ui): apply ADR-035 design-system cleanup contract`), the new token CSS files (`apps/ui/src/styles/globals.css` + `apps/ui/src/styles/tokens/{brand,retailer,builder}.css` + `tokens/CONTRAST.md`), the deletion of legacy configs / components / layouts, and the bundle-budget + axe-core CI workflows are net-new artifacts that MUST land in the same merge train as this ADR's reference work. Until all of those exist, the design-system contract is advisory; the contract activates only when the cleanup PR ships.

| Component | File / Location | Change | State |
|---|---|---|---|
| ADR | `docs/architecture/adrs/adr-035-ui-design-system.md` | This file | Net-new (this PR) |
| ADR index | `docs/architecture/ADRs.md` | Append ADR-035 row | This PR |
| Tokens — brand | `apps/ui/src/styles/tokens/brand.css` | `@theme` block + reference tokens + audience-neutral system tokens; `light-dark()` bindings + fallback | Net-new; depends on ADR-033 refactor |
| Tokens — retailer | `apps/ui/src/styles/tokens/retailer.css` | Warm reference + `[data-audience="retailer"]` system bindings | Net-new |
| Tokens — builder | `apps/ui/src/styles/tokens/builder.css` | Cool reference + `[data-audience="builder"]` system bindings | Net-new |
| Tokens — contrast | `apps/ui/src/styles/tokens/CONTRAST.md` | Documented contrast ratios per token pair | Net-new |
| Globals | `apps/ui/src/styles/globals.css` | ≤ 60 lines: imports + cascade-layer order + base reset | Net-new |
| Shells | `apps/ui/src/components/shells/{RetailerShell,BuilderShell,DeployShell,HomeShell}.tsx` | Set `data-audience` + `audience-*` class; import section tokens | Net-new |
| Primitives | `apps/ui/src/components/primitives/<Primitive>/` | 13 neutral building blocks per §3 list | Net-new (migrated from `apps/ui/components/atoms/`) |
| Composites | `apps/ui/src/components/composites/<Composite>/` | Opinionated, pattern-named composites per §3 list | Net-new (migrated from `apps/ui/components/molecules/` and `organisms/`) |
| Barrel | `apps/ui/src/components/index.ts` | Single public surface; deep imports rejected | Net-new |
| Lint — deep imports | `apps/ui/eslint.config.mjs` (or `.eslintrc.json` until ADR-033 flat-config migration) | `no-restricted-imports` rule rejects deep imports across `primitives/` ↔ `composites/` ↔ `shells/` tiers; complements ADR-033's feature-isolation rule | Net-new |
| Cleanup — package | `apps/ui/package.json` | Rename `"name"` to `"@hph/ui"`; remove dead-weight deps; replace `react-icons` with tree-shakable library | This PR's cleanup |
| Cleanup — Tailwind | `apps/ui/tailwind.config.ts`, `apps/ui/tailwind.config.js` | Hard-delete both | Cleanup PR |
| Cleanup — globals | `apps/ui/app/globals.css` | Migrated to `apps/ui/src/styles/`; old file deleted | Cleanup PR |
| Cleanup — layout | `apps/ui/app/layout.tsx` | Remove nine global vendor CSS imports; vendor CSS moves to `(demo)` route group or is deleted | Cleanup PR |
| Cleanup — home | `apps/ui/app/page.tsx` | Replace `<ExecutiveDemoPage />` with `<HomeSplitHero>` per ADR-034 §4; demo moves to `/demo` (deferred) or is deleted | Cleanup PR |
| Cleanup — legacy components | `apps/ui/components/{navbar-1,left-sidebar-1,left-sidebar-2,right-sidebar-1}.tsx`, `apps/ui/layouts/` tree | Hard-delete | Cleanup PR |
| Cleanup — stale docs | `apps/ui/components/ATOMIC_README.md` | Hard-delete; replaced by per-primitive README written during migration | Cleanup PR |
| CI — bundle budget | `.github/workflows/ui-quality.yml` (or successor) | Add `@next/bundle-analyzer` + `--budget-json` from `apps/ui/budgets.json`; gate active after EG-7 | Net-new |
| CI — axe-core | `.github/workflows/ui-quality.yml` | Add `axe-core` step against retailer / builder / deploy preview environments; merge-blocking on `serious` + `critical` | Net-new |
| CI — motion-reduce | `.github/workflows/ui-quality.yml` | Smoke test in `prefers-reduced-motion` snapshot; assert duration ≤ 0.01 ms | Net-new |
| Lint — token names | `apps/ui/.stylelintrc` (or stylelint config) | Custom rule: no custom property without `--ref-` / `--sys-` / `--comp-` / Tailwind reserved prefix | Net-new |
| Lint — inline bezier | `apps/ui/eslint.config.mjs` (or `.eslintrc.json` until ADR-033 flat-config migration) | Regex rule: `cubic-bezier(` in `className` strings is an error | Net-new |

## Verification

- **Filesystem reality check** is part of every PR review against this ADR; the diagnostic table in §Context lists what is on `main` at the time of writing, with deviations from the staging-memory text noted inline.
- **Lint gate**: a stylelint custom rule rejects any `--<name>` not prefixed `--ref-` / `--sys-` / `--comp-` / Tailwind reserved. PR fails on first match.
- **Bundle budget**: Lighthouse + `@next/bundle-analyzer` enforce per-route JS / CSS budgets after cleanup PR (EG-7) verification. Initial budget revisited at first cutover.
- **Accessibility**: `axe-core` CI gate green on retailer / builder / deploy preview environments (zero `serious` + `critical`); manual keyboard pass on `/`, one `/retailers/*` page, one `/builders/*` page captured in the design-token PR description; contrast ratios documented in `tokens/CONTRAST.md`.
- **Motion-reduce**: smoke test in a `prefers-reduced-motion` snapshot asserts no animations remain (animation-duration / transition-duration ≤ 0.01 ms across the page).
- **Server-component default**: bundle analyzer asserts marketing-surface routes do not bundle MSAL / Stripe / Recharts. PR fails if any of those packages reaches `/`, `/retailers/*`, `/builders/*`, `/deploy/*`.
- **No deep imports**: ESLint `no-restricted-imports` rejects deep imports across `primitives/` ↔ `composites/` ↔ `shells/` tiers. The barrel `@/components` is the API.
- **Token-only motion**: ESLint regex rejects inline `cubic-bezier(` in `className`; stylelint rejects bezier curves outside the brand token file.

## Pattern References

- **Three-layer design tokens** — Material Design 3 token model; Adobe Spectrum token guide; GitHub Primer Primitives. The `--ref-` / `--sys-` / `--comp-` separation is the industry-standard pattern for design systems at scale.
- **Modular monolith** — microservices.io. Component tiers (`primitives` / `composites` / `shells`) are the UI-tier expression of ADR-033's modular-monolith feature isolation.
- **Strangler Fig** — microservices.io. The cleanup PR sequence migrates the atomic tree section by section; the legacy `apps/ui/components/{atoms,molecules,organisms,templates}/` tree is strangled by `apps/ui/src/components/{primitives,composites,shells}/`.
- **Cascade Layers** (CSS) — W3C CSS Cascade Layers spec. The `@layer reset, theme, base, components, utilities, app;` declaration is the cascade-management pattern that prevents specificity wars.

## Out of scope (tracked separately)

- **Per-page UX-pattern authoring** — content of `/`, `/retailers/*`, `/builders/*`, `/deploy/*` pages. Tracked under the Section 40 / 54 capability epics and ADR-034 capability 44.
- **mkdocs-material theme overrides** — `/docs/*` content and theme. Tracked under Section 42 / capability 42.
- **Storybook setup** — deferred until the new component library stabilizes per the §52 locked decision.
- **Internal Figma curation** — workspace asset, not a code artifact.
- **RTL support** — deferred to v2; logical CSS properties from v1 keep the migration cheap.
- **`/docs/*` budget enforcement mechanism** — lives in the docs pipeline, not the Next.js build.

## References

- [ADR-011 — Next.js 15 with App Router for Frontend (revised by ADR-033 to Next.js 16)](adr-011-nextjs-app-router.md)
- [ADR-012 — Atomic Design System for Component Library (superseded on naming convention only)](adr-012-atomic-design-system.md)
- [ADR-018 — Git Branch Naming Convention](adr-018-branch-naming-convention.md)
- [ADR-033 — UI as a Modular Monolith on Static Web Apps (Path 2)](adr-033-ui-modular-monolith-on-swa.md)
- [ADR-034 — Audience-Segmented Information Architecture for the UI](adr-034-audience-segmented-ia.md)
- [Repository purpose canonical statement](../../../.github/instructions/repository-purpose.instructions.md)
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Tailwind 4 CSS-first `@theme`: https://tailwindcss.com/blog/tailwindcss-v4
- Material Design 3 tokens: https://m3.material.io/foundations/design-tokens/overview
- Core Web Vitals thresholds: https://web.dev/articles/vitals
