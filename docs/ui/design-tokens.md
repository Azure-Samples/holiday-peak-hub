# Design tokens — Holiday Peak Hub UI

**Owner**: UI design system
**Origin**: ADR-035 §50–52, Issue #1056
**Last updated**: 2026-05-08

The Holiday Peak Hub UI runs a **three-layer design-token system** on
Tailwind 4's CSS-first `@theme` API. There is no `tailwind.config.ts` /
`tailwind.config.js` — both were removed in [#1056](https://github.com/Azure-Samples/holiday-peak-hub/issues/1056)
to enforce a single source of truth.

## Layers

| Layer       | Prefix(es)                                                  | Where it lives                                              |
| ----------- | ----------------------------------------------------------- | ----------------------------------------------------------- |
| Reference   | `--color-*`, `--font-*`, `--radius-*`, `--motion-*`, `--ease-*` | `apps/ui/app/globals.css` inside `@theme`                  |
| System      | `--sys-*`                                                   | `apps/ui/app/styles/tokens.system.css`                      |
| Component   | `--comp-*`                                                  | Per-component, in `apps/ui/components/shared/<Component>.tsx` |
| Brand-scoped (transitional) | `--hp-*`                                  | `apps/ui/styles/tokens/{brand,retailer,builder,deploy}.css` |

> The `--hp-*` aliases survive in this PR so existing components keep
> rendering. F4 (Issue #1058) prunes them once consumers migrate to
> `--sys-*` and `--comp-*`.

## Naming convention

```
--<layer>-<category>-<role>[-<state>]
```

Examples: `--color-warm-500` (reference), `--sys-action-primary-hover`
(system, role + state), `--comp-card-padding-block` (component slot).

A custom property that does not start with one of the layer prefixes
(`--ref-`, `--sys-`, `--comp-`, `--hp-`) **or** a Tailwind-reserved prefix
(`--color-`, `--font-`, `--spacing-`, `--radius-`, `--ease-`, `--motion-`)
is rejected by the `stylelint` rule introduced in F4 (#1058).

## Reference layer (`@theme`)

### Color — warm (retailer cognitive model)

| Token              | OKLCH                       | Notes                              |
| ------------------ | --------------------------- | ---------------------------------- |
| `--color-warm-50`  | `oklch(0.97 0.02 65)`       | Warm tint background               |
| `--color-warm-100` | `oklch(0.94 0.04 60)`       | Soft warm surface                  |
| `--color-warm-200` | `oklch(0.88 0.07 55)`       | Warm divider                       |
| `--color-warm-400` | `oklch(0.66 0.13 50)`       | Warm hover hint                    |
| `--color-warm-500` | `oklch(0.55 0.135 50)`      | Retailer action primary            |
| `--color-warm-600` | `oklch(0.48 0.135 48)`      | Retailer action hover              |
| `--color-warm-700` | `oklch(0.41 0.12 45)`       | Pressed state (reserved)           |
| `--color-warm-900` | `oklch(0.27 0.09 40)`       | High-emphasis warm text on light   |

### Color — cool (builder & deploy cognitive model)

| Token              | OKLCH                       | Notes                              |
| ------------------ | --------------------------- | ---------------------------------- |
| `--color-cool-50`  | `oklch(0.97 0.02 250)`      | Cool tint background               |
| `--color-cool-100` | `oklch(0.93 0.04 250)`      | Soft cool surface                  |
| `--color-cool-200` | `oklch(0.86 0.08 252)`      | Cool divider                       |
| `--color-cool-400` | `oklch(0.55 0.18 260)`      | Cool hover hint                    |
| `--color-cool-500` | `oklch(0.44 0.215 264)`     | Builder action primary             |
| `--color-cool-600` | `oklch(0.38 0.21 264)`      | Builder action hover               |
| `--color-cool-700` | `oklch(0.32 0.18 264)`      | Pressed state (reserved)           |
| `--color-cool-900` | `oklch(0.20 0.10 264)`      | High-emphasis cool text on light   |

### Color — neutral

| Token                | OKLCH               |
| -------------------- | ------------------- |
| `--color-neutral-50`  | `oklch(0.98 0 0)`  |
| `--color-neutral-100` | `oklch(0.96 0 0)`  |
| `--color-neutral-200` | `oklch(0.92 0 0)`  |
| `--color-neutral-400` | `oklch(0.70 0 0)`  |
| `--color-neutral-600` | `oklch(0.50 0 0)`  |
| `--color-neutral-800` | `oklch(0.30 0 0)`  |
| `--color-neutral-900` | `oklch(0.18 0 0)`  |
| `--color-neutral-950` | `oklch(0.10 0 0)`  |

### Typography

| Token         | Value                                                                  |
| ------------- | ---------------------------------------------------------------------- |
| `--font-sans` | `'Inter', ui-sans-serif, system-ui, -apple-system, sans-serif`         |
| `--font-mono` | `'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace`           |

`next/font` wires the actual webfont loading; the `@theme` value is the
fallback chain.

### Radius

| Token         | Value     |
| ------------- | --------- |
| `--radius-sm` | `0.5rem`  |
| `--radius-md` | `0.75rem` |
| `--radius-lg` | `1rem`    |

### Motion

| Token                 | Value      | Use case                                 |
| --------------------- | ---------- | ---------------------------------------- |
| `--motion-fast`       | `120ms`    | Hover, button press                      |
| `--motion-base`       | `200ms`    | Default UI transitions                   |
| `--motion-emphasized` | `320ms`    | Page transitions, modal enter/exit       |
| `--ease-base`         | `cubic-bezier(0.2, 0, 0, 1)`         | Standard easing               |
| `--ease-emphasized`   | `cubic-bezier(0.05, 0.7, 0.1, 1)`    | Spatial / emphasised motion   |

`@media (prefers-reduced-motion: reduce)` zeros all four motion tokens to
`0.01ms` AND zeros animation/transition durations globally. Spinners stay
visible — only their duration goes to zero.

## System layer

System tokens are role-named, audience-aware, and theme-aware. They live
in `apps/ui/app/styles/tokens.system.css` and bind to reference tokens
under three selectors:

| Selector                          | Cognitive model | Action accent           |
| --------------------------------- | --------------- | ----------------------- |
| `:root, [data-audience="neutral"]` | Neutral (warm action default) | `--color-warm-500` |
| `[data-audience="retailer"]`      | Warm            | `--color-warm-500`      |
| `[data-audience="builder"]`       | Cool            | `--color-cool-500`      |
| `[data-audience="deploy"]`        | Cool            | `--color-cool-500`      |

`SectionShell` (`apps/ui/components/shared/SectionShell.tsx`) emits both
the `data-audience` attribute and a matching `audience-*` className.

### Roles defined at the system layer

| Token                              | Purpose                                  |
| ---------------------------------- | ---------------------------------------- |
| `--sys-action-primary`             | Primary CTA background                   |
| `--sys-action-primary-hover`       | Primary CTA hover background             |
| `--sys-action-primary-foreground`  | Primary CTA text                         |
| `--sys-surface-accent`             | Accent surface (banners, inline calls)  |
| `--sys-border-accent`              | Accent border (focus card, inline alert) |
| `--sys-bg`                         | Page background                          |
| `--sys-surface`                    | Card / panel surface                     |
| `--sys-surface-strong`             | Elevated card surface                    |
| `--sys-text`                       | Body text                                |
| `--sys-text-muted`                 | Muted / secondary text                   |
| `--sys-border`                     | Default 1 px divider                     |
| `--sys-focus-ring`                 | `:focus-visible` outline color           |

Theme-aware pairs (`--sys-bg`, `--sys-surface`, `--sys-surface-strong`,
`--sys-text`, `--sys-text-muted`, `--sys-border`) are bound via
`light-dark(lightVal, darkVal)`. The
`@supports not (color: light-dark(red, blue))` fallback re-binds them via
`@media (prefers-color-scheme: dark)` for browsers that have not yet
adopted `light-dark()` (Baseline 2024).

## Focus ring

A single `:focus-visible` rule in `globals.css` consumes
`--sys-focus-ring`:

```css
*:focus-visible {
  outline: 3px solid var(--sys-focus-ring);
  outline-offset: 2px;
  border-radius: var(--radius-sm);
}
```

Per-component focus styles are forbidden — the audience attribute is the
only switch.

## WCAG 2.2 AA contrast — verified pairs

The OKLCH reference values are perceptually-uniform approximations of
hex anchors that were verified against WebAIM's contrast checker. The
hex anchors remain available as `--hp-retailer-accent`, `--hp-builder-accent`,
`--hp-deploy-accent` in `apps/ui/styles/tokens/*.css` so the verification
ledger below stays grounded in measurable pairs.

| Pair (background → foreground)                              | Contrast | WCAG 2.2 AA            |
| ----------------------------------------------------------- | -------- | ---------------------- |
| `#ffffff` → `#b45309` (retailer accent on white)            | 5.71 : 1 | ✅ AA body, AA large    |
| `#ffffff` → `#1d4ed8` (builder accent on white)             | 8.59 : 1 | ✅ AA body, AAA large   |
| `#ffffff` → `#334155` (deploy accent on white)              | 10.78 : 1| ✅ AAA both             |
| `#ffffff` → `#1a1a1a` (default body text on white)          | 17.4 : 1 | ✅ AAA both             |
| `#fafaf9` → `#1a1a1a` (sys-text on sys-bg, light)           | 16.6 : 1 | ✅ AAA both             |
| `#0a0a0a` → `#fafafa` (sys-text on sys-bg, dark)            | 19.3 : 1 | ✅ AAA both             |
| Warm-500 background → `#ffffff` text (button foreground)    | 5.71 : 1 | ✅ AA body              |
| Cool-500 background → `#ffffff` text (button foreground)    | 8.59 : 1 | ✅ AAA body             |

The `ui-axe-core` CI gate (`.github/workflows/ui-axe-core.yml`) re-runs
axe-core against the rendered audience pages on every PR; any drift below
4.5 : 1 (body) or 3 : 1 (large) blocks merge.

## Consumer examples

### CTA button (system tokens)

```tsx
<button className="rounded-md px-4 py-2"
        style={{ background: 'var(--sys-action-primary)',
                 color: 'var(--sys-action-primary-foreground)' }}>
  Pick your lane
</button>
```

### Tailwind utility from a reference token

```tsx
<aside className="bg-warm-50 text-warm-900 p-4 rounded-md">…</aside>
```

### Audience-aware accent surface

```tsx
<section data-audience="retailer" className="audience-retailer">
  {/* inside, var(--sys-action-primary) === var(--color-warm-500) */}
</section>
```

## Forbidden patterns

- Raw hex literals inside `app/(retailer)/**`, `app/(builder)/**`,
  `app/(deploy)/**`, or `components/shared/**` — enforced by the ESLint
  rule introduced in [#1011](https://github.com/Azure-Samples/holiday-peak-hub/issues/1011).
- `tailwind.config.{ts,js}` — both were deleted in [#1056](https://github.com/Azure-Samples/holiday-peak-hub/issues/1056).
- `.dark` class override in `globals.css` — replaced by `light-dark()`
  + `@media (prefers-color-scheme: dark)` fallback at the system layer.
- New `dark:` Tailwind utilities introduced after [#1056](https://github.com/Azure-Samples/holiday-peak-hub/issues/1056).

## Migration trail (what F4 / #1058 will prune)

- `--hp-*` brand-scoped aliases that simply forward to system tokens.
- The `dark:` Tailwind variants scattered across `apps/ui/components/`,
  `apps/ui/app/categories/page.tsx`, etc. (replaced by token-based
  surfaces).
- `globals.css` body decorations (radial gradients) — those move into
  per-route layouts so the global file approaches the ≤ 60 line target.

## Related

- [ADR-034 — Information architecture, audience segmentation](../architecture/adrs/adr-034-audience-segmented-ia.md)
- [ADR-035 — UI design system contract](../architecture/adrs/adr-035-ui-design-system.md)
- [Frontend governance](../governance/frontend-governance.md)
- [Five-second test merge gate](../governance/five-second-test.md)
