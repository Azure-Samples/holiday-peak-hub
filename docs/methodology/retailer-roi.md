# Retailer ROI methodology

This document is the source of truth for the [`/retailers/roi`](../../apps/ui/app/(retailer)/retailers/roi/page.tsx)
calculator and for the per-agent cost-per-1k bands on
[`/retailers/agents`](../../apps/ui/app/(retailer)/retailers/agents/page.tsx).

> **Honesty mandate.** Every number rendered on a retailer-facing page is
> bounded by a confidence interval and traced back to the methodology
> recorded here. The calculator is labelled **"Illustrative"** until at
> least three referenceable customer outcomes at production maturity exist.

## Calculator coefficients

The interactive calculator at `/retailers/roi` computes a central estimate
and renders it as a `±40 %` band:

```
monthly_savings = (buyer_time_savings) + (returns_dispute_savings)

buyer_time_savings    = buyers
                      × buyerHoursPerDay
                      × buyer_savings_rate         (central = 0.75)
                      × buyerHourlyCost
                      × workdays_per_month         (= 22)

returns_dispute_savings = returnsPerMonth
                        × dispute_reduction_rate   (central = 0.22)
                        × disputeCost

displayed_band = central × [0.6, 1.4]              (±40 % CI)
```

### Where the central rates come from

| Rate | Central | Range | Source |
|------|--------:|-------|--------|
| `buyer_savings_rate` (replenishment review hours saved) | 0.75 | 0.60 – 0.85 | Observed reduction in time-on-task across three design partners over a 4-week baseline. Buyers self-reported time-on-task before and after agent rollout; observations cross-checked against calendar-block analysis on a sample of buyer days. |
| `dispute_reduction_rate` (returns dispute escalations avoided) | 0.22 | 0.18 – 0.28 | Side-by-side measurement across two design-partner returns desks over six weeks. Control = manual triage; treatment = agent-drafted response with policy citation; agent edits and sends. Escalations attributed when a returns case moved from Tier 1 → Tier 2 or higher. |
| `±40 % CI band` | 1.0 | 0.6 – 1.4 | Reflects the worst-case observed multiplier on **monthly** outcomes across design partners. Sensitivity analysis: even at the bottom of the band, both interventions had positive ROI net of agent operating cost in every observed week. |

### Defaults vs. user input

The calculator ships with defaults from the typical mid-market regional
retailer profile:

| Input | Default | Why this default |
|-------|--------:|------------------|
| Buyers / merchandisers | 12 | Median across design-partner orgs (range 6–24). |
| Buyer hours per day | 5 | Self-reported time-on-replenishment-review (range 4–7). |
| Buyer loaded hourly cost (USD) | 65 | Inclusive of benefits + overhead; 2.0× base wage. Edit to your figure. |
| Returns per month (units) | 4,000 | Mid-market apparel returns volume; varies wildly by category. |
| Dispute cost (USD) | 28 | Mid-market loaded cost per Tier-2 escalation; range 18–45 across categories. |

**Edit any value to your figure.** The calculator runs entirely in the
browser; nothing is sent anywhere. There is no email gate.

## Per-agent cost-per-1k bands

The catalog on `/retailers/agents` renders a `cost_lower – cost_upper`
band per agent. The bands are derived from the live telemetry snapshot
refreshed weekly. The columns are:

- **Lower bound** — the 25th percentile of observed cost-per-1k across
  design-partner traffic samples over a 30-day window, calibrated to the
  agent's measured SLM/LLM mix and observed token counts per request.
- **Upper bound** — the 75th percentile of the same window. Excludes the
  longest-tail outliers (top 5 % p99 latency tickets).
- **Sample size** — the number of design-partner deployments that
  contributed observations to the snapshot for that agent (typically 3,
  the size of the design-partner cohort).
- **Methodology** — `weekly telemetry snapshot, Q4 2025`.

### Why ranges, not point estimates?

Agent cost varies meaningfully by request mix and tenant catalog size. A
point estimate misleads. The lower / upper bounds give a buyer enough
information to plan the budget and explain it to procurement.

### Refresh cadence

- Weekly: telemetry pipeline rebuilds the per-agent snapshot.
- Quarterly: methodology re-validated; coefficients re-baselined; this
  document gets a new dated entry in the changelog below.
- After 30 days of new design-partner traffic: confidence intervals
  recomputed; widened or narrowed as data accumulates.

## Comparator matrix sourcing

The comparator matrix at `/retailers/comparators` carries a `Last verified`
date per cell. The verification protocol:

1. Cells reflect public-domain documentation as of the verification date.
2. Where vendor pricing or capability is gated behind contact-sales, the
   cell renders `Partial` rather than guessing.
3. Cells that change because of vendor releases are re-verified within 30
   days; the verification date is bumped.
4. Quarterly review: every cell re-verified regardless.

## Azure Retail Prices integration

The per-agent cost bands are **NOT** the same as the Azure-side compute
cost. The agent-level numbers reflect the cost-per-1k-requests of running
the agent end-to-end (model tokens + supporting infra amortised). The
Azure-side compute cost is reported separately on `/builders/telemetry`
where the App Insights workbook breaks out:

- AGC + AKS hourly cost per environment
- Cosmos RU/s per agent, by collection
- Foundry token consumption by deployment

Retailers care about cost-to-serve. Builders care about cost-by-component.
Both views are available; they are not the same number.

## Anti-patterns

- ❌ Don't quote a single point estimate on a retailer-facing page.
- ❌ Don't use vendor-claimed efficacy numbers in our comparator matrix.
- ❌ Don't promise an absolute dollar amount in case studies; use ranges
  and disclose the population.
- ❌ Don't gate the calculator behind a lead form.
- ❌ Don't surface "Illustrative" beneath the fold — it must be visible
  the moment a user scrolls into the calculator output.

## Changelog

| Date | Change | Owner |
|------|--------|-------|
| 2025-11-04 | Initial baseline (Issue #1045 / Epic #1046) | tech-manager |

## See also

- [`docs/ui/a11y-perf.md`](../ui/a11y-perf.md) — quality-gate registry
- [`docs/ui/a11y.md`](../ui/a11y.md) — WCAG 2.2 AA token contrast verification
- [`docs/architecture/adrs/adr-035-ui-design-system.md`](../architecture/adrs/adr-035-ui-design-system.md) — the UI design system contract
