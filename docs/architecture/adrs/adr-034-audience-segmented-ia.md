# ADR-034: Audience-Segmented Information Architecture for the UI

**Status**: Accepted (Extends ADR-033)
**Date**: 2026-05-08
**Deciders**: Architecture Team, Ricardo Cataldi
**Tags**: frontend, information-architecture, design-tokens, accessibility, sales-surface
**References**: [ADR-011](adr-011-nextjs-app-router.md), [ADR-012](adr-012-atomic-design-system.md), [ADR-018](adr-018-branch-naming-convention.md), [ADR-033](adr-033-ui-modular-monolith-on-swa.md)

## Status

Accepted. **Extends ADR-033**; does not supersede it.

ADR-033 is accepted and this ADR extends its modular-monolith directory contract. Future amendments to ADR-033 that materially change its §1 directory contract must update this ADR's Implementation table in the same PR.

## Context

`apps/ui/` is the platform's primary sales surface. It must serve two audiences with materially different cognitive models without diluting either:

1. **External retailers** (Retail CTO/CIO, VP Engineering, Heads of eCommerce / CRM / Supply Chain) — business-case-first; want a clear value story, low-friction trial path, predictable cost, and an exit story. Decision style is product-page tone: hero outcome, warm accent, large CTAs, social proof.
2. **Internal Microsoft + open-source builders** (Field, ATU, GBB, partner sellers, retail engineering, OSS contributors) — evidence-first; want technical depth, ADRs, comparable wins, sales artifacts. Decision style is documentation tone: dense layouts, prominent code, neutral palette, deep links.

Three failure modes need to be ruled out at the IA layer, not at the page layer:

- **Single homogeneous skin** — site reads as "another open-source repo with a marketing skin." Both audiences bounce.
- **Two microsites** — splits the SEO surface, the trust signal, the auth boundary, and doubles maintenance. Brand coherence collapses.
- **Soft persona toggle on a unified IA** — assumes everyone arrives at `/`. They don't. SEO, sales links, and ADR cross-references land users directly in the middle of either funnel. Each landing must work as a valid entry point.

This ADR locks the IA contract that the modular monolith from [ADR-033](adr-033-ui-modular-monolith-on-swa.md) renders. The decision is grounded in the canonical positioning at [`.github/instructions/repository-purpose.instructions.md`](../../../.github/instructions/repository-purpose.instructions.md) — `lib/` is a framework, `apps/` is a product, both are first-class — which forces the UI to address both adoption paths with equal weight.

The locked decisions in this ADR were converged during the round-of-3 deliberation captured in the UI go-to-market plan (BusinessStrategist proposed; UIDesigner adversarial; joint synthesis). Three hard rules from that plan are pinned here as ADR contract:

- **No vanity metrics on retailer-facing pages.** Every number on a `/retailers/*` page carries a confidence interval and a cited methodology.
- **One brand, one domain.** No microsites; segmentation lives in route groups and design tokens, not URLs.
- **5-second test before merge.** Any change to home or top-level navigation must pass a 5-second test with at least 3 retailer-persona reviewers and 3 internal-persona reviewers.

## Decision

### 1. Single domain, three top-level paths

One domain. Three top-level audience paths plus a shared documentation path and a default home:

```text
holiday-peak.example  (Static Web Apps; see ADR-033)
│
├── /                      Home — split hero, equal-weight CTAs (retailer / builder)
├── /retailers             Audience: external retailers (warm tokens, product tone)
├── /builders              Audience: Microsoft internal + open-source devs (cool tokens, docs tone)
├── /deploy                One-click deployment portal (neutral tokens, task-focused)
└── /docs                  mkdocs Material output mounted as a sub-path
```

No microsites. No second domain. Splitting cognitive models is done with route groups and design tokens, not with separate URLs. This pins the **"one brand, one domain"** hard rule as ADR contract.

`/docs/*` content rules and build pipeline are out of scope for this ADR (tracked under capability 42). `/deploy/*` flow is out of scope (tracked under capability 43, with security guardrails).

### 2. Route groups in Next.js App Router

Audience segmentation is implemented as **Next.js App Router route groups** under `apps/ui/src/app/`:

```text
apps/ui/src/app/
├── layout.tsx                       # root layout — shared shell, brand tokens, LaneSwitch slot
├── page.tsx                         # home — HomeSplitHero
├── (retailer)/                      # route group — applies retailer tokens via section layout
│   ├── layout.tsx                   # imports tokens/retailer.css; SectionShell variant="retailer"
│   ├── retailers/
│   │   ├── page.tsx                 # /retailers
│   │   ├── value/page.tsx           # /retailers/value
│   │   ├── agents/page.tsx          # /retailers/agents
│   │   ├── roi/page.tsx             # /retailers/roi
│   │   ├── comparators/page.tsx     # /retailers/comparators
│   │   ├── case-studies/page.tsx    # /retailers/case-studies
│   │   └── security/page.tsx        # /retailers/security
├── (builder)/
│   ├── layout.tsx                   # imports tokens/builder.css; SectionShell variant="builder"
│   ├── builders/
│   │   ├── page.tsx                 # /builders
│   │   ├── architecture/page.tsx
│   │   ├── adrs/page.tsx
│   │   ├── patterns/page.tsx
│   │   ├── telemetry/page.tsx
│   │   └── enablement/page.tsx      # role-gated; tracked separately under capability 45
├── (deploy)/
│   ├── layout.tsx                   # imports tokens/brand.css only; SectionShell variant="deploy"
│   └── deploy/
│       ├── page.tsx
│       ├── catalog/page.tsx
│       ├── configure/page.tsx
│       ├── preflight/page.tsx
│       └── track/[id]/page.tsx
```

**Relationship to ADR-033 §1**: Route groups `(retailer)`, `(builder)`, `(deploy)` are the **public-facing audience surface** under `src/app/`. They consume — but do not replace — the per-bounded-context internal feature modules at `src/features/<context>/` defined in ADR-033 §1 (modular-monolith directory contract). Page components inside the route groups import from `src/features/<context>/index.ts` (CRM, eCommerce, inventory, logistics, product-management, search, truth) and from `src/shared/`. Cross-feature imports remain forbidden by the ESLint `no-restricted-imports` rule pinned in ADR-033.

The route-group structure under `src/app/` is **net-new** — it is introduced in the same refactor PR(s) that move the current flat `apps/ui/app/` layout to `apps/ui/src/app/` per ADR-033. Until the ADR-033 refactor lands, this contract is forward-looking and not yet enforced.

Next.js 16 App Router (revised by ADR-033 from the Next.js 15 baseline in [ADR-011](adr-011-nextjs-app-router.md)) is required for route groups; this is a load-bearing dependency.

### 3. Dual design-token system under one brand

Three CSS token files under `apps/ui/src/styles/tokens/` (net-new directory):

| File | Scope | Visual character |
|---|---|---|
| `tokens/brand.css` | Shared baseline. Logo, focus ring, typography scale base, spacing rhythm, motion timing, breakpoints. Imported by every section. | Brand-neutral. |
| `tokens/retailer.css` | Loaded only by `(retailer)/layout.tsx`. Warm accent (coral/terracotta family), generous spacing, hero-image-led layouts, larger CTA buttons, sans-serif headings via `next/font`. | Product-page tone. |
| `tokens/builder.css` | Loaded only by `(builder)/layout.tsx`. Cool slate, denser spacing, prominent code blocks (mono via `next/font`), neutral palette with deep-link emphasis. | Documentation tone. |

`(deploy)/layout.tsx` imports only `tokens/brand.css` — task-focused screens stay neutral so users at this step are not re-pitched.

Tailwind theme switches via the section route group (each section layout sets a `data-section` attribute that token CSS keys off, or per-section CSS variable overrides). `next/font` is the supported typography mechanism per ADR-011 / ADR-033. Storybook screenshots for both retailer and builder palettes are required on every design-system PR.

### 4. Persona-aware "switch-lane" component

A `<LaneSwitch>` component rendered by the root layout on **every page** (every section, every depth). Copy is section-aware:

| Current section | LaneSwitch copy |
|---|---|
| `/retailers/*` | *"Looking for the technical reference? Switch to the builder view →"* |
| `/builders/*` | *"Looking for the retailer business case? Switch to the retailer view →"* |
| `/` (home) | Both lanes shown via `<HomeSplitHero>`; LaneSwitch hidden in this case. |
| `/deploy/*` | LaneSwitch links back to whichever section the user came from (cookie-resolved; defaults to `/retailers/value`). |
| `/docs/*` | LaneSwitch suppressed; mkdocs has its own navigation chrome. |

Component contract:

- `<SectionShell variant="retailer|builder|deploy|docs|home">` — wraps each section, applies tokens, renders top-nav, breadcrumb, and `<LaneSwitch>` slot.
- `<LaneSwitch from="retailer|builder" to="retailer|builder">` — copy-aware, accessible (focus order, `aria-label`), ships in shared bundle.
- `<HomeSplitHero>` — two equal-weight CTAs, persona-detected default tab, 5-second-test certified before merge.

Copy is snapshot-tested. Accessibility (focus order, screen-reader labels, keyboard navigability) is verified via `axe-core` per §8.

### 5. 5-second test as a merge gate (CODEOWNERS-enforced)

Any change that touches `/`, `/retailers/*`, or `/builders/*` (i.e., the audience-segmented public surface) is gated by a structured 5-second test before merge. The **"5-second test before merge"** hard rule is pinned as ADR contract.

Enforcement mechanism:

1. A `.github/CODEOWNERS` (net-new) entry covers the audience-facing route paths and requires review by named persona pools — one pool of at least 3 retailer-persona reviewers (field-recruited from pilot contacts and external retailer customers, anonymized) and one pool of at least 3 internal-persona reviewers (from Field / ATU / GBB / retail engineering).
2. The PR template (net-new section under `.github/pull_request_template.md` or a path-conditional template) carries a structured 5-second-test questionnaire. Reviewers answer two questions on first cold view of the preview environment:
   - "Where would you click first?"
   - "What do you think this site offers?"
3. PR cannot merge until **at least 3 retailer-persona and 3 internal-persona reviewers** have submitted answers and at least one reviewer from each pool has approved. Anonymized responses are captured in the PR description as the audit trail.

The reviewer pool roster lives in `.github/audience-reviewers.md` (net-new) and is owned by BusinessStrategist + UIDesigner jointly. Roster rotation is reviewed quarterly; rotation is the primary mitigation against the gate degenerating into ceremony.

Until CODEOWNERS, the PR template addition, and the reviewer roster all land, the 5-second-test gate is documented review process tracked in the PR description, not a CODEOWNERS-required review. Their landing is part of the conditional-acceptance footnote in §Implementation.

### 6. Persona detection is a soft hint only

Persona detection is a **navigation reordering hint**, not a content gate.

Detection inputs:

- First interaction with a CTA on `/` writes a cookie `persona=retailer|builder` (90 days, `SameSite=Lax`, `Secure`, no other attributes).
- Query parameter `?as=retailer|builder` overrides the cookie for shareable links.

Allowed uses (exhaustive):

1. Reorder LaneSwitch CTA copy (already section-aware; cookie disambiguates `/deploy/*` and `/` repeat-visit defaults).
2. Pick the default tab on `/` for repeat visits.
3. Sort recommended-next-step lists in section landing pages.

Forbidden uses:

- Gate, hide, or remove content based on persona.
- Change pricing or any commercial term.
- Branch route handlers on persona (`if (persona === ...) return ...` is a defect; banned by lint rule).
- Personalize SEO meta or canonical URLs.

**Privacy contract**: the cookie contains only the literal string `retailer` or `builder`. No PII, no email, no IP, no fingerprint, no user identifier of any kind. The cookie is documented in the privacy notice that ships with the SWA. A user clearing cookies — or arriving with a `?as=` override — produces identical content for the same URL; only ordering of secondary links differs.

### 7. Each section is a valid landing page

Every page under `/retailers/*` and `/builders/*` ships, on its own, as a complete landing surface:

- Own `<title>`, `<meta name="description">`, Open Graph (`og:title`, `og:description`, `og:image`), Twitter card.
- Own hero (no shared "section landing" anti-pattern that delegates messaging to the parent section).
- Own breadcrumb.
- Persona-aware LaneSwitch in the footer.
- Sitemap segmented per section (`/sitemap-retailers.xml`, `/sitemap-builders.xml`, plus root `/sitemap.xml`).
- `og:image` distinct per audience: retailer images use the warm-token palette; builder images use the cool-token palette. Generated at build time from a single source so the two stay coherent.

This pins the IA against the "soft fork at home" failure mode where deep links degrade.

### 8. Accessibility contract

- Both palettes (`tokens/retailer.css` and `tokens/builder.css`) verified against **WCAG 2.2 AA** at the design-token PR. Documented contrast ratios per token pair (background / foreground, accent / background, focus ring / background) — minimum 4.5:1 for normal text, 3:1 for large text and UI components, recorded in `apps/ui/src/styles/tokens/CONTRAST.md` (net-new) alongside the token files.
- `axe-core` automated check runs in CI at the **route-group level** — three preview environments (retailer, builder, deploy) each pass `axe-core` with zero violations of `serious` or `critical` severity. CI gate is mandatory; no exception.
- Manual screen-reader pass on `/`, one `/retailers/*` page, and one `/builders/*` page is captured in the PR description on every design-token change.

### 9. Cross-references locked

- **ADR-033 §1** modular-monolith directory contract is **extended** by §2 of this ADR. Route groups are the public surface; feature modules at `src/features/<context>/` are the bounded-context internals. The two layers compose; neither replaces the other. This ADR does not modify the ESLint isolation rule pinned by ADR-033.
- **ADR-011** (revised by ADR-033 to Next.js 16 with App Router) — required for route groups; load-bearing.
- **"No vanity metrics on retailer-facing pages"** applies to all `/retailers/*` content. ROI numbers carry confidence intervals and cited methodology. This ADR pins the rule as content gate; the per-page enforcement lives in capability 44.
- **"One brand, one domain"** is pinned by §1 of this ADR.
- **"5-second test before merge"** is pinned by §5 of this ADR as a merge gate.

## Consequences

### Positive

- Both audiences land on a surface tuned to their decision style without splitting the SEO domain or the auth boundary.
- Deep links (SEO, ADR cross-references, sales artifacts) work as first-class entry points; no "soft fork at home" failure mode.
- LaneSwitch makes audience errors recoverable in one click, lowering bounce on cross-audience SEO traffic.
- Dual tokens encode the visual contract in code; design-system PRs see both palettes in one Storybook view, drift is visible.
- The 5-second-test merge gate makes the IA decision a continuous review property, not a one-time launch property.
- Persona detection as a soft hint avoids the personalization bug surface (A/B drift, gated content, leaked PII) entirely.

### Negative / Trade-offs

- Two design-token sets cost more to maintain than one. Mitigated by tokens living in one folder with mandatory dual-Storybook screenshots on every design-system PR (§3).
- The 5-second-test gate adds review latency on every change to home + audience landings. Mitigated by a pre-recruited reviewer pool with anonymized async response and quarterly rotation (§5).
- Per-section SEO meta and `og:image` generation add build-time cost. Mitigated by generating images from a shared source rather than authoring two copies.
- Route groups + section layouts add one layout layer between the root layout and pages. Acceptable; the alternative (per-page token import) is far more error-prone.
- CODEOWNERS-driven required reviews can stall merges when reviewer pools are short-staffed. Mitigated by the rotating roster and by allowing emergency override only via documented process owned by the architecture team.

### Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Dual design tokens drift over time, producing visual incoherence between `/retailers/*` and `/builders/*`. | Tokens live in one folder; design-system PRs require both palettes' Storybook screenshots; quarterly visual-diff audit by UIDesigner. |
| 5-second test degenerates into ceremony (reviewers rubber-stamp). | Reviewers are real personas (3 from external retailer pool, 3 from internal field pool); responses anonymous; roster rotated quarterly; questionnaire is structured and short. |
| Persona detection drifts into a content gate (a/b drift, gated content). | Code review enforces the rule "cookie reads only for reordering and default-tab." Lint rule bans `if (persona === ...) return ...` in route handlers and page components. |
| WCAG 2.2 AA fails on the warm retailer palette (low-contrast accent). | Accessibility is a merge gate at the design-token PR; no exceptions in CI; contrast ratios documented in `CONTRAST.md`. |
| Cross-section links bleed audiences (retailer reads dense docs and bounces). | LaneSwitch surfaces the easy way back from every page; telemetry on bounce-by-section flags pages that need a friendlier landing; capability 44/45 owns the per-page response. |
| Cookie-based detection runs into privacy review or browser tracking-prevention defaults. | Cookie contains only `retailer\|builder`, no PII, no fingerprint, no third-party domain; documented in privacy notice; clearing cookies is fully supported and produces identical content. |
| Route-group structure conflicts with future micro-frontend extraction. | Modular-monolith feature isolation per ADR-033 makes extraction cheaper. Route groups extract cleanly per section; the contract is reversible. |
| A future ADR-033 amendment materially changes its §1 directory contract and invalidates this ADR's §2. | The same PR must update this ADR's Implementation table if the §1 contract changes. |
| 5-second-test merge gate is unenforceable until CODEOWNERS lands. | CODEOWNERS, PR template, and reviewer roster are part of the conditional-acceptance footnote in §Implementation; until they land, the gate is documented review process, not CODEOWNERS-required. |

## Alternatives Considered

### Alternative A — Single homogeneous IA with a soft persona toggle

Rejected. Assumes everyone arrives at `/`. SEO, sales-deck links, and ADR cross-references land users mid-funnel. A homogeneous skin reads as "another open-source repo with marketing" to retailers and "marketing-overproduced docs" to builders — both bounce.

### Alternative B — Two microsites, two domains

Rejected. Splits the SEO surface, the trust signal, the auth boundary; doubles the maintenance and the design-system. Violates README.md hard rule 5.

### Alternative C — Single-token system, content-only differentiation

Rejected. The adversarial round established that visual tone (color temperature, density, type pairing) is the load-bearing signal for "where am I and is this for me?" within the 5-second window. Content alone cannot carry that signal at first paint.

### Alternative D — Persona detection as a hard fork (route on cookie)

Rejected on privacy and on personalization-bug risk. Hard forking on a cookie creates A/B drift, breaks SEO canonicals, and turns the cookie into a content gate. The soft-hint rule (§6) is the explicit guardrail against this failure mode.

## Implementation

> **Implementation enforcement**: this ADR is Accepted on the contract (§1–§9 above), but the following net-new artifacts MUST land on the same merge train as the §2 route-group refactor. Until all of these exist, the IA contract is authoritative but not yet fully enforced by automation:
>
> - `apps/ui/src/styles/tokens/{brand,retailer,builder}.css` and `apps/ui/src/styles/tokens/CONTRAST.md`.
> - Storybook configuration showing both retailer and builder palettes side-by-side.
> - `axe-core` CI job covering all three section preview environments.
> - `.github/CODEOWNERS` entries for `apps/ui/src/app/page.tsx`, `apps/ui/src/app/(retailer)/**`, `apps/ui/src/app/(builder)/**` requiring the audience-reviewer pools.
> - `.github/audience-reviewers.md` roster (BusinessStrategist + UIDesigner co-owned, quarterly rotation).
> - PR template section carrying the structured 5-second-test questionnaire (path-conditional or section in the global template).
> - Lint rule banning `if (persona === ...) return ...` in route handlers and page components.

The §2 refactor depends on the modular-monolith refactor pinned by ADR-033 §1 (move from flat `apps/ui/app/` to `apps/ui/src/app/`). This ADR does not duplicate that work; it adds the route-group layer on top.

| Component | File / Location | Change | State |
|---|---|---|---|
| ADR | `docs/architecture/adrs/adr-034-audience-segmented-ia.md` | This file | Net-new (this PR) |
| ADR index | `docs/architecture/ADRs.md` | Append ADR-034 row | This PR |
| Route-group shells | `apps/ui/src/app/(retailer)/layout.tsx`, `apps/ui/src/app/(builder)/layout.tsx`, `apps/ui/src/app/(deploy)/layout.tsx` | Section layouts that import the section's tokens, render `<SectionShell>`, and slot `<LaneSwitch>` into the footer. | Net-new; depends on ADR-033 refactor |
| Pages — retailer | `apps/ui/src/app/(retailer)/retailers/{value,agents,roi,comparators,case-studies,security}/page.tsx` | Per-page hero, breadcrumb, SEO meta, LaneSwitch in footer. Content tracked under capability 44. | Net-new; this ADR pins shape only |
| Pages — builder | `apps/ui/src/app/(builder)/builders/{architecture,adrs,patterns,telemetry,enablement}/page.tsx` | Same shape contract. `enablement` is role-gated under capability 45. | Net-new; this ADR pins shape only |
| Pages — deploy | `apps/ui/src/app/(deploy)/deploy/{catalog,configure,preflight,track/[id]}/page.tsx` | Task-focused; neutral tokens. Content tracked under capability 43. | Net-new; this ADR pins shape only |
| Home | `apps/ui/src/app/page.tsx` | `<HomeSplitHero>` with persona-detected default tab. | Net-new; depends on ADR-033 refactor |
| Tokens | `apps/ui/src/styles/tokens/{brand,retailer,builder}.css` | Three CSS files; documented contrast in `CONTRAST.md`. | Net-new |
| Components | `apps/ui/src/shared/layout/{SectionShell,LaneSwitch,HomeSplitHero}.tsx` | Shared layout primitives per §4 contract. | Net-new; lives in `src/shared/` per ADR-033 |
| Storybook | `apps/ui/.storybook/` (or equivalent) | Side-by-side retailer + builder palette views; mandatory on design-system PRs. | Net-new |
| Sitemaps | `apps/ui/src/app/sitemap.ts` (and per-section sub-sitemaps) | Segmented per section; root sitemap indexes the sub-sitemaps. | Net-new |
| Persona-detection middleware | `apps/ui/src/middleware.ts` (or per-page client component) | Reads `persona` cookie + `?as=` query; sets cookie on first CTA interaction. Soft-hint only per §6. | Net-new |
| Lint rule | `apps/ui/eslint.config.mjs` | Custom rule banning `if (persona === ...) return ...` in route handlers and pages; complements ADR-033 ESLint isolation. | Net-new |
| `axe-core` CI | `.github/workflows/ui-quality.yml` (or successor) | Adds `axe-core` step against retailer / builder / deploy preview environments; merge-blocking on `serious` or `critical` violations. | Net-new |
| CODEOWNERS | `.github/CODEOWNERS` | Path entries for audience-facing routes requiring audience-reviewer pools. | Net-new |
| Reviewer roster | `.github/audience-reviewers.md` | Pool roster for retailer + internal personas; quarterly rotation. | Net-new |
| PR template | `.github/pull_request_template.md` (or path-conditional template) | Structured 5-second-test questionnaire section. | Net-new |
| Privacy notice | `apps/ui/src/app/privacy/page.tsx` (or equivalent) | Documents the `persona` cookie scope and contents. | Update |

## Verification

- **5-second test**: structured questionnaire ("Where would you click first?" / "What do you think this site offers?") captured in the PR description for every change to `/`, `/retailers/*`, `/builders/*`. CODEOWNERS-required reviews from both pools.
- **Accessibility**: `axe-core` CI job green on retailer / builder / deploy preview environments (zero `serious` or `critical` violations); manual screen-reader pass on `/`, one `/retailers/*` page, and one `/builders/*` page captured in the design-token PR.
- **Contrast**: ratios per token pair documented in `apps/ui/src/styles/tokens/CONTRAST.md`; minimum 4.5:1 for normal text, 3:1 for large text and UI components.
- **SEO**: Lighthouse SEO score ≥ 90 on home and on at least one section landing per audience; per-page `<title>`, `<meta description>`, and Open Graph tags asserted via integration test; segmented sitemaps validated against the live route table.
- **LaneSwitch**: snapshot test per section asserting copy is correct; integration test asserting the component renders on every page outside `/docs/*` and `/`.
- **Persona-detection**: integration test asserts cookie + query-param contract — `?as=retailer` writes/overrides the cookie, cleared cookies produce identical content, no PII leaves the client.
- **Lint**: rule banning `if (persona === ...) return ...` covered by an intentional-failure test fixture in CI.

## Pattern References

- **Progressive disclosure** — content layers from outcome → details → source per audience.
- **Information scent** (Pirolli & Card) — every link names its destination in the user's terms; audience-segmented copy is the load-bearing signal.
- **Strangler Fig** — microservices.io. The route-group structure migrates section by section as part of the ADR-033 refactor; the flat `apps/ui/app/` layout remains until each section is migrated.
- **Modular Monolith** — ADR-033's feature isolation pattern; route groups are the public-facing layer that consumes the feature modules.

## Out of Scope

Tracked separately under the named capability epics:

- Content of `/retailers/*` value pages (capability 44).
- `/deploy/*` flow and security guardrails (capability 43).
- mkdocs-as-UI build pipeline at `/docs/*` (capability 42).
- Internal sales-enablement role-gating at `/builders/enablement/*` (capability 45).

## References

- [ADR-011 — Next.js 15 with App Router (revised by ADR-033 to Next.js 16)](adr-011-nextjs-app-router.md)
- [ADR-012 — Atomic Design System for Component Library](adr-012-atomic-design-system.md)
- [ADR-018 — Git Branch Naming Convention](adr-018-branch-naming-convention.md)
- [ADR-033 — UI as a Modular Monolith on Static Web Apps (Path 2)](adr-033-ui-modular-monolith-on-swa.md)
- [Repository purpose canonical statement](../../../.github/instructions/repository-purpose.instructions.md)
- WCAG 2.2 AA: https://www.w3.org/TR/WCAG22/
- Next.js App Router — Route Groups: https://nextjs.org/docs/app/building-your-application/routing/route-groups
