# Business Scenario 02: Product Discovery & Enrichment

## Executive Statement

Conversion acceleration engine that combines semantic discovery, AI enrichment, and resilient fallback to keep revenue flowing during peak traffic.

## Capability Mapping

| Capability | Business Leverage |
| --- | --- |
| Catalog search intelligence | High-relevance results and lower bounce |
| Product detail enrichment | Better content quality and conversion lift |
| Cart intelligence | Incremental AOV through contextual upsell |
| CRUD fallback path | Availability protection when search intelligence degrades |

## Outcome Targets

| North-Star KPI | Target |
| --- | --- |
| Search response latency | < 1.2s p95 |
| Search-to-product click-through | > 35% |
| Enriched catalog coverage | > 98% |
| Fallback continuity during degradation | > 99% |

## Executive Flow

```mermaid
flowchart LR
   A[Customer Query Intent] --> B[Catalog Search Agent]
   B --> C[Semantic Ranking + Inventory Signals]
   C --> D[Product Detail Enrichment]
   D --> E[Personalized Recommendation Layer]
   E --> F[Conversion Decision]

   B --> G{Search Service Degraded?}
   G -->|Yes| H[CRUD Fallback Query]
   H --> F

   classDef a fill:#0B84F3,color:#fff,stroke:#085ea8
   classDef b fill:#00A88F,color:#fff,stroke:#0b6e5f
   classDef c fill:#F39C12,color:#fff,stroke:#af6f0c
   classDef d fill:#8E44AD,color:#fff,stroke:#5b2a70
   class A,B a
   class C,D,E,F b
   class G c
   class H d
```

## Issue #32 Implementation Status (2026-03-12)

Implemented and operational in platform deployment/runtime paths:

- **Provisioning**: Shared infrastructure provisions Azure AI Search, and `azd` `postprovision` ensures the `catalog-products` index after the service is reachable.
- **Environment propagation**: `AI_SEARCH_ENDPOINT`, `AI_SEARCH_INDEX`, and `AI_SEARCH_AUTH_MODE` flow from Bicep outputs through `azd`/workflow outputs into Helm-rendered service environment variables.
- **Runtime query path**: `ecommerce-catalog-search` queries Azure AI Search when configured.
- **Runtime fallback**: If AI Search is unconfigured/unavailable or returns no usable SKU set, catalog search falls back to the existing adapter-based retrieval path to preserve response continuity.
- **Index maintenance**: Product event handlers attempt AI Search document upsert/delete when AI Search configuration is present.

### Optional Hardening (Non-blocking)

- Add vector embeddings + weighted hybrid query tuning (current path is keyword/SKU retrieval).
- Add index relevance/load evaluation suites and SLO-driven alert thresholds.
- Add stricter index/schema drift validation in CI pre-deploy checks.
