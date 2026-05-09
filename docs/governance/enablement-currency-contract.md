# Enablement Currency Contract

> **Audience.** Internal sales / GTM / enablement authors.
>
> **Owner.** `CompetitiveIntelAnalyst` agent (per [team-mapping](../../.github/agents/data/team-mapping.md)).
>
> **Source of truth.** This document, plus the registry loader at
> [`apps/ui/lib/enablement/registry.ts`](../../apps/ui/lib/enablement/registry.ts).

This contract pins the rules that govern every asset rendered under
`/builders/enablement/*` (Issue #1051 / Issue #1052 / Epic #1053).

## Why a currency contract

Sales enablement assets that aren't refreshed become **graveyards of
misinformation**. A 2-year-old battle card claims a competitor doesn't
support an integration that has shipped. A demo script says "click X" when
the UI has moved. A customer quote attributed without permission becomes a
legal incident.

The contract enforces three rules:

1. **Every asset has an owner and a last_reviewed date.**
2. **Expired assets are hidden, not stale-rendered.** Hiding is honest;
   stale rendering is a lie.
3. **Customer quotes render only with written permission.** Even within
   the gated GTM tenant.

## Front-matter schema

Every file under `docs/enablement/**/*.md` MUST carry this YAML
front-matter at the very top of the file:

```yaml
---
title: "Holiday Peak Hub vs. Algolia — battle card"
kind: battle-card               # required, enum below
owner: ricardo-cataldi          # required, GitHub handle (no @)
last_reviewed: 2025-11-04       # required, ISO date YYYY-MM-DD
attribution_status: approved    # required IFF kind == customer-quote
---
```

### `kind` enum

| `kind` | Expiry window | Notes |
|--------|---------------|-------|
| `battle-card` | **90 days** | Refresh quarterly. |
| `demo-script` | **180 days** | Refresh half-yearly. |
| `win-loss` | **never expires** | Append-only history; immutable record. |
| `customer-quote` | **never expires** | Hidden unless `attribution_status == approved`. |

### `attribution_status` enum (for `customer-quote` only)

| Status | Renders? | Meaning |
|--------|----------|---------|
| `approved` | ✅ | Written permission on file. |
| `pending` | ❌ | Awaiting permission. |
| `unknown` | ❌ | No permission process started. |

Anything other than `approved` HIDES the quote.

## What the registry loader does

[`loadEnablementIndex()`](../../apps/ui/lib/enablement/registry.ts):

1. Reads every `*.md` file under `docs/enablement/**`.
2. Parses front-matter. Files missing required fields are skipped.
3. Computes `daysToExpiry`:
   - `battle-card` / `demo-script` → `expiry_window - days_since_last_reviewed`
   - `win-loss` / `customer-quote` → `Infinity`
4. Hides:
   - any expired asset (`daysToExpiry < 0`)
   - any `customer-quote` whose `attribution_status` is not `approved`
5. Reports the **count** of hidden assets so the GTM lead can refresh.
6. Sorts: soonest-to-expire first, immutable assets at the bottom.

The expired count is rendered in the index banner. The expired assets
themselves are NEVER rendered.

## Authoring workflow

1. Add a new asset under `docs/enablement/<kind>/<slug>.md` with the full
   front-matter.
2. Open a PR. Branch naming follows ADR-018 (`feature/<id>-...` or
   `chore/...` if no issue number).
3. CI runs the front-matter validator on PRs that touch
   `docs/enablement/**`.
4. After merge the asset shows up at `/builders/enablement` (gated to the
   Microsoft Retail GTM Entra group).
5. Set yourself a calendar reminder for the next refresh:
   - battle cards: every 90 days
   - demo scripts: every 180 days

## Refreshing an asset

Refresh = update `last_reviewed` to today's date, AND substantively review
the content. Bumping the date without reading the asset is a violation of
this contract — and it's caught at PR review time.

When refreshing a `battle-card`:
- Verify every claim against the competitor's current public docs.
- Verify dates and version numbers.
- Re-run the comparator matrix at `/retailers/comparators` against the
  refreshed competitor entry.

When refreshing a `demo-script`:
- Run the demo end-to-end against the latest deployed version.
- Update screenshots and click sequences.

`win-loss` records are **immutable** — never edit, only append.

`customer-quote` records require an updated permission email if the
customer's role or context has changed.

## Anti-patterns

- ❌ Don't render expired assets with a "stale" badge. Hide them.
- ❌ Don't bump `last_reviewed` without actually reviewing.
- ❌ Don't render `customer-quote` with `attribution_status: pending`.
- ❌ Don't store enablement assets outside `docs/enablement/`.
- ❌ Don't add a `kind` outside the enum without first amending this
  contract via PR.
- ❌ Don't put real customer data in `win-loss` without pseudonymising —
  even within the GTM tenant — unless written permission is on file.

## Cross-references

- `apps/ui/app/(builder)/builders/enablement/layout.tsx` — server-side gate (path contains parentheses; see file in repo)
- [`apps/ui/lib/enablement/gate.ts`](../../apps/ui/lib/enablement/gate.ts) — gate evaluator + audit log
- [`apps/ui/lib/enablement/registry.ts`](../../apps/ui/lib/enablement/registry.ts) — registry loader + currency rules
- Epic #1053 (this contract is acceptance for Issue #1052)

## Changelog

| Date | Change | Owner |
|------|--------|-------|
| 2025-11-04 | Initial baseline (Issue #1052 / Epic #1053) | tech-manager |
