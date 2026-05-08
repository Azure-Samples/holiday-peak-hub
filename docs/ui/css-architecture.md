# UI CSS architecture (ADR-035 §49 / Issue #1058)

> **Status**: Active — landed via Issue #1058. Future amendments require an ADR-035 update.

The CSS surface in `apps/ui/` is organized in a strict cascade: **token layer → component layer → utility layer**. The token layer is split into three sub-layers per ADR-035 §49 (reference / system / component). All layers are imported in a deterministic order in [`apps/ui/app/globals.css`](../../apps/ui/app/globals.css), and `globals.css` itself is **≤ 60 lines (soft) / ≤ 80 lines (hard)** — enforced by the [`ui-css-architecture-gate`](../../.github/workflows/ui-css-architecture-gate.yml) workflow.

## File map

| File | Layer | Owner | Lines |
|---|---|---|---|
| [`apps/ui/app/globals.css`](../../apps/ui/app/globals.css) | Tailwind import + base reset + `prefers-reduced-motion` global override | UI design system | ≤ 60 (soft) / ≤ 80 (hard) |
| [`apps/ui/app/styles/tokens.reference.css`](../../apps/ui/app/styles/tokens.reference.css) | Reference layer (`@theme` — Tailwind utility tokens) | UI design system | ~60 |
| [`apps/ui/app/styles/tokens.system.css`](../../apps/ui/app/styles/tokens.system.css) | System layer (`--sys-*` audience-aware bindings via `light-dark()` and `[data-audience="…"]`) | UI design system | ~80 |
| [`apps/ui/app/styles/tokens.legacy-decorations.css`](../../apps/ui/app/styles/tokens.legacy-decorations.css) | Legacy `--hp-*` decorations (glass / glow / stage / shadows) for d-board / demo / dashboard routes only | Legacy d-board | ~70 |
| [`apps/ui/styles/tokens/brand.css`](../../apps/ui/styles/tokens/brand.css) | Section-shell brand tokens (audience accents, type scale, spacing rhythm) | UI design system | ~60 |
| [`apps/ui/styles/tokens/retailer.css`](../../apps/ui/styles/tokens/retailer.css) | Warm audience accent overrides bound through `[data-section="retailer"]` | Retailer | ~30 |
| [`apps/ui/styles/tokens/builder.css`](../../apps/ui/styles/tokens/builder.css) | Cool audience accent overrides bound through `[data-section="builder"]` | Builder | ~30 |
| [`apps/ui/styles/tokens/deploy.css`](../../apps/ui/styles/tokens/deploy.css) | Deploy-funnel slate accent overrides | Deploy | ~30 |
| [`apps/ui/app/styles/legacy-utilities.css`](../../apps/ui/app/styles/legacy-utilities.css) | Legacy `.btn-*`, `.card`, `.input`, `.link`, `.demo-*`, `.showcase-*` classes used by d-board / demo / dashboard routes | Legacy d-board | ~120 |

## Cascade-layer order

`globals.css` declares the cascade-layer order at line 11:

```css
@layer reset, theme, base, components, utilities, app;
```

Higher specificity later. This pins the order regardless of the import order of consumer files.

## Globals.css contents (≤ 60 lines)

`globals.css` carries **theme + base + motion-reduce only** — no component classes, no component-specific styles, no `.dark` override. The audience theme switch happens at the system-token layer through `light-dark()`.

The file contains:

1. `@import 'tailwindcss';` (line 1)
2. Token-layer imports (lines 2–9)
3. `@layer reset, theme, base, components, utilities, app;` (line 11)
4. `@layer base` block (lines 13–55):
   - Box-sizing reset
   - `html { color-scheme: light dark; -webkit-text-size-adjust: 100%; }`
   - `:focus-visible` rule consuming `var(--sys-focus-ring)`
   - Body background / color / font-family bound to `--sys-*`
   - `::selection`
   - `@media (prefers-reduced-motion: reduce)` global override (zeros all motion tokens to `0.01ms`)

## Reduced-motion contract

The `prefers-reduced-motion: reduce` block in `globals.css` does two things:

1. Sets the motion tokens (`--motion-fast`, `--motion-base`, `--motion-emphasized`) to `0.01ms !important` so that any consumer reading them via `var(--motion-*)` honors reduced motion automatically.
2. Sets `animation-duration`, `transition-duration`, and `scroll-behavior` to `0.01ms / auto` globally so that bespoke animations (legacy code) also stop without per-component opt-in.

**Spinners remain visible** — the rule zeros duration, not visibility.

## Vendor / legacy CSS at root layout (allowlisted baseline)

[`apps/ui/app/layout.tsx`](../../apps/ui/app/layout.tsx) imports a small allowlisted set of legacy / vendor CSS at the root layout level:

| Import | Reason | Cleanup target |
|---|---|---|
| `./globals.css` | Always imported at root | n/a |
| `@/css/main.css` | Legacy d-board base | Migrate to per-route imports under `/dashboard`, `/cart`, `/orders`, etc. |
| `@/css/animate.css` | `animate.css` global utility classes | Inline Tailwind animations or co-located modules |
| `@/css/components/nprogress.css` | NProgress route-change indicator | Scope to layouts that use the NProgress provider |
| `@/css/components/recharts.css` | Recharts theme overrides | Scope to dashboard layouts that render charts |
| `@/css/components/steps.css` | Steps molecule fallback | Inline Tailwind |
| `@/css/components/left-sidebar-3.css` | d-board sidebar | Scope to d-board layout |

The [`ui-css-architecture-gate`](../../.github/workflows/ui-css-architecture-gate.yml) workflow enforces this allowlist — **any new CSS import at the root layout fails the PR**. Cleanup of the existing baseline happens in follow-up PRs that move each vendor stylesheet into the leaf route segment that owns it.

## ESLint enforcement

The audience route groups (`app/(retailer)/**`, `app/(builder)/**`, `app/(deploy)/**`) and `components/shared/**` carry stricter rules than the rest of the app. From [`apps/ui/.eslintrc.json`](../../apps/ui/.eslintrc.json):

| Rule | Scope | Severity | Issue |
|---|---|---|---|
| No raw hex literals | audience routes + `components/shared/` | error | #1011 (PR #1067) |
| No persona branching | route handlers | error | #1012 (PR #1068) |
| Tier-import discipline (`no-restricted-imports`) | `components/{atoms,molecules,organisms}/` | error | #1057 (PR #1072) |
| **No inline `cubic-bezier(...)` in className** | **audience routes + `components/shared/`** | **error** | **#1058** |
| **No `dark:` Tailwind variants in className** | **audience routes + `components/shared/`** | **error** | **#1058** |
| **No `style={{}}` prop (`react/forbid-dom-props`)** | **audience routes + `components/shared/`** | **error** | **#1058** |

These rules apply only to the audience-IA route groups and the shared components folder. Legacy d-board code (under `/dashboard`, `/cart`, `/orders`, etc.) is grandfathered.

## What about stylelint?

Stylelint is **not** adopted in this PR. The `globals.css` line-count gate, the `cubic-bezier`-in-className ESLint rule, the `dark:`-in-className ESLint rule, and the no-`style={{}}`-in-audience-routes rule cover most of the contract intent. A follow-up issue can adopt stylelint for the remaining acceptance criteria (L-1 token-prefix discipline, L-2 `declaration-no-important`, L-9 redundant `@apply`, L-10 module-class-name convention).

## Motion vocabulary

Motion tokens are declared in `tokens.reference.css` inside `@theme`:

| Token | Value |
|---|---|
| `--motion-fast` | `120ms` |
| `--motion-base` | `200ms` |
| `--motion-emphasized` | `320ms` |
| `--ease-base` | `cubic-bezier(0.2, 0, 0, 1)` |
| `--ease-emphasized` | `cubic-bezier(0.05, 0.7, 0.1, 1)` |

Component code consumes them through Tailwind utilities (`duration-fast`, `duration-base`, `duration-emphasized`, `ease-base`, `ease-emphasized`) or directly via `var(--motion-*)` in CSS Modules.

**No bespoke `cubic-bezier(…)` in component code** — the ESLint rule rejects it inside audience routes and `components/shared/`.

## Future cleanup

Follow-up issues track:

1. Per-route migration of vendor / legacy CSS off the root layout.
2. Stylelint adoption for L-1 / L-2 / L-9 / L-10.
3. Migration of `.btn-*` / `.card` / `.input` / `.link` / `.showcase-*` / `.demo-*` legacy classes to Tailwind utilities or co-located CSS Modules — once consumers are migrated to the new component library at `apps/ui/components/{atoms,molecules,templates}/`.

## References

- ADR-035 — UI design system contract — [`docs/architecture/adrs/adr-035-ui-design-system.md`](../architecture/adrs/adr-035-ui-design-system.md)
- ADR-034 — Audience-segmented IA — [`docs/architecture/adrs/adr-034-audience-segmented-ia.md`](../architecture/adrs/adr-034-audience-segmented-ia.md)
- Design tokens — [`docs/ui/design-tokens.md`](./design-tokens.md)
- Five-second test — [`docs/governance/five-second-test.md`](../governance/five-second-test.md)
