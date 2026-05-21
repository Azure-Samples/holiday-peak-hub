# Persona — soft audience detection (ADR-034 §3)

This folder defines the **soft persona detection** contract used across the
audience-segmented IA.

## The contract

| | |
|---|---|
| Cookie name | `persona` |
| Allowed values | `retailer` \| `builder` |
| TTL | 90 days (`Max-Age=7776000`) |
| Flags | `SameSite=Lax`, `Secure` (when on HTTPS) |
| Query override | `?as=retailer\|builder` |
| Set on | First CTA interaction on `/` (HomeSplitHero), or LaneSwitch click. |
| Used by | LaneSwitch (copy ordering), HomeSplitHero (default tab), recommended-next-step lists (ordering only). |

## What persona is allowed to do

- **Reorder** which CTA renders first on `/`.
- **Reorder** copy in `<LaneSwitch>` (e.g., "I run a retail business" vs. "I'm building on this platform" — which one comes first).
- **Reorder** recommended-next-step lists.

## What persona is **NOT** allowed to do

- ❌ **Gate** any primary content. A retailer landing on `/builders/architecture` directly via SEO must see the same content as a builder.
- ❌ **Hide** any primary content.
- ❌ **Change** route handler responses based on persona.
- ❌ **Trigger** persona-specific telemetry events that fan out into a/b drift.

## Linting

`apps/ui/.eslintrc.json` adds an override on `app/api/**/route.{ts,tsx}` that
bans `BinaryExpression[left.name='persona']`. Reordering logic that compares
against `persona` is allowed in client components under `components/**` — it's
the gating logic in route handlers and server components that is the bug.

## Testing

- Unit: `LaneSwitch` snapshot test covers all four `from` → `to` permutations.
- Integration: cookie + query-param resolution contract under `tests/unit/`.

## ADR alignment

- **ADR-034** §3 — soft persona detection: this is the implementation.
- **ADR-035** — UI design system contract: LaneSwitch lives in
  `apps/ui/components/shared/` per the shared-bundle rule.
