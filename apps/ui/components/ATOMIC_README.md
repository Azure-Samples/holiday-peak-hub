# Component Library — Atomic Layout

Per ADR-035, the UI component library lives at `apps/ui/components/{atoms,molecules,organisms,templates}/`. There is **no** `atomic/` parent folder. There is **no** `components/Button.tsx` co-existing with `components/atoms/Button.tsx`.

## Structure

```
apps/ui/components/
├── atoms/          # Primitive UI elements (buttons, inputs, icons, badges)
├── molecules/      # Compositions of atoms (cards, form fields, alerts)
├── organisms/      # Domain-aware features (navigation, filter panels, carts)
├── templates/      # Page-level layout shells
├── admin/          # Internal-tooling-only widgets (gated under ADR-034 §5)
├── demo/           # Demo-only widgets (lazy-loaded behind (demo) route group)
├── enrichment/     # Enrichment-pipeline UI primitives (ADR-022)
├── truth/          # Product-truth UI primitives (ADR-020)
├── types/          # Shared TypeScript contracts
├── utils/          # Cross-cutting helpers
└── utils.ts        # Component utilities (cn, format helpers)
```

## Import contract

```tsx
// Atoms
import { Button } from '@/components/atoms/Button';

// Molecules
import { Card } from '@/components/molecules/Card';

// Organisms
import { Navigation } from '@/components/organisms/Navigation';

// Templates
import { MainLayout } from '@/components/templates/MainLayout';
```

The barrel `apps/ui/components/index.ts` exports a curated public surface; prefer named per-file imports for tree-shaking.

## Status

Component coverage as of the ADR-035 cleanup gate (Issue #1055):

- `atoms/`     — ~20 components
- `molecules/` — ~21 components
- `organisms/` — ~18 components
- `templates/` — ~5 templates

The three-layer design-token system, CSS architecture, and a11y/perf gates land in follow-up issues (#1056–#1060) per the ADR-035 roll-forward sequence.

## ADR references

- [ADR-033](../../../docs/architecture/adrs/adr-033-ui-modular-monolith-on-swa.md) — UI as a modular monolith on Static Web Apps
- [ADR-034](../../../docs/architecture/adrs/adr-034-audience-segmented-ia.md) — Audience-segmented information architecture
- [ADR-035](../../../docs/architecture/adrs/adr-035-ui-design-system.md) — UI design system contract (tokens, components, CSS, quality gates)
