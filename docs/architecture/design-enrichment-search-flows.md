# Architecture Design: End-to-End Enrichment & Intelligent Search Flows

**Status**: Accepted  
**Date**: 2026-03-19  
**Last Updated**: 2026-04-30  
**Author**: SystemArchitect  
**Scope**: Two new end-to-end flows for the Holiday Peak Hub agentic retail platform  
**Frameworks**: C4 Model, DDD Bounded Contexts, EIP (Enterprise Integration Patterns), microservices.io Saga Choreography

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Integration Pattern Assessment](#2-integration-pattern-assessment)
3. [Flow 1: End-to-End Product Enrichment](#3-flow-1-end-to-end-product-enrichment)
4. [Flow 2: Intelligent Product Search](#4-flow-2-intelligent-product-search)
5. [New/Modified Infrastructure](#5-newmodified-infrastructure)
6. [New Adapters](#6-new-adapters)
7. [New Agents vs Extending Existing](#7-new-agents-vs-extending-existing)
8. [Migration Path](#8-migration-path)
9. [ADR Recommendations](#9-adr-recommendations)
10. [Risk Register](#10-risk-register)

---

## 1. Executive Summary

Both flows are **architecturally well-fitted** to the existing platform. The codebase already has:

- **Truth Layer services** (`truth-enrichment`, `truth-hitl`, `truth-export`) with the exact Agent/Adapter/Schema pattern needed
- **Enterprise connectors** with a `ConnectorRegistry` factory pattern (ADR-003) and generic DAM/PIM integrations (`lib/integrations/dam_generic.py`, `lib/integrations/pim_writeback.py`)
- **Event Hub choreography** (ADR-006) with established subscription wiring in `main.py` via `create_eventhub_lifespan`
- **AI Search integration** in `ecommerce-catalog-search` with `search_catalog_skus_detailed()` and `upsert_catalog_document()`
- **SLM-first routing** (ADR-010) via `AgentBuilder.with_foundry_models()`
- **MCP tool exposition** (ADR-004) via `FastAPIMCPServer`

**Key finding**: Neither flow requires greenfield service creation. Both are achievable by **extending existing services** and adding targeted new components, consistent with the principle *"simplicity first — pick the simplest pattern that satisfies the quality attributes"*.

---

## 2. Integration Pattern Assessment

### 2.1 How Flows Connect to Existing Services

```
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
flowchart TB
    subgraph Existing["Existing Services (Unchanged)"]
        TI["truth-ingestion"]
        TH["truth-hitl"]
        TE["truth-export"]
        NormClass["product-management-\nnormalization-classification"]
    end

    subgraph Extended["Extended Services"]
        TEnrich["truth-enrichment\n(+ DAM image analysis\n+ gap detection v2)"]
        CatSearch["ecommerce-catalog-search\n(+ agentic search agent\n+ dual-path routing)"]
    end

    subgraph New["New Components"]
        SEA["search-enrichment-agent\n(use_cases, complements,\nsubstitutes)"]
        Indexer["AI Search Indexer\n(Cosmos → index pipeline)"]
    end

    subgraph Infra["Infrastructure"]
        EH["Event Hubs"]
        Cosmos["Cosmos DB"]
        AISearch["Azure AI Search"]
        Foundry["Azure AI Foundry"]
    end

    TI -->|ingestion-notifications| EH
    EH -->|enrichment-jobs| TEnrich
    TEnrich -->|hitl-jobs| EH
    EH -->|hitl-jobs| TH
    TH -->|export-jobs| EH
    EH -->|export-jobs| TE
    
    TH -->|search-enrichment-jobs| EH
    EH -->|search-enrichment-jobs| SEA
    SEA --> Cosmos
    Cosmos --> Indexer
    Indexer --> AISearch
    AISearch --> CatSearch
    
    TEnrich --> Foundry
    SEA --> Foundry
    CatSearch --> Foundry
```

### 2.2 Pattern Compliance Matrix

| Pattern | ADR | Flow 1 Compliance | Flow 2 Compliance |
|---------|-----|--------------------|--------------------|
| Adapter Pattern | ADR-003 | ✅ New `DAMImageAnalysisAdapter` extends `BaseAdapter` | ✅ New `SearchEnrichmentAdapter` extends `BaseAdapter` |
| Builder Pattern | ADR-007 | ✅ Uses `AgentBuilder.with_foundry_models()` | ✅ Uses `AgentBuilder` for new search agent |
| Saga Choreography | ADR-006 | ✅ Event Hub pub/sub chain: ingest → enrich → hitl → export | ✅ Event Hub: approval → search-enrich → index |
| MCP Exposition | ADR-004 | ✅ New MCP tools on `truth-enrichment` | ✅ New MCP tools on `ecommerce-catalog-search` |
| ACP Alignment | ADR-009 | N/A (internal enrichment) | ✅ Search results follow ACP product schema |
| SLM-First Routing | ADR-010 | ✅ SLM for gap detection, LLM for image analysis | ✅ SLM for keyword/filter, LLM for semantic/multi-query |
| Truth Layer | ADR-020 | ✅ Core flow extends enriched_data → HITL → approved_data | ✅ Reads from approved_data for search enrichment |
| Connector Registry | ADR-003 | ✅ DAM connector registered in domain factory | ✅ N/A |
| Resilience | ADR-019 | ✅ Circuit breaker on DAM/PIM calls via `BaseAdapter` | ✅ Fallback path already exists in `_search_products()` |

---

## 3. Flow 1: End-to-End Product Enrichment

### 3.1 C4 Container Diagram

```
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
C4Container
    title Flow 1 — End-to-End Product Enrichment (Container View)

    Person(staff, "Staff Reviewer", "Reviews AI-proposed attributes")

    System_Boundary(hub, "Holiday Peak Hub") {
        Container(ingestion, "truth-ingestion", "FastAPI/Python", "Ingests PIM feeds, publishes ingest events")
        Container(enrichment, "truth-enrichment", "FastAPI/Python", "Gap detection + AI enrichment via Foundry")
        Container(hitl, "truth-hitl", "FastAPI/Python", "Staff review queue with approve/reject")
        Container(export, "truth-export", "FastAPI/Python", "Writeback approved data to PIM")
        Container(ui, "UI", "Next.js 16", "Staff review page at /staff/review")
        
        ContainerDb(cosmos, "Cosmos DB", "Truth Store", "products, attributes_proposed, attributes_truth, schemas, audit")
        ContainerQueue(eventhubs, "Event Hubs", "Azure", "enrichment-jobs, hitl-jobs, export-jobs")
    }

    System_Ext(pim, "PIM System", "Akeneo / Salsify")
    System_Ext(dam, "DAM System", "Generic REST DAM")
    System_Ext(foundry, "Azure AI Foundry", "GPT-4o for image analysis, GPT-5-nano for gap detection")

    Rel(pim, ingestion, "Product feeds", "REST/webhook")
    Rel(ingestion, eventhubs, "Publishes ingestion-notifications")
    Rel(eventhubs, enrichment, "Subscribes enrichment-jobs")
    Rel(enrichment, dam, "Fetches product images", "REST")
    Rel(enrichment, foundry, "Image analysis + text enrichment", "REST")
    Rel(enrichment, cosmos, "Writes attributes_proposed")
    Rel(enrichment, eventhubs, "Publishes hitl-jobs")
    Rel(eventhubs, hitl, "Subscribes hitl-jobs")
    Rel(staff, ui, "Reviews proposals")
    Rel(ui, hitl, "Approve/reject API")
    Rel(hitl, cosmos, "Writes attributes_truth")
    Rel(hitl, eventhubs, "Publishes export-jobs")
    Rel(eventhubs, export, "Subscribes export-jobs")
    Rel(export, pim, "Writeback approved data", "REST")
```

### 3.2 Sequence Diagram — Event-Driven Enrichment

```
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
sequenceDiagram
    participant PIM as PIM System
    participant Ingest as truth-ingestion
    participant EH as Event Hubs
    participant Enrich as truth-enrichment
    participant DAM as DAM System
    participant Foundry as Azure AI Foundry
    participant Cosmos as Cosmos DB
    participant HITL as truth-hitl
    participant Staff as Staff UI
    participant Export as truth-export

    PIM->>Ingest: POST /ingest/product (webhook)
    Ingest->>Cosmos: Upsert ProductStyle + Variants
    Ingest->>EH: Publish ingestion-notifications<br/>{entity_id, category}

    Note over EH,Enrich: Existing subscription wiring

    EH->>Enrich: enrichment-jobs event
    
    rect rgb(255, 230, 230)
        Note over Enrich: Gap Detection Phase
        Enrich->>Cosmos: Fetch CategorySchema for category
        Enrich->>Enrich: Compare product vs schema required_fields
        Enrich->>Enrich: Identify missing attributes
    end

    rect rgb(230, 240, 255)
        Note over Enrich: DAM Image Analysis Phase (New)
        Enrich->>DAM: GET /api/assets?product_id={entity_id}
        DAM-->>Enrich: AssetData[] (image URLs, metadata)
        Enrich->>Foundry: GPT-4o vision: analyze images for<br/>color, material, pattern, style attributes
        Foundry-->>Enrich: Structured attribute extraction
    end

    rect rgb(230, 255, 230)
        Note over Enrich: Text Enrichment Phase (Existing)
        Enrich->>Foundry: GPT-5-nano: generate missing text attributes
        Foundry-->>Enrich: {value, confidence, evidence}
    end

    Enrich->>Cosmos: Upsert attributes_proposed<br/>{original_data, enriched_data, reasoning, status: pending}
    Enrich->>Cosmos: Append audit event
    
    alt confidence >= 0.95
        Enrich->>Cosmos: Auto-approve → attributes_truth
    else confidence < 0.95
        Enrich->>EH: Publish hitl-jobs<br/>{entity_id, field_name, proposed_id}
    end

    EH->>HITL: hitl-jobs event
    Staff->>HITL: GET /hitl/queue (review pending)
    HITL-->>Staff: Diff view: source vs enriched
    Staff->>HITL: POST /hitl/approve or /hitl/reject

    alt Approved
        HITL->>Cosmos: Promote enriched → attributes_truth
        HITL->>Cosmos: Append audit (approved)
        HITL->>EH: Publish export-jobs<br/>{entity_id, approved_fields}
    else Rejected
        HITL->>Cosmos: Mark rejected with reason
        HITL->>EH: Publish enrichment-jobs<br/>(re-enrich with feedback)
    end

    EH->>Export: export-jobs event
    Export->>Cosmos: Read approved attributes
    Export->>PIM: Writeback via PIM connector
    Export->>Cosmos: Append audit (exported)
```

### 3.3 Data Model — Enrichment Proposal Record

The existing `attributes_proposed` Cosmos container already stores proposed attributes. For image-analysis enrichment, extend the schema:

```python
# Extension to existing ProposedAttribute (enrichment_engine.py)
{
    "id": "uuid",
    "entity_id": "STYLE-123",
    "field_name": "material",
    "proposed_value": "100% organic cotton",
    "confidence": 0.87,
    "evidence": "Extracted from hero image texture analysis + product title context",
    "source_model": "gpt-4o",
    "source_type": "image_analysis",        # NEW: "text_enrichment" | "image_analysis" | "hybrid"
    "source_assets": ["asset-uuid-1"],      # NEW: DAM asset IDs used as evidence
    "original_data": {"material": null},    # NEW: snapshot of original field state
    "enriched_data": {"material": "100% organic cotton"},  # NEW: the proposed change
    "reasoning": "Image shows woven texture consistent with cotton...",  # NEW: detailed reasoning
    "status": "pending",
    "created_at": "2026-03-19T12:00:00Z"
}
```

**Cosmos container change**: No new container needed. The existing `attributes_proposed` container adds optional fields (`source_type`, `source_assets`, `original_data`, `enriched_data`, `reasoning`). Schema-free Cosmos DB handles this seamlessly.

### 3.4 What Changes in Existing Services

| Service | Change Type | Details |
|---------|-------------|---------|
| `truth-enrichment` | **Extend** | Add `DAMImageAnalysisAdapter` in `adapters.py`; add image analysis step in `enrichment_engine.py`; extend event handler to call DAM + Foundry GPT-4o |
| `truth-enrichment` | **Extend** | Upgrade `_detect_gaps()` to compare against full `CategorySchema` with required/recommended field differentiation |
| `truth-enrichment` | **Extend** | Add enhanced proposed record with `original_data`, `enriched_data`, `reasoning` fields |
| `truth-hitl` | **Minor** | Ensure diff view supports `source_assets` preview (image thumbnails) |
| `truth-export` | **None** | Already reads approved attributes and writes back via PIM connector |
| `truth-ingestion` | **Minor** | Publish `enrichment-jobs` event after successful ingestion (verify existing wiring) |

---

## 4. Flow 2: Intelligent Product Search

### 4.1 C4 Container Diagram

```
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
C4Container
    title Flow 2 — Intelligent Product Search (Container View)

    Person(shopper, "Shopper", "Searches products")
    Person(staff, "Staff", "Monitors search quality")

    System_Boundary(hub, "Holiday Peak Hub") {
        Container(searchEnrich, "search-enrichment-agent", "FastAPI/Python", "Generates use_cases, complements, substitutes per product")
        Container(catSearch, "ecommerce-catalog-search", "FastAPI/Python", "Dual-path search: keyword/filter + semantic/vector")
        Container(hitl, "truth-hitl", "FastAPI/Python", "Approval triggers search enrichment")
        Container(ui, "UI", "Next.js 16", "/search and /shop pages")
        
        ContainerDb(cosmosApproved, "Cosmos DB", "attributes_truth", "Approved product data")
        ContainerDb(cosmosSEP, "Cosmos DB", "search_enriched_products", "Enriched search data")
        ContainerQueue(eventhubs, "Event Hubs", "Azure", "search-enrichment-jobs")
        Container(indexer, "AI Search Indexer", "Azure", "Cosmos DB → AI Search pipeline with vectorization")
        ContainerDb(aiSearch, "Azure AI Search", "product_search_index", "Vectorized product index")
    }

    System_Ext(foundry, "Azure AI Foundry", "GPT-5-nano for enrichment, GPT-5 for multi-query interpretation")

    Rel(hitl, eventhubs, "Publishes search-enrichment-jobs on approval")
    Rel(eventhubs, searchEnrich, "Subscribes search-enrichment-jobs")
    Rel(searchEnrich, cosmosApproved, "Reads approved product data")
    Rel(searchEnrich, foundry, "Generate use_cases, complements, substitutes")
    Rel(searchEnrich, cosmosSEP, "Writes enriched search data")
    Rel(cosmosSEP, indexer, "Cosmos change feed → Indexer")
    Rel(indexer, aiSearch, "Vectorize + index")
    Rel(shopper, ui, "Search queries")
    Rel(ui, catSearch, "Search API")
    Rel(catSearch, aiSearch, "Vector/semantic search")
    Rel(catSearch, foundry, "Intent interpretation for complex queries")
```

### 4.2 Sequence Diagram — Background Enrichment + Indexing

```
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
sequenceDiagram
    participant HITL as truth-hitl
    participant EH as Event Hubs
    participant SEA as search-enrichment-agent
    participant Cosmos as Cosmos DB (approved)
    participant CosSEP as Cosmos DB (search_enriched)
    participant Foundry as Azure AI Foundry
    participant Indexer as AI Search Indexer
    participant AISearch as Azure AI Search

    Note over HITL,EH: Triggered by HITL approval (existing flow)
    HITL->>EH: Publish search-enrichment-jobs<br/>{entity_id, approved_fields}

    EH->>SEA: search-enrichment-jobs event
    SEA->>Cosmos: Fetch approved ProductStyle + attributes_truth
    SEA->>Foundry: GPT-5-nano: generate use_cases,<br/>complementary_products, substitute_products
    Foundry-->>SEA: Structured enrichment response
    
    SEA->>CosSEP: Upsert search_enriched_products<br/>{entity_id, use_cases[], complements[], substitutes[],<br/>enriched_description, search_keywords[]}

    Note over CosSEP,Indexer: Azure-managed Cosmos DB change feed → Indexer
    CosSEP-->>Indexer: Change feed detects new/updated document
    Indexer->>Indexer: AI Skills pipeline:<br/>1. Text splitting<br/>2. Embedding generation (text-embedding-3-large)<br/>3. Field mapping
    Indexer->>AISearch: Upsert vectorized document into product_search_index
```

### 4.3 Sequence Diagram — Agentic Search Query

```
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
sequenceDiagram
    participant User as Shopper
    participant UI as Next.js UI
    participant Agent as CatalogSearchAgent
    participant Foundry as Azure AI Foundry
    participant AISearch as Azure AI Search
    participant CRUD as CRUD Service

    User->>UI: "waterproof jacket for hiking in winter"
    UI->>Agent: POST /search {query, mode: "auto"}

    rect rgb(255, 230, 230)
        Note over Agent: Complexity Assessment (ADR-010)
        Agent->>Agent: Assess query complexity
        Note over Agent: Multi-attribute intent → COMPLEX
    end

    rect rgb(230, 240, 255)
        Note over Agent: Agentic Path (Complex Queries)
        Agent->>Foundry: GPT-5: interpret user intent<br/>→ extract: {category: "jackets",<br/>attributes: ["waterproof", "winter"],<br/>use_case: "hiking"}
        Foundry-->>Agent: Structured intent
        
        Agent->>AISearch: Multi-query retrieval:<br/>1. Vector search on enriched_description<br/>2. Filter: category="outerwear"<br/>3. Semantic search on use_cases="hiking"
        AISearch-->>Agent: Ranked results with scores
        
        Agent->>Foundry: GPT-5: validate characteristics<br/>matching + rank explanation
        Foundry-->>Agent: Re-ranked results with reasoning
    end

    Agent->>CRUD: Resolve inventory/price for top results
    CRUD-->>Agent: Availability + pricing

    Agent-->>UI: ACP-formatted results with<br/>complementary_products, substitutes
    UI-->>User: Search results with recommendations
```

### 4.4 Non-Agentic Path (Simple Queries)

```
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
sequenceDiagram
    participant User as Shopper
    participant UI as Next.js UI
    participant Agent as CatalogSearchAgent
    participant AISearch as Azure AI Search
    participant CRUD as CRUD Service

    User->>UI: "SKU-12345" or "Nike Air Max"
    UI->>Agent: POST /search {query, mode: "auto"}

    rect rgb(230, 255, 230)
        Note over Agent: Complexity Assessment
        Agent->>Agent: Assess: SKU lookup or brand match → SIMPLE
    end

    Agent->>AISearch: Keyword/filter search<br/>top=10, filter by sku or brand
    AISearch-->>Agent: Direct matches

    Agent->>CRUD: Resolve availability
    CRUD-->>Agent: Inventory + price
    Agent-->>UI: ACP-formatted results
    UI-->>User: Product results
```

### 4.5 Data Model — Search Enriched Products

**New Cosmos container**: `search_enriched_products`

```python
{
    "id": "STYLE-123",
    "entity_id": "STYLE-123",
    "partition_key": "outerwear",          # categoryId for partition alignment
    
    # Core product data (denormalized from approved truth)
    "sku": "SKU-12345",
    "name": "Alpine Pro Waterproof Jacket",
    "brand": "MountainGuard",
    "category": "outerwear",
    "description": "Approved product description...",
    "price": 189.99,
    
    # Search enrichment fields (AI-generated)
    "use_cases": ["hiking", "winter sports", "outdoor work", "camping"],
    "complementary_products": ["SKU-67890", "SKU-11111"],   # SKU references
    "substitute_products": ["SKU-22222", "SKU-33333"],
    "search_keywords": ["waterproof", "breathable", "insulated", "gore-tex"],
    "enriched_description": "Extended description optimized for search...",
    
    # Metadata
    "enriched_at": "2026-03-19T12:00:00Z",
    "enrichment_model": "gpt-5-nano",
    "source_approval_version": 3,
    "ttl": -1
}
```

### 4.6 AI Search Index — `product_search_index`

```json
{
    "name": "product_search_index",
    "fields": [
        {"name": "id", "type": "Edm.String", "key": true, "filterable": true},
        {"name": "entity_id", "type": "Edm.String", "filterable": true},
        {"name": "sku", "type": "Edm.String", "filterable": true, "searchable": true},
        {"name": "name", "type": "Edm.String", "searchable": true, "analyzer": "en.microsoft"},
        {"name": "brand", "type": "Edm.String", "filterable": true, "facetable": true, "searchable": true},
        {"name": "category", "type": "Edm.String", "filterable": true, "facetable": true},
        {"name": "description", "type": "Edm.String", "searchable": true, "analyzer": "en.microsoft"},
        {"name": "price", "type": "Edm.Double", "filterable": true, "sortable": true, "facetable": true},
        {"name": "use_cases", "type": "Collection(Edm.String)", "filterable": true, "searchable": true},
        {"name": "complementary_products", "type": "Collection(Edm.String)", "filterable": true},
        {"name": "substitute_products", "type": "Collection(Edm.String)", "filterable": true},
        {"name": "search_keywords", "type": "Collection(Edm.String)", "searchable": true},
        {"name": "enriched_description", "type": "Edm.String", "searchable": true},
        {"name": "description_vector", "type": "Collection(Edm.Single)", "dimensions": 3072, "vectorSearchProfile": "default-vector-profile"}
    ],
    "vectorSearch": {
        "algorithms": [{"name": "hnsw-algo", "kind": "hnsw", "hnswParameters": {"m": 4, "efConstruction": 400, "efSearch": 500, "metric": "cosine"}}],
        "profiles": [{"name": "default-vector-profile", "algorithmConfigurationName": "hnsw-algo", "vectorizer": "text-embedding-vectorizer"}],
        "vectorizers": [{"name": "text-embedding-vectorizer", "kind": "azureOpenAI", "azureOpenAIParameters": {"modelName": "text-embedding-3-large", "deploymentId": "text-embedding-3-large", "resourceUri": "${FOUNDRY_ENDPOINT}"}}]
    },
    "semantic": {
        "configurations": [{"name": "default-semantic", "prioritizedFields": {"titleField": {"fieldName": "name"}, "contentFields": [{"fieldName": "enriched_description"}, {"fieldName": "description"}], "keywordsFields": [{"fieldName": "search_keywords"}, {"fieldName": "use_cases"}]}}]
    }
}
```

---

## 5. New/Modified Infrastructure

### 5.1 Cosmos DB Containers

| Container | Status | Partition Key | Purpose |
|-----------|--------|---------------|---------|
| `products` | **Existing** | `/categoryId` | Product styles and variants |
| `attributes_proposed` | **Existing** — schema extended | `/entityId` | Add `source_type`, `source_assets`, `original_data`, `enriched_data`, `reasoning` |
| `attributes_truth` | **Existing** | `/entityId` | Approved canonical attributes |
| `schemas` | **Existing** | `/categoryId` | Category schemas for gap detection |
| `audit` | **Existing** | `/entityId` | Immutable audit trail |
| `search_enriched_products` | **NEW** | `/category` | Denormalized search-enrichment data with use_cases, complements, substitutes |
| *(all others)* | **Existing** | *(unchanged)* | config, mappings, relationships, completeness |

**Rationale for `search_enriched_products` as a separate container** (not embedded in `products`):

1. **Different access pattern** — search indexer reads this continuously via change feed; embedding in `products` would trigger unnecessary re-indexing on non-search attribute changes
2. **Different partition key need** — indexed by `category` for search faceting, vs `categoryId` in products
3. **Independent lifecycle** — search enrichment can be reprocessed without touching the truth source
4. **Container-level throughput isolation** — search indexer is a continuous workload; isolating it prevents RU contention with HITL review reads/writes

### 5.2 Event Hub Topics

| Topic | Status | Publishers | Subscribers |
|-------|--------|-----------|-------------|
| `enrichment-jobs` | **Existing** | `truth-ingestion` | `truth-enrichment` |
| `hitl-jobs` | **Existing** | `truth-enrichment` | `truth-hitl` |
| `export-jobs` | **Existing** | `truth-hitl` | `truth-export` |
| `ingestion-notifications` | **Existing** | `truth-ingestion` | *(various)* |
| `search-enrichment-jobs` | **NEW** | `truth-hitl` | `search-enrichment-agent` |

**One new topic** only. The `search-enrichment-jobs` topic carries HITL approval events specifically for the search enrichment pipeline, keeping it decoupled from the PIM writeback flow (EIP: Content-Based Router — separate channels for separate consumers).

### 5.3 AI Search Indexes

| Index | Status | Data Source | Population Method |
|-------|--------|------------|-------------------|
| `catalog-products` | **Existing** | Manual push | `upsert_catalog_document()` in `ai_search.py` — keep as-is for backward compat |
| `product_search_index` | **NEW** | `search_enriched_products` Cosmos container | Azure AI Search indexer with Cosmos DB data source + AI skills pipeline (vectorization) |

**Indexer configuration**:
- **Data source**: Cosmos DB change feed on `search_enriched_products`
- **Skillset**: Text splitting → embedding generation (`text-embedding-3-large`) → field mapping
- **Schedule**: Every 5 minutes (configurable) or change-feed triggered
- **Field mappings**: Direct mapping from Cosmos document fields to index schema

---

## 6. New Adapters

### 6.1 Flow 1 — New Adapters

| Adapter | Location | Extends | Purpose |
|---------|----------|---------|---------|
| `DAMImageAnalysisAdapter` | `apps/truth-enrichment/src/truth_enrichment/adapters.py` | `BaseAdapter` (circuit breaker, rate limiter inherited) | Fetches images from Generic DAM connector, sends to Foundry GPT-4o for vision analysis, returns extracted attributes |
| *(none new in lib)* | — | — | Existing `GenericDAMConnector` in `lib/integrations/dam_generic.py` provides asset fetching; the adapter wraps it with Foundry vision calls |

**Implementation sketch**:

```python
class DAMImageAnalysisAdapter(BaseAdapter):
    """Fetch product images from DAM and extract attributes via Foundry GPT-4o."""

    def __init__(self, dam_connector: GenericDAMConnector, foundry_invoker: ModelInvoker):
        super().__init__(timeout=30.0, retries=2)
        self._dam = dam_connector
        self._invoker = foundry_invoker

    async def _fetch_impl(self, query: dict[str, Any]) -> list[dict[str, Any]]:
        entity_id = query["entity_id"]
        missing_fields = query.get("missing_fields", [])
        
        assets = await self._dam.get_assets_for_product(entity_id)
        if not assets:
            return []
        
        # Send primary/hero image to GPT-4o vision
        primary = next((a for a in assets if a.role == "primary"), assets[0])
        response = await self._invoker(
            messages=self._build_vision_prompt(primary.url, missing_fields),
        )
        return [{"source_type": "image_analysis", "source_assets": [primary.id], **response}]
```

### 6.2 Flow 2 — New Adapters

| Adapter | Location | Extends | Purpose |
|---------|----------|---------|---------|
| `SearchEnrichmentAdapter` | `apps/search-enrichment-agent/src/adapters.py` | `BaseAdapter` | Reads approved product data from Cosmos, writes enriched search data to `search_enriched_products` |
| `AISearchIndexAdapter` | `apps/ecommerce-catalog-search/src/ecommerce_catalog_search/adapters.py` | Extends existing `CatalogAdapters` | Queries `product_search_index` with vector/semantic/hybrid capabilities |

---

## 7. New Agents vs Extending Existing

### 7.1 Decision Matrix

| Component | Decision | Rationale |
|-----------|----------|-----------|
| **Product enrichment with DAM images** | **Extend `truth-enrichment`** | Same bounded context (product data enrichment). Adding a DAM analysis step is a capability extension, not a new domain. Already has `EnrichmentEngine`, `EnrichmentAdapters`, and event handlers. Creating a separate service would violate DDD — it's the same aggregate (enrichment proposal). |
| **Search enrichment agent** | **NEW service: `search-enrichment-agent`** | Different bounded context (search optimization ≠ truth enrichment). Different output container. Different consumer (AI Search indexer, not HITL). Follows microservices.io "Database per Service" — owns `search_enriched_products`. |
| **Agentic search** | **Extend `ecommerce-catalog-search`** | Same bounded context (product search). Already has `CatalogSearchAgent`, `AISearchConfig`, `search_catalog_skus_detailed()`. Adding agentic intent interpretation is a capability upgrade to the existing agent, not a new domain. |
| **AI Search indexer** | **Azure-managed infrastructure** | Not a service — it's an Azure AI Search indexer resource configured declaratively. No custom code needed. |

### 7.2 New Service: `search-enrichment-agent`

```
apps/search-enrichment-agent/
├── src/
│   └── search_enrichment/
│       ├── __init__.py
│       ├── main.py              # build_service_app() with event handler
│       ├── agents.py            # SearchEnrichmentAgent(BaseRetailAgent)
│       ├── adapters.py          # SearchEnrichmentAdapters
│       ├── enrichment_engine.py # Generate use_cases, complements, substitutes
│       ├── event_handlers.py    # Handle search-enrichment-jobs events
│       └── routes.py            # REST + MCP endpoints
├── Dockerfile
└── pyproject.toml
```

Follows the identical Agent/Adapter/Schema pattern of every other service.

### 7.3 Extension: `truth-enrichment` Changes

```
apps/truth-enrichment/src/truth_enrichment/
├── adapters.py          # + DAMImageAnalysisAdapter
├── agents.py            # + enrich_with_images() method
├── enrichment_engine.py # + build_vision_prompt(), parse_vision_response()
├── event_handlers.py    # + DAM image analysis step in handle_enrichment_job()
└── (rest unchanged)
```

### 7.4 Extension: `ecommerce-catalog-search` Changes

```
apps/ecommerce-catalog-search/src/ecommerce_catalog_search/
├── agents.py    # + complexity assessment, agentic multi-query path
├── ai_search.py # + vector_search(), semantic_search(), hybrid_search()
├── adapters.py  # + AISearchIndexAdapter in CatalogAdapters
└── (rest unchanged)
```

---

## 8. Migration Path

### Phase 1: Foundation (Week 1-2)

1. **Create `search_enriched_products` Cosmos container** with partition key `/category`
2. **Create `search-enrichment-jobs` Event Hub topic**
3. **Define `product_search_index` schema** in Azure AI Search
4. **Configure Azure AI Search indexer** with Cosmos DB data source on `search_enriched_products`
5. **Extend `attributes_proposed` schema** with optional `source_type`, `source_assets`, `original_data`, `enriched_data`, `reasoning` fields

### Phase 2: Flow 1 — Enrichment Extension (Week 2-3)

1. **Add `DAMImageAnalysisAdapter`** to `truth-enrichment/adapters.py`
2. **Extend `EnrichmentEngine`** with `build_vision_prompt()` and `parse_vision_response()`
3. **Update `handle_enrichment_job()`** to include DAM fetch + image analysis step
4. **Extend MCP tools**: Add `/enrich/image-analysis` tool
5. **Update UI**: Add image thumbnail preview in `/staff/review` diff view
6. **Test**: Integration test with mock DAM + mock Foundry

### Phase 3: Flow 2 — Search Pipeline (Week 3-4)

1. **Create `search-enrichment-agent` service** following Agent/Adapter/Schema pattern
2. **Extend `truth-hitl`** to publish `search-enrichment-jobs` on approval
3. **Implement `SearchEnrichmentAgent`** with use_cases/complements/substitutes generation
4. **Verify indexer pipeline**: Cosmos change feed → skillset → `product_search_index`
5. **Backfill**: Run search enrichment for all existing approved products

### Phase 4: Agentic Search (Week 4-5)

1. **Extend `CatalogSearchAgent`** with complexity assessment and dual-path routing
2. **Add vector/semantic search functions** to `ai_search.py`
3. **Switch `ecommerce-catalog-search` default index** from `catalog-products` to `product_search_index`
4. **Update UI `/search` page**: Support agentic search results with complementary/substitute products
5. **Keep `catalog-products` index** as fallback (graceful degradation)

### Phase 5: Validation & Cutover (Week 5-6)

1. **A/B test**: Route 10% traffic to new search pipeline
2. **Monitor**: Search relevance metrics, latency, RU consumption
3. **Cutover**: Make `product_search_index` the primary index
4. **Deprecate**: Manual `upsert_catalog_document()` population path (keep as fallback)

---

## 9. ADR Recommendations

### Proposed: DAM Image Analysis for Product Enrichment

**Status**: Proposed  
**Decision**: Extend `truth-enrichment` with DAM image retrieval and Foundry GPT-4o vision analysis for attribute extraction. Image-derived attributes follow the same HITL review workflow as text-derived attributes.  
**Key trade-off**: GPT-4o vision calls cost ~10x more than text-only enrichment. Mitigated by: (a) only processing products with missing visual attributes, (b) batch processing during off-peak hours, (c) caching extracted attributes per asset ID.  
**Pattern**: Pipes and Filters (EIP) — DAM fetch → image analysis → confidence scoring → HITL routing.

### Proposed: Search Enrichment as Separate Bounded Context

**Status**: Proposed  
**Decision**: Create `search-enrichment-agent` as a new service owning `search_enriched_products`, rather than embedding search enrichment in `truth-enrichment`.  
**Key trade-off**: One more service to operate vs. clean bounded context separation. The search enrichment domain has different data output, different consumers, different throughput profile, and different failure modes.  
**Pattern**: Database per Service (microservices.io) — `search-enrichment-agent` owns its Cosmos container.

### Proposed: Azure AI Search Indexer for Auto-Population

**Status**: Proposed  
**Decision**: Use Azure-managed AI Search indexer with Cosmos DB change feed data source and AI skills pipeline for vectorization, replacing manual `upsert_catalog_document()` calls.  
**Key trade-off**: Less control over indexing timing vs. zero custom indexing code. Azure indexer supports configurable scheduling (every 5 min) and change detection. Skillset handles embedding generation.  
**Pattern**: Event-Carried State Transfer (EIP) — Cosmos change feed is the event that triggers index update.

### Proposed: Dual-Path Search Routing

**Status**: Proposed  
**Decision**: Extend `CatalogSearchAgent` with complexity assessment to route simple queries (SKU lookup, brand filter) through keyword/filter search, and complex queries (natural language intent) through agentic multi-query retrieval with Foundry validation.  
**Key trade-off**: Complexity assessment adds ~50ms overhead. Mitigated by: simple heuristics run first (lexical signals from ADR-010), embedding-based assessment only on ambiguous cases.  
**Pattern**: Content-Based Router (EIP) — route request to appropriate processing path based on assessed complexity.

---

## 10. Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| GPT-4o vision latency (2-5s per image) blocks enrichment throughput | Medium | High | Process images asynchronously; batch during off-peak; cache per asset ID |
| AI Search indexer lag creates stale search results | Low | Medium | Configure 5-min indexer schedule; add manual trigger endpoint for urgent updates |
| `search_enriched_products` RU cost from continuous indexer reads | Medium | Medium | Use Cosmos autoscale 400-4000 RU/s; monitor with Azure Monitor alerts |
| Complementary/substitute product SKU references become stale | Low | Medium | Include `enriched_at` timestamp; re-enrich on product updates; TTL-based staleness detection |
| Dual-path routing misclassifies complex queries as simple | Medium | Low | SLM-first with confidence-based escalation (ADR-010 pattern already addresses this) |
| DAM connector auth failures cascade to enrichment pipeline | High | Low | Circuit breaker on `DAMImageAnalysisAdapter` (`BaseAdapter` provides this); skip image analysis on DAM failure, continue text-only enrichment |

---

## Appendix A: Event Hub Topology Update

| Topic | Publishers | Subscribers |
|-------|-----------|-------------|
| `ingestion-notifications` | `truth-ingestion` | `truth-enrichment`, `product-management-*` |
| `enrichment-jobs` | `truth-ingestion` | `truth-enrichment` |
| `hitl-jobs` | `truth-enrichment` | `truth-hitl` |
| `export-jobs` | `truth-hitl` | `truth-export` |
| **`search-enrichment-jobs`** | **`truth-hitl`** | **`search-enrichment-agent`** |
| `order-events` | CRUD | CRM, ecommerce, inventory, logistics |
| `payment-events` | CRUD | `crm-campaign-intelligence` |
| `return-events` | CRUD | `logistics-returns-support`, `crm-support-assistance` |
| `inventory-events` | CRUD | ecommerce, inventory |
| `user-events` | CRUD | CRM |
| `shipment-events` | CRUD | *(pending)* |

## Appendix B: Service Count Impact

| Category | Before | After | Delta |
|----------|--------|-------|-------|
| Existing services (unchanged) | 21 | 21 | 0 |
| Extended services | 0 | 2 | +2 (`truth-enrichment`, `ecommerce-catalog-search`) |
| New services | 0 | 1 | +1 (`search-enrichment-agent`) |
| Azure-managed components | — | 1 | +1 (AI Search indexer — infrastructure, not a service) |
| **Total AKS services** | **21** | **22** | **+1** |
