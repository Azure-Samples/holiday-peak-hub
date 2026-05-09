# Sales Enablement Asset Tree

> **Audience.** GTM authors. **Owner.** `CompetitiveIntelAnalyst` per [team-mapping](../../.github/agents/data/team-mapping.md).

This tree is the curated source for assets rendered under `/builders/enablement/*`. The currency contract is documented in:

- [enablement-asset-contract.md](../governance/enablement-asset-contract.md) — front-matter schema (machine-readable contract).
- [enablement-currency-contract.md](../governance/enablement-currency-contract.md) — operational rules (expiry windows, hide-on-expiry, runtime loader behavior).

## How to add a new asset

1. Create a Markdown file under the appropriate subdirectory:
   - `battle-cards/` — competitive battle cards (90-day expiry).
   - `demos/` — demo scripts and walkthroughs (180-day expiry).
   - `win-loss/` — append-only win/loss entries (immutable; never expires).
   - `quotes/` — customer quotes (rendered iff `attribution_status: approved`).
2. Add the front-matter block (see schema in [enablement-asset-contract.md](../governance/enablement-asset-contract.md)).
3. Open a PR. The lint workflow validates the contract; `python scripts/ops/build_enablement_index.py --check` is the gate.

## How an asset gets refreshed

When you review or refresh an asset, set `last_reviewed` to today's ISO date and bump the body. **Do not delete or modify expired assets** — the loader hides them automatically; the GTM lead sees the count in the index banner and prompts a curation pass.

## How win/loss is appended

Win/loss entries are immutable. If a fact changes, write a **new** entry that references the original by slug; do not edit the original. The quarterly digest preserves both.

## What renders at `/builders/enablement`

The Next.js page at `apps/ui/app/(builder)/builders/enablement/page.tsx` reads `apps/ui/public/enablement-index.json` (built by `scripts/ops/build_enablement_index.py`) and surfaces:

- One row per **live** asset (sorted soonest-to-expire).
- An **expired count** banner (e.g., "3 asset(s) expired and hidden").
- A CTA pointing back to the currency contract.

Hidden assets never reach the surface. That is the whole point of the contract.

## Build commands

```sh
# Validate the contract (CI gate)
python scripts/ops/build_enablement_index.py --check

# Write the index artifact consumed by the UI
python scripts/ops/build_enablement_index.py

# Render the quarterly win/loss digest
python scripts/ops/build_winloss_digest.py --quarter 2025-Q4
```
