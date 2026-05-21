---
title: "Holiday Peak Hub vs. point-solution AI search vendors — battle card"
kind: battle-card
owner: ricardo-cataldi
last_reviewed: 2026-05-09
---

## When the buyer says "we already have Algolia / Vertex / Coveo"

**One-liner.** Holiday Peak Hub is not a search vendor. It is an **agentic-microservices runtime** that ships search as one of 27 agents, with a shared three-tier memory, MCP-based agent-to-agent calls, AGC-weighted canary routing, and continuous evaluation. Point solutions move the search problem; we move the **product-experience** problem.

## Talk track

1. **Anchor on the boundary.** Point solutions optimize ranking. We optimize the **decision the shopper is making**: the catalog agent enriches the SKU, the cart-intelligence agent reasons about substitutes, the checkout-support agent rescues abandoned carts. Each agent reads the same warm/hot memory tier; nothing is reinvented per service.
2. **Latency discipline.** SLM-first routing keeps p95 under 300ms for the common path; LLM upgrade only when complexity warrants. Most "AI search" demos hide a 2s LLM call behind every keystroke.
3. **Eval baseline.** Continuous evaluation runs on every PR — `lib/src/holiday_peak_lib/eval/` ships with golden sets per agent. Point solutions cannot tell you their drift rate; we publish it.
4. **Connector breadth.** Real connectors exist: Salesforce, Shopify, SAP, custom legacy. The deploy portal at `/deploy` provisions all of it under the customer's tenant.

## Common objections

| Objection | Response |
|---|---|
| "Algolia is faster." | Yes — for the indexing step. We are faster end-to-end because we skip the orchestration layer the customer would otherwise have to build. |
| "Vertex AI Search has Google's models." | Foundry has the same catalog plus we pick the **right** model per request via SLM-first routing. The model is the cheapest part of the system. |
| "Coveo has unified search." | Coveo unifies indexes. We unify **agents**. That is a different category. |

## Differentiator slugs (use these in the deck)

- "27 agents, one runtime, one eval baseline."
- "SLM-first by default — LLM only when the request earns it."
- "AGC canary routing 5/25/50/100, every release, no exception."
- "Three-tier memory: hot Redis, warm Cosmos, cold Blob — agents share state without re-indexing."

## Cited evidence

- [`lib/README.md`](https://github.com/Azure-Samples/holiday-peak-hub/blob/main/lib/README.md) — framework contract.
- [`docs/architecture/ADRs.md`](https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/architecture/ADRs.md) — ADR-029 (canary), ADR-030 (MCP A2A), ADR-032 (three-tier memory).
- [`docs/methodology/retailer-roi.md`](https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/methodology/retailer-roi.md) — 75% buyer-time savings, 22% dispute reduction, ±40% CI.
