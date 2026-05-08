---
applyTo: '**'
description: Canonical statement of what this repository IS. Loaded into every agent prompt. Single source of truth for positioning — all other docs must align with this file.
---

# Repository Purpose — Canonical Statement

> This file is the single source of truth for what Holiday Peak Hub IS. Every agent operating in this repository must internalize this statement before planning, implementing, or reviewing any change. Other docs (READMEs, ADRs, architecture references) MUST align with this file. If they drift, this file wins and the drift is a bug.

## What this repository is

Holiday Peak Hub is **a framework AND a product**, distributed as a public Microsoft sample under `Azure-Samples/`. It is **not** a demo. It is **not** a framework with toy apps. It is **not** a product without a framework. It is both, deliberately, and the engineering bar reflects that.

| Layer | What it is | Status |
|---|---|---|
| `lib/holiday_peak_lib/` | **Framework** — an opinionated agentic-microservices runtime for retail. Stable seams: `BaseRetailAgent`, `AgentBuilder`, `ModelTarget` / `ModelInvoker`, `FastAPIMCPServer`, three-tier memory (Hot/Warm/Cold), enrichment guardrails, routing strategy, evaluation runners, structured telemetry, connector contracts. Versioned. Reusable. Forks adopt it directly. | **Framework** |
| `apps/` | **Product** — a retail platform built on the framework: 1 transactional microservice (`crud-service`), 26 agent services across CRM/eCommerce/Inventory/Logistics/Product Management/Search/Truth Layer, and 1 Next.js frontend (`ui`). Real domain logic, real connectors, real SLOs, real canary routing, real continuous evaluation. | **Product** |
| `Azure-Samples/holiday-peak-hub` | Distribution channel and licensing path. **Not a downgrade to "sample."** | Distribution |

## Engineering bar

The latency obsession, the AGC weighted-canary discipline, the per-agent eval baselines, the three-tier memory, the connector breadth, the namespace isolation, the self-healing kernel — those exist because **the product needs them in production**. Not because they make a good demo.

When evaluating a change, the question is not "does this look good in a sample?" The question is:
- Does it strengthen the framework's contracts (`lib/`)?
- Does it strengthen the product's SLOs, UX, or operability (`apps/`)?
- Or both?

If the answer to all three is no, the change does not belong here.

## Who clones this repository, and why

Architects, platform engineers, and AI/ML engineers clone Holiday Peak Hub to do one or more of:

1. **Adopt the framework** — fork `lib/`, build their own retail platform on it
2. **Run the product** — deploy `apps/` end-to-end, treat it as a reference retail platform
3. **Both** — adopt the framework, learn from the product, evolve both inside their own org

All three are first-class. None is a downgrade.

## What we do NOT claim

- "A framework for agentic retail solutions" — too narrow. Drops the product half.
- "Demonstration services" / "demo apps" — false. `apps/` is product-grade with production discipline.
- "Reference implementation" alone — true but incomplete. It is also a framework architects extract and adopt.
- "Agentic retail platform" alone — true but incomplete. The framework underneath is the durable contract.

## What we DO claim

- **`lib/` is a framework.** Versioned, contracted, designed for adoption.
- **`apps/` is a product.** Production-grade retail platform, 26 agents, real connectors, real SLOs.
- **Both ship together.** They evolve together. They are tested together (1796+ tests). They are deployed together (azd + Flux + AGC).
- **Distribution is via Azure-Samples.** That is a channel, not a quality tier.

## Documented gaps (do not over-claim)

The product runs in a single subscription at sample scale. We do **not** claim:
- Production-scale economics at 10M MAU
- Multi-tenant data residency / SOC 2 / PCI evidence under real-retailer PII

When an architect-customer asks those questions, point them to Microsoft FastTrack / CSA conversations. Do not pretend the repo answers production-scale on its own.

## Boundary rules (operational)

- Changes to `lib/` are framework changes — require a stable contract, contract tests, and (where applicable) an ADR. The framework's seams are load-bearing.
- Changes to `apps/` are product changes — require domain reasoning, eval impact analysis, SLO awareness, and operational runbook updates when behavior changes.
- Cross-cutting changes (`lib/` + `apps/`) require both lenses and explicit coordination.

## Required usage by agents

Every agent working in this repository must:

1. Treat `lib/` as a framework with stable contracts. Never propose breaking changes to `lib/` casually. Never treat `lib/` edits as "small."
2. Treat `apps/` as a product with production SLOs. Never propose `apps/` changes that ignore latency budgets, eval baselines, canary routing, or operational impact.
3. Reject framing that calls this repo "just a sample" or "just a framework." Both halves matter.
4. When summarizing the repo's purpose to the user (in plans, briefs, ADRs, PR descriptions), state the framework + product positioning explicitly.

## Cross-references

- Root: [README.MD](../../README.MD)
- Framework: [lib/README.md](../../lib/README.md)
- Product: [apps/README.md](../../apps/README.md)
- Architecture index: [docs/README.md](../../docs/README.md)
- Reference architecture: [docs/agentic-microservices-reference.md](../../docs/agentic-microservices-reference.md)
- ADR index: [docs/architecture/ADRs.md](../../docs/architecture/ADRs.md)

If any of those drift from this file, this file is correct and the drift is a bug to fix.
