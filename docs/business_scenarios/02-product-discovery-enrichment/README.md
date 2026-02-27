# Business Scenario 02: Product Discovery & Enrichment

## Overview

**Product Discovery & Enrichment** covers how customers find products (search, browse, recommendations) and how product data is enriched with AI-generated content. This is a **hybrid pattern** combining synchronous REST calls (with circuit-breaker fallback) for real-time search, and asynchronous event-driven flows for catalog indexing and enrichment pipelines.

## Business Importance for Retail

| Metric | Impact |
|--------|--------|
| **Conversion Rate** | Relevant search results increase conversion by 2–5×. Irrelevant results = bounce |
| **Average Order Value** | Smart recommendations add 10–30% to AOV through cross-sell/upsell |
| **Catalog Quality** | Rich, consistent product descriptions reduce return rates by up to 20% |
| **Time to Market** | Automated enrichment reduces manual cataloging from days to minutes |
| **SEO Performance** | AI-enriched descriptions improve organic search rankings |

During holiday peaks, product discovery becomes critical — customers searching for gifts need fast, accurate results. The difference between a 200ms and 2-second search response can mean millions in lost revenue.

## Traditional Challenges

1. **Keyword-Only Search**: Traditional SQL LIKE queries miss semantic intent ("warm winter jacket" vs. "insulated parka")
2. **Stale Catalog Data**: Product changes propagate slowly to search indexes — customers see out-of-stock items
3. **Manual Enrichment**: Product managers write descriptions by hand — bottleneck at scale (10K+ SKUs)
4. **Generic Recommendations**: Rule-based "customers also bought" lacks context awareness
5. **Search Fragility**: Single search service down = entire catalog inaccessible
6. **Inconsistent Descriptions**: Different suppliers provide varying quality data, no standardization

## How Holiday Peak Hub Addresses It

### Synchronous Search with Circuit Breaker

The catalog search agent (`ecommerce-catalog-search`) provides semantic search powered by Azure AI Search:

```
Customer → CRUD Service → Catalog Search Agent (500ms timeout)
                              ↓ (circuit open)
                         CRUD Fallback: Basic SQL query
```

- **SLM-first routing**: Simple keyword queries handled by SLM; complex semantic queries escalated to LLM
- **Redis cache**: Search results cached for 15 minutes (TTL), reducing redundant AI Search calls
- **Circuit breaker**: If the agent fails 3× in 30s, CRUD falls back to basic product listing

### Async Catalog Indexing

When products are created or updated, an event-driven pipeline keeps the search index current:

```
Staff creates product → ProductCreated event → catalog-search updates AI Search index
                                             → product-enrichment generates descriptions
                                             → normalization classifies category
```

### AI-Powered Enrichment

The enrichment agent (`ecommerce-product-detail-enrichment`) uses AI to:
- Generate ACP-compliant product descriptions
- Extract key attributes (material, size, color) from raw supplier data
- Create SEO-optimized titles and meta descriptions
- Enrich with cross-reference data from similar products

## Process Flow

### Product Search (Synchronous)

1. **Customer** enters search query on `/category/[slug]` or search bar
2. **CRUD Service** receives `GET /api/products?search={query}`
3. **CRUD Service** calls `ecommerce-catalog-search` agent (500ms timeout):
   - Agent receives query → checks Redis cache (15min TTL)
   - Cache miss → queries Azure AI Search with vector + hybrid search
   - AI Search returns ranked results → agent formats response
   - Agent caches results in Redis → returns to CRUD
4. **Circuit Breaker**: If agent unavailable, CRUD falls back to basic SQL product query
5. **Results** returned to customer with AI-ranked relevance

### Cart Recommendations (Synchronous)

1. **Customer** views cart on `/cart` or `/checkout`
2. **CRUD Service** calls `ecommerce-cart-intelligence` agent (500ms timeout):
   - Agent analyzes cart contents (product categories, price range, quantity)
   - SLM generates cross-sell/upsell recommendations
   - Complex scenarios (gift bundles, seasonal combos) escalated to LLM
3. **Fallback**: If agent unavailable, CRUD returns trending products

### Catalog Index Update (Asynchronous)

1. **Staff** creates/updates product via admin panel → `POST /api/products`
2. **CRUD Service** publishes `ProductCreated` / `ProductUpdated` to `product-events` topic
3. **Catalog Search Agent** receives event:
   - Extracts searchable fields (title, description, category, attributes)
   - Updates Azure AI Search index with new/modified document
   - Invalidates related Redis cache entries
4. **Product Enrichment Agent** receives event:
   - Fetches base product data from CRUD
   - Generates AI-enriched description (SLM-first, LLM for complex products)
   - Stores enriched data in Cosmos DB (warm memory)
   - Publishes `ProductEnriched` event

### Product Detail Enrichment (Synchronous + Async)

1. **Customer** opens `/product/[id]`
2. **CRUD Service** fetches base product → calls `ecommerce-product-detail-enrichment` (500ms timeout)
3. **Enrichment Agent** checks warm memory (Cosmos DB) for pre-enriched data:
   - Found → returns enriched details immediately
   - Not found → generates on-the-fly with SLM → caches for future requests
4. Response includes: AI description, extracted attributes, compatibility info, care instructions

## Agents Involved

| Agent | Role | Pattern | Fallback |
|-------|------|---------|----------|
| `ecommerce-catalog-search` | Semantic product search | Sync REST (500ms) | Basic SQL query |
| `ecommerce-product-detail-enrichment` | AI product descriptions | Sync REST (500ms) | Raw supplier data |
| `ecommerce-cart-intelligence` | Cart-based recommendations | Sync REST (500ms) | Trending products |
| `product-management-normalization-classification` | Category auto-classification | Async Event | Manual classification |
| `product-management-acp-transformation` | ACP compliance transformation | Async Event | Raw data stored |

## Event Hub Topology

```
product-events (ProductCreated/Updated)  ──→  ecommerce-catalog-search (index update)
                                         ──→  ecommerce-product-detail-enrichment (pre-enrich)
                                         ──→  product-management-normalization-classification
                                         ──→  product-management-acp-transformation
```

## Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| Search response time (p95) | < 300ms | End-to-end including AI Search |
| Search relevance (NDCG@10) | > 0.75 | Normalized discounted cumulative gain |
| Cache hit rate | > 60% | Redis cache hits / total search requests |
| Enrichment throughput | 100+ products/min | Async enrichment pipeline |
| Circuit breaker recovery | < 30 seconds | Time from circuit open to half-open probe |
| Recommendation click-through | > 8% | Clicks on recommended products / impressions |

## BPMN Diagram

See [product-discovery-enrichment.drawio](product-discovery-enrichment.drawio) for the complete BPMN 2.0 process diagram showing:
- **5 pools**: Customer, CRUD Service, Catalog Search Agent, Enrichment Agent, Azure AI Search
- **Synchronous paths**: Direct REST calls with circuit-breaker fallback
- **Asynchronous paths**: Event-driven catalog indexing and enrichment pipeline
- **Decision gateways**: Cache hit/miss, circuit breaker state, SLM/LLM routing
