# ISSUE-005: Enrichment and Search Orchestration Hardening

## Summary
Harden the product-enrichment and product-search flow so enrichment remains human-gated, validated records trigger both export and search indexing pipelines, and search UX uses baseline-first retrieval with asynchronous intelligent rerank.

## 5W2H

### What
Implement end-to-end orchestration safeguards and UX behavior across truth ingestion, HITL, enrichment, catalog search, and UI proxy/search hooks.

### Why
- Ensure only human validation can promote enriched data.
- Keep enrichment and search-indexing pipelines synchronized.
- Improve user-perceived search latency while preserving intelligent ranking quality.
- Persist search behavior context across memory tiers for personalization and replay.

### Who
- Backend services: Truth pipeline and catalog-search owners.
- Frontend services: UI search and API proxy owners.
- Platform: Event contract and deployment/monitoring owners.

### Where
- `apps/truth-ingestion`
- `apps/truth-enrichment`
- `apps/truth-hitl`
- `apps/ecommerce-catalog-search`
- `apps/ui`

### When
Roll out in controlled slices:
1. Event topology and HITL gating.
2. Search UX two-stage behavior.
3. Search memory and observability hardening.

### How
- Use event-driven choreography (`enrichment-jobs`, `hitl-jobs`, `export-jobs`, `search-enrichment-jobs`).
- Enforce human-only validation state in enrichment.
- Add UI baseline-first retrieval and background rerank.
- Store search history context using hot/warm/cold memory where available.

### How Much
- Engineering scope: medium-large cross-service change.
- Operational risk: moderate, mitigated via targeted tests and phased rollout.

## Step-by-Step Execution Plan

1. Wire missing enrichment producer in ingestion and dual approval publishers in HITL.
2. Enforce `pending_review` in enrichment proposals and remove direct auto-approval writes.
3. Share HITL adapter state between event handlers and review routes.
4. Add search request-stage contract (`baseline` and `rerank`) and response metadata.
5. Implement baseline-first UI and background intelligent rerank replacement.
6. Forward correlation and user/session/IP context through UI proxy headers.
7. Persist search history records in memory tiers with best-effort writes.
8. Add and run targeted unit tests for ingestion, HITL, enrichment, catalog-search, and UI flows.

## Acceptance Criteria

- Ingestion publishes `enrichment-jobs` for ingested entities.
- HITL approval publishes both export and search-enrichment events.
- Enrichment proposals remain `pending_review` until human decision.
- Search page renders baseline results immediately, then updates with reranked results.
- Search responses include stage/session metadata for traceability.
- Search history writes are attempted to hot, warm, and cold memory without blocking query results.
- Targeted Python and UI test suites pass.

## Current Status

Implemented in this delivery:
- Event topology wiring in ingestion and HITL.
- Human-only validation enforcement in truth enrichment.
- Two-stage search UX and proxy context propagation.
- Catalog-search stage/session response metadata and search memory persistence.
- Targeted tests for modified services and UI components.

Remaining follow-up opportunities:
- Expand schema-contract validation depth for proposed attributes.
- Add controlled external evidence lookup policy for low-confidence fields.
- Add production dashboards for end-to-end freshness and search rerank latency SLO.