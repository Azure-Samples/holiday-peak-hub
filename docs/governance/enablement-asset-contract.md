# Enablement Asset Contract — Front-Matter Schema

> **Audience.** Internal sales / GTM / enablement authors **and** the build pipeline.
>
> **Owner.** `CompetitiveIntelAnalyst` agent (per [team-mapping](../../.github/agents/data/team-mapping.md)).
>
> **Companion document.** [enablement-currency-contract.md](enablement-currency-contract.md) — operational rules (expiry windows, hide-on-expiry, runtime loader behavior).
>
> **Build artifact.** `apps/ui/public/enablement-index.json` (generated; not tracked) — emitted by [`scripts/ops/build_enablement_index.py`](../../scripts/ops/build_enablement_index.py).

This contract pins the **machine-readable schema** for every Markdown file rendered under `/builders/enablement/*` (Issue #1051 / Issue #1052 / Epic #1053). It is the source of truth consumed by the Python build script and the TypeScript runtime loader.

## Why a separate schema doc

The currency contract describes **why** we hide expired assets and **how** they behave at render time. The asset contract — this document — describes **what the file must look like on disk** so that:

- Authors know exactly which fields are required.
- The CI build fails on missing fields *before* a stale-or-malformed asset reaches `main`.
- The TypeScript loader and the Python build script share one definition.

## Front-matter schema (canonical)

Every file under `docs/enablement/**/*.md` (or any configured curated source path) MUST begin with this YAML front-matter block:

```yaml
---
title: "Holiday Peak Hub vs. Algolia — battle card"
kind: battle-card               # required, enum: battle-card | demo-script | win-loss | customer-quote
owner: ricardo-cataldi          # required, GitHub handle without leading "@"
last_reviewed: 2025-11-04       # required, ISO date (YYYY-MM-DD)
attribution_status: approved    # required IFF kind == customer-quote
permission_doc: https://...     # required IFF kind == customer-quote AND attribution_status == approved
---
```

### Required fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `title` | string | always | Human-readable, used as the link label. |
| `kind` | enum | always | `battle-card`, `demo-script`, `win-loss`, `customer-quote`. |
| `owner` | string | always | GitHub handle, lowercase, no `@`. Owner is on the hook for refresh cadence. |
| `last_reviewed` | ISO date | always | `YYYY-MM-DD`. Refresh sets this to the current date. |
| `attribution_status` | enum | iff `kind == customer-quote` | `approved`, `pending`, or `unknown`. |
| `permission_doc` | URL | iff `kind == customer-quote` AND `attribution_status == approved` | Link to the permission record (e.g., signed agreement, ticket). |

### Disallowed fields

The schema is **closed**. Any front-matter key not in the table above is rejected by the build script. This prevents authors from inventing parallel schemas and silently degrading the contract.

## Validation rules (build-time)

The Python build script `scripts/ops/build_enablement_index.py` enforces:

1. **Front-matter present** — file must start with `---\n...\n---`. Missing front-matter is an error.
2. **All required fields present and non-empty** — missing field is an error.
3. **`last_reviewed` is parseable as ISO date** — bad date is an error.
4. **`kind` ∈ enum** — invalid kind is an error.
5. **Conditional fields enforced**:
   - If `kind == customer-quote`, `attribution_status` is required.
   - If `kind == customer-quote` and `attribution_status == approved`, `permission_doc` is required.
6. **Owner is a plausible GitHub handle** — matches `[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}[A-Za-z0-9])?` (GitHub username rules).
7. **No unknown fields** — closed schema.

The script exits with status `1` and a structured error report on any violation. This is wired into CI in [`.github/workflows/lint.yml`](../../.github/workflows/lint.yml) (front-matter validation) and [`.github/workflows/test.yml`](../../.github/workflows/test.yml) (unit tests).

## Build artifact: `enablement-index.json`

The build script emits `apps/ui/public/enablement-index.json` with this shape:

```jsonc
{
  "generatedAt": "2025-11-04T00:00:00+00:00",
  "schemaVersion": 1,
  "expiredCount": 0,
  "hiddenQuoteCount": 0,
  "assets": [
    {
      "slug": "vs-algolia-battle-card",
      "title": "Holiday Peak Hub vs. Algolia — battle card",
      "kind": "battle-card",
      "owner": "ricardo-cataldi",
      "lastReviewed": "2025-11-04",
      "daysToExpiry": 90,
      "href": "https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/enablement/battle-cards/vs-algolia.md"
    }
  ]
}
```

Expired assets and non-approved customer quotes are **excluded from the `assets` array** — they are counted in `expiredCount` / `hiddenQuoteCount` so the GTM lead sees the graveyard size, but they never render.

## Quarterly win/loss digest

The companion script [`scripts/ops/build_winloss_digest.py`](../../scripts/ops/build_winloss_digest.py) builds a Markdown digest of all `win-loss` entries authored in the past quarter. It is published to `/builders/enablement/win-loss/digest/<YYYY-Q>/`.

Win/loss entries are **immutable**: corrections are written as **new** entries that reference the original by slug. The digest reflects this append-only history.

## Cross-references

- Operational rules: [enablement-currency-contract.md](enablement-currency-contract.md)
- TypeScript runtime loader: [`apps/ui/lib/enablement/registry.ts`](../../apps/ui/lib/enablement/registry.ts)
- Python build script: [`scripts/ops/build_enablement_index.py`](../../scripts/ops/build_enablement_index.py)
- Quarterly digest script: [`scripts/ops/build_winloss_digest.py`](../../scripts/ops/build_winloss_digest.py)
- Sample assets: [`docs/enablement/`](../enablement/)
- Owning team mapping: [`.github/agents/data/team-mapping.md`](../../.github/agents/data/team-mapping.md)
- ADR: [ADR-034 — audience-segmented IA](../architecture/adrs/adr-034-audience-segmented-ia.md)
