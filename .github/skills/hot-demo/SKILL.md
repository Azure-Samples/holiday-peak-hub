---
name: hot-demo
description: "End-to-end customer demo orchestration: CSV export from CRUD, blob upload, Event Hub triggered enrichment (UCP/ACP), AI Search vectorized indexing, and agentic semantic search — with streaming UI, live tracing, and independent step execution."
argument-hint: "Run the full hot-demo pipeline, or specify a step: export-csv, upload-blob, enrich, index, search, or frontend."
user-invocable: true
disable-model-invocation: false
---

# Hot Demo: Agentic Retail Data Pipeline

## Purpose

Deliver a live, customer-facing demonstration of the agentic retail data pipeline — from raw product data through AI enrichment to intelligent semantic search. Each step is independently executable and traceable, enabling live re-runs during the demo.

## When To Use

Use this skill when you need to:
- Prepare and execute the end-to-end agentic retail demo for customer conversations.
- Export CRUD mock products to CSV, upload to Blob, trigger enrichment via Event Hub, populate AI Search, and run semantic queries.
- Validate that each pipeline step works independently and produces traceable output.
- Ensure the frontend supports streaming, live logs, CSV upload, and sub-5s search latency.

## Non-Functional Requirements

| Requirement | Target | Validation |
|---|---|---|
| Search latency | < 5 seconds end-to-end | Measure from query submit to first result rendered |
| Enrichment independence | Search works while AI Search is being populated | CRUD fallback path must remain functional |
| Streaming | All agent responses stream via SSE | ChatWidget uses `searchStream()` path |
| Traceability | Every step emits structured logs with `entity_id` | Foundry tracer + Application Insights |
| Re-runnability | Upload a new CSV live → triggers full pipeline again | Event Hub subscription must handle repeat entity IDs |
| Upload interface | Admin UI supports CSV file upload at `/admin/enrichment-monitor` | File input + POST to truth-ingestion bulk endpoint |

## Architecture Overview

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
flowchart LR
  A["CRUD Service<br/>(seed data)"] -->|"GET /api/products"| B["Export to CSV<br/>(demo script)"]
  B -->|"Upload CSV"| C["Blob Storage<br/>(raw_data container)"]
  C -->|"Event Hub<br/>enrichment-jobs"| D["Truth-Enrichment<br/>Agent"]
  D -->|"UCP/ACP gaps<br/>+ AI model"| E["Proposed Attributes<br/>(Cosmos DB)"]
  E -->|"Auto-approve ≥0.95<br/>or HITL review"| F["Approved Truth<br/>(Cosmos DB)"]
  F -->|"Event Hub<br/>search-enrichment-jobs"| G["Search-Enrichment<br/>Agent"]
  G -->|"use_cases, keywords<br/>enriched_description"| H["AI Search Index<br/>(vectorized)"]
  H -->|"Hybrid search<br/>keyword + vector"| I["Catalog-Search<br/>Agent"]
  I -->|"SSE streaming"| J["Frontend UI<br/>(Next.js)"]
```

## Ownership Model

| Step | Primary Agent | Supporting Agent | Human Role |
|---|---|---|---|
| 1. CSV Export | **PythonDeveloper** | — | Verify CSV content |
| 2. Blob Upload + Event Hub Trigger | **PythonDeveloper** | — | Trigger via admin UI or script |
| 3. Truth Enrichment Pipeline | **PythonDeveloper** | SystemArchitect (if schema changes needed) | Monitor enrichment-monitor dashboard |
| 4. Search Enrichment + AI Search Indexing | **PythonDeveloper** | — | Verify index population |
| 5. Semantic Search Validation | **PythonDeveloper** | — | Run demo queries |
| 6. Frontend: Streaming + Upload + Tracing | **TypeScriptDeveloper** | UIDesigner (accessibility) | Demo operator |
| 7. Integration Validation | **PythonDeveloper** + **TypeScriptDeveloper** | PlatformEngineer (if infra issues) | Final sign-off |

## Pipeline Steps

### Step 1: Export CRUD Products to CSV

**Agent**: PythonDeveloper
**Scope**: Create `scripts/demo/export_products_csv.py`

**Requirements**:
- Call `GET /api/products?limit=200` from CRUD service (uses `CRUD_SERVICE_URL` env var, or `http://localhost:8000` for local)
- Map each product to a flat CSV row with columns:
  - `entity_id`, `sku`, `name`, `description`, `brand`, `category`, `price`, `currency`, `image_url`, `features`, `rating`, `tags`
- `features` and `tags` columns must be pipe-delimited (`|`) for multi-value fields
- Save to `docs/demos/sample-data/products_export.csv`
- Also produce `docs/demos/sample-data/products_export.json` (array of raw product dicts) for programmatic re-use
- Script must be idempotent — re-running overwrites the previous export
- Print summary: total products exported, categories found, output file paths

**Acceptance Criteria**:
- [ ] CSV is valid, loadable in Excel/pandas, has header row
- [ ] JSON output matches CSV content 1:1
- [ ] At least 100 products across 11 categories (matches seed data)
- [ ] Script runs without CRUD service if `--mock` flag is passed (uses embedded seed data)

### Step 2: Upload CSV to Blob + Trigger Enrichment

**Agent**: PythonDeveloper
**Scope**: Create `scripts/demo/upload_and_trigger.py`

**Requirements**:
- Read the CSV from Step 1 (or accept `--csv-path` argument)
- Upload each product as individual JSON blob to Azure Blob Storage:
  - Container: `raw_data` (env var `TRUTH_PRODUCT_BLOB_CONTAINER`, override to `raw_data`)
  - Blob name: `{entity_id}.json`
  - Account URL from `BLOB_ACCOUNT_URL` env var
  - Auth via `DefaultAzureCredential` (Managed Identity in AKS, `az login` locally)
- After upload batch completes, publish one `enrichment-jobs` event per product to Event Hub:
  - Use `TruthEventPublisher` from `holiday_peak_lib.utils.truth_event_hub`
  - Payload: `{"event_type": "product.uploaded", "data": {"entity_id": "<id>", "source": "csv_upload"}}`
  - Namespace env: `PLATFORM_JOBS_EVENT_HUB_NAMESPACE` / connection string env: `PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING`
- Support `--dry-run` flag (logs actions without executing)
- Support `--batch-size N` for upload concurrency (default 10)

**Acceptance Criteria**:
- [ ] Blobs appear in `raw_data` container (verify via Azure Portal or `az storage blob list`)
- [ ] Event Hub receives `enrichment-jobs` events (verify via consumer group or agent logs)
- [ ] Truth-Enrichment agent starts processing within 30 seconds of event publish
- [ ] Script handles auth errors gracefully with clear error messages
- [ ] Re-upload of same CSV replaces existing blobs (idempotent)

### Step 3: Truth Enrichment Processing

**Agent**: PythonDeveloper
**Scope**: Verify and extend `apps/truth-enrichment/`

**Requirements**:
- Truth-Enrichment agent (`TruthEnrichmentAgent`) is already wired to `enrichment-jobs` Event Hub topic
- `BlobProductStoreAdapter` reads product JSON from `raw_data` container when `BLOB_ACCOUNT_URL` and `TRUTH_PRODUCT_BLOB_CONTAINER` are set
- For each product, the agent:
  1. Loads product from blob → `get_product(entity_id)`
  2. Loads UCP schema for category → `get_schema(category)`
  3. Detects attribute gaps via `_detect_gaps(product, schema)`
  4. For each gap: runs vision analysis (DAM) + text enrichment (Foundry model)
  5. Merges candidates with confidence weighting → `merge_enrichment_candidates()`
  6. Auto-approves if confidence ≥ 0.95; otherwise queues to HITL
  7. Persists proposed attributes → `ProposedAttributeStoreAdapter.upsert()`
  8. Publishes HITL review events to `hitl-jobs` Event Hub topic
- After all fields enriched, publish `search-enrichment-jobs` event for the entity

**What may need implementation**:
- Ensure the enrichment agent publishes to `search-enrichment-jobs` after completing enrichment for an entity (bridge between truth-enrichment → search-enrichment)
- Add a route or background task to export enriched data as `enriched_data.csv` to blob storage
- Ensure UCP schemas exist for all 11 seed categories (currently: apparel, footwear, electronics, home_furniture, beauty — may need: toys_games, sports_outdoors, books_media, jewelry_watches, food_gourmet, pet_supplies)

**Acceptance Criteria**:
- [ ] Agent processes events from `enrichment-jobs` within 30 seconds
- [ ] Each product gets proposed attributes with confidence scores
- [ ] High-confidence attributes (≥ 0.95) are auto-approved
- [ ] Lower-confidence attributes appear in HITL review queue (`/staff/review`)
- [ ] `search-enrichment-jobs` event is published per entity after enrichment
- [ ] Enrichment monitor dashboard (`/admin/enrichment-monitor`) shows active jobs and status cards

### Step 4: Search Enrichment + AI Search Indexing

**Agent**: PythonDeveloper
**Scope**: Verify and extend `apps/search-enrichment-agent/`

**Requirements**:
- Search-Enrichment agent (`SearchEnrichmentOrchestrator`) is wired to `search-enrichment-jobs` Event Hub
- For each entity:
  1. Fetch approved truth data from `ApprovedTruthAdapter`
  2. Determine complexity (simple vs complex based on text length/feature count)
  3. Simple: deterministic field generation (use_cases, keywords, enriched_description)
  4. Complex: model-assisted enrichment via `FoundryEnrichmentAdapter`
  5. Persist `SearchEnrichedProduct` to `SearchEnrichedStoreAdapter`
  6. Push to AI Search index via `SearchIndexingAdapter.sync_after_upsert()`
- AI Search index fields: `sku`, `name`, `description`, `brand`, `category`, `price`, `use_cases`, `complementary_products`, `substitute_products`, `search_keywords`, `enriched_description`, `content_vector`
- Set `AI_SEARCH_PUSH_IMMEDIATE=true` for demo (bypasses indexer-based sync for real-time indexing)

**Acceptance Criteria**:
- [ ] Agent processes `search-enrichment-jobs` events
- [ ] Enriched products appear in AI Search index with vectorized `content_vector` field
- [ ] Index is queryable via both keyword and vector search
- [ ] `enriched_description` contains category-aware narrative content
- [ ] `use_cases` field captures product utility scenarios (critical for demo queries)

### Step 5: Semantic Search Validation

**Agent**: PythonDeveloper
**Scope**: Create `scripts/demo/validate_search.py`

**Requirements**:
- Run the following demo queries against the catalog-search agent endpoint (`/search` or `/agent/search`):
  1. `"I'm traveling to Russia. Which clothes should I take?"`
  2. `"I'm travelling to Caribe. What do you have for me?"`
  3. `"I'm buying a new house, 140 square meters. I need furniture, and I like modern stuff"`
  4. `"My dog eat his collar. Help me out"`
- For each query:
  - Record: response time (must be < 5 seconds), result count, top-3 product names, intent classification, search mode used
  - Verify results are contextually relevant (clothing for travel, furniture for house, pet supplies for dog)
  - Log the full response for demo traceability
- Output results as a formatted table to stdout and save to `docs/demos/sample-data/search_validation_results.json`

**Acceptance Criteria**:
- [ ] All 4 queries return results within 5 seconds
- [ ] Query 1 (Russia travel): returns cold-weather clothing items
- [ ] Query 2 (Caribe travel): returns warm-weather/beach items
- [ ] Query 3 (new house furniture): returns modern furniture items
- [ ] Query 4 (dog collar): returns pet supplies
- [ ] Intent classification identifies category and use_case correctly
- [ ] Results come from AI Search (not CRUD fallback) when index is populated

### Step 6: Frontend Enhancements

**Agent**: TypeScriptDeveloper
**Scope**: `apps/ui/`

**6.1 Streaming Search (already implemented)**:
- `ChatWidget.tsx` uses `searchStream()` for SSE-based progressive rendering
- `useStreamingSearch` hook handles `onResults`, `onToken`, `onDone`, `onError` callbacks
- Verify streaming works end-to-end with live agent

**6.2 CSV Upload Interface**:
- Add a CSV upload component to `/admin/enrichment-monitor` page
- Component: `CsvUploadPanel`
  - File input accepting `.csv` files
  - Upload button that:
    1. Parses CSV client-side (validate headers match expected schema)
    2. POSTs parsed products to truth-ingestion bulk endpoint: `POST /ingest/bulk`
    3. Shows upload progress (product count, success/failure counts)
    4. After upload, triggers enrichment by publishing events via backend endpoint
  - Status display: uploading → processing → complete (with product counts)
  - Re-upload button to trigger another round with new CSV

**6.3 Live Processing Logs**:
- Add a `LiveProcessingPanel` component to `/admin/enrichment-monitor`
- Connects to backend SSE endpoint for real-time enrichment status
- Shows: entity being processed, current step (gap detection / vision analysis / text enrichment / approval), confidence scores, HITL queue count
- Auto-scrolls log entries
- Filter by entity_id or status

**6.4 Search Tracing**:
- Ensure search results page shows:
  - Response latency (ms)
  - Search mode used (keyword / intelligent / hybrid)
  - Intent classification (category, use_case, confidence)
  - Source indicator (AI Search vs CRUD fallback)
  - Subqueries generated (for complex intent)

**6.5 Evaluation Panel**:
- Add evaluation display to search results:
  - Side-by-side comparison: enriched result vs raw CRUD result
  - Enrichment quality indicators (has use_cases, has enriched_description, confidence score)
  - Search relevance score from AI Search

**Acceptance Criteria**:
- [ ] ChatWidget streams tokens progressively (no flash-of-full-content)
- [ ] CSV upload panel appears on enrichment-monitor page
- [ ] Upload triggers enrichment pipeline (visible in live logs)
- [ ] Live logs show real-time processing status per entity
- [ ] Search results display latency, mode, intent, and source
- [ ] All UI components follow existing Tailwind + design token conventions
- [ ] WCAG 2.2 AA compliant (keyboard navigation, screen reader labels, focus management)

## Demo Validation Queries

These queries must return relevant results within 5 seconds:

| # | Query | Expected Category | Expected Behavior |
|---|---|---|---|
| 1 | "I'm traveling to Russia. Which clothes should I take?" | Clothes & Apparel | Returns cold-weather items (coats, boots, layers) |
| 2 | "I'm travelling to Caribe. What do you have for me?" | Clothes & Apparel, Sports & Outdoors | Returns warm-weather items (swimwear, sunscreen, sandals) |
| 3 | "I'm buying a new house, 140 square meters. I need furniture, and I like modern stuff" | Furniture | Returns modern furniture items (sofas, desks, shelving) |
| 4 | "My dog eat his collar. Help me out" | Pet Supplies | Returns pet collars, leashes, and dog accessories |

## Environment Variables Reference

### Required for Demo Pipeline

| Variable | Service | Purpose | Example |
|---|---|---|---|
| `CRUD_SERVICE_URL` | export script | CRUD API base URL | `http://crud-service:8000` |
| `BLOB_ACCOUNT_URL` | upload script, truth-enrichment | Blob Storage account | `https://<account>.blob.core.windows.net` |
| `TRUTH_PRODUCT_BLOB_CONTAINER` | upload script, truth-enrichment | Blob container name | `raw_data` |
| `PLATFORM_JOBS_EVENT_HUB_NAMESPACE` | upload script, agents | Event Hub FQDN | `<namespace>.servicebus.windows.net` |
| `PLATFORM_JOBS_EVENT_HUB_CONNECTION_STRING` | upload script, agents | Event Hub connection string (if not using MI) | `Endpoint=sb://...` |
| `AI_SEARCH_ENDPOINT` | catalog-search | Azure AI Search endpoint | `https://<service>.search.windows.net` |
| `AI_SEARCH_INDEX` | catalog-search | Lexical index name | `products` |
| `AI_SEARCH_VECTOR_INDEX` | catalog-search | Vector index name | `products-vector` |
| `AI_SEARCH_AUTH_MODE` | catalog-search | Auth mode | `managed_identity` or `api_key` |
| `AI_SEARCH_PUSH_IMMEDIATE` | search-enrichment | Push to index immediately | `true` |
| `EMBEDDING_DEPLOYMENT_NAME` | catalog-search | Azure OpenAI embedding model | `text-embedding-3-large` |
| `PROJECT_ENDPOINT` | all agents | Azure AI Foundry endpoint | `https://<resource>.services.ai.azure.com/api/projects/<project>` |

### Foundry Model Configuration

| Variable | Purpose | Demo Value |
|---|---|---|
| `MODEL_DEPLOYMENT_NAME_FAST` | SLM for intent classification | `gpt-5-nano` |
| `MODEL_DEPLOYMENT_NAME_RICH` | LLM for enrichment + search synthesis | `gpt-5` |
| `FOUNDRY_STREAM` | Enable streaming | `true` |

## Execution Workflow

### Pre-Demo Setup (Run Once)

```bash
# 1. Export products from CRUD
python scripts/demo/export_products_csv.py

# 2. Upload to blob + trigger enrichment
python scripts/demo/upload_and_trigger.py

# 3. Wait for enrichment pipeline (monitor at /admin/enrichment-monitor)
# Typical: 2-5 minutes for 100+ products

# 4. Validate search
python scripts/demo/validate_search.py
```

### Live Demo Flow

| Step | Action | Show | Duration |
|---|---|---|---|
| 1 | Open `/admin/enrichment-monitor` | Pipeline status, active jobs | 30s |
| 2 | Upload new CSV via admin UI | CSV upload panel, progress indicator | 60s |
| 3 | Watch live processing logs | Entity processing, gap detection, confidence scores | 2-3 min |
| 4 | Open `/staff/review` | HITL review queue for low-confidence attributes | 60s |
| 5 | Approve/reject an attribute | Status transition, audit trail | 30s |
| 6 | Open search (ChatWidget) | Type demo query 1 (Russia travel) | 30s |
| 7 | Show streaming response | Progressive token rendering, intent panel | 30s |
| 8 | Run remaining demo queries | Side-by-side comparison, relevance scoring | 2 min |
| 9 | Show trace/eval panel | Response latency, search mode, source indicator | 30s |

### Recovery Procedures

| Issue | Recovery |
|---|---|
| Enrichment stuck | Check Event Hub consumer group offset; restart truth-enrichment pod |
| AI Search empty | Set `AI_SEARCH_PUSH_IMMEDIATE=true`; re-run upload script |
| Search > 5s | Check AI Search tier/RU; verify vector index has documents |
| Streaming broken | Verify `FOUNDRY_STREAM=true`; check catalog-search SSE endpoint |
| Upload fails | Verify blob storage RBAC (Storage Blob Data Contributor); check `BLOB_ACCOUNT_URL` |

## Quality Gate Checklist

- [ ] CSV export produces valid file with 100+ products across 11 categories
- [ ] Blob upload succeeds for all products with `raw_data` container
- [ ] Event Hub `enrichment-jobs` events are consumed by truth-enrichment agent
- [ ] Enrichment produces proposed attributes with confidence scores
- [ ] `search-enrichment-jobs` events bridge truth-enrichment to search-enrichment
- [ ] AI Search index contains enriched products with vector embeddings
- [ ] All 4 demo queries return relevant results in < 5 seconds
- [ ] Frontend streams search responses progressively
- [ ] CSV upload interface works from admin UI
- [ ] Live processing logs show real-time enrichment status
- [ ] Search results show latency, mode, intent, and source metadata
- [ ] Re-uploading a CSV triggers the full pipeline again
- [ ] Enrichment and search are independent (search works during enrichment)
- [ ] All Python code follows PEP 8, passes pylint ≥ 8.5
- [ ] All TypeScript code follows ESLint 7 configuration
- [ ] Unit and integration tests cover new scripts and components
