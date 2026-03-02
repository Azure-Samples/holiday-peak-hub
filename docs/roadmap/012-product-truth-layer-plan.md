# Product Truth Layer — Implementation Plan

**Date**: 2026-03-02
**Status**: Proposed
**Spec**: Agent-Ready Product Truth Layer (Catalog Enrichment + Knowledge Graph)
**Parent issue**: [010 - PIM/DAM Feature Request](010-pim-dam-feature-request.md)
**Epic issue**: [#87](https://github.com/Azure-Samples/holiday-peak-hub/issues/87)

---

## GitHub Issue Tracker

| Phase | Issue | Title |
|-------|-------|-------|
| Epic | #87 | Product Truth Layer Epic |
| 1 | #88 | Cosmos DB containers |
| 1 | #89 | Event Hub topics |
| 1 | #90 | Product Graph data models |
| 1 | #91 | Truth Store Cosmos adapter |
| 1 | #92 | Tenant Configuration model |
| 1 | #93 | UCP schema + category schemas |
| 1 | #94 | Event Hub helpers |
| 1 | #95 | TruthLayerSettings |
| 2 | #96 | Generic REST PIM connector |
| 2 | #97 | Generic DAM connector |
| 2 | #98 | Truth Ingestion service |
| 2 | #99 | Completeness Engine refactor |
| 2 | #100 | Sample data and seed scripts |
| 3 | #101 | Truth Enrichment service |
| 3 | #102 | Truth HITL service |
| 3 | #103 | HITL Staff Review UI |
| 4 | #104 | Truth Export service + Protocol Mappers |
| 4 | #105 | CRUD truth-layer routes |
| 4 | #106 | Postman collection + API docs |
| 5 | #107 | PIM writeback module |
| 5 | #108 | Evidence extraction |
| 5 | #109 | Admin UI pages |
| 5 | #110 | Enterprise hardening |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current State Assessment](#2-current-state-assessment)
3. [Gap Analysis](#3-gap-analysis)
4. [Changes to Existing Code](#4-changes-to-existing-code)
5. [New Features Plan](#5-new-features-plan)
6. [Implementation Phases](#6-implementation-phases)
7. [File-Level Work Breakdown](#7-file-level-work-breakdown)
8. [IaC Changes](#8-iac-changes)
9. [Open PR Impact](#9-open-pr-impact)

---

## 1. Executive Summary

The spec defines a **deployable reference implementation** for retailers to ingest product data, build a canonical Product Graph, run deterministic completeness checks, enrich via AI, support human-in-the-loop approvals, and publish governed UCP/ACP exports. This plan maps every spec requirement against the existing Holiday Peak Hub codebase and identifies what to **create**, **modify**, and **remove/replace**.

### Key Numbers

| Category | Count |
|----------|-------|
| New services to create | 5 (ingestion, completeness, enrichment-truth, hitl, export) |
| New lib modules to create | 8 |
| Existing services to modify | 4 |
| New IaC modules | 2 (Cosmos containers, Event Hub topics) |
| IaC modules to modify | 3 (Cosmos DB, Event Hubs, APIM) |
| New schema files | ~15 |
| New sample files | ~8 |
| New docs | 5 |

---

## 2. Current State Assessment

### 2.1 What Exists and Aligns

| Spec Requirement | Existing Asset | Alignment |
|------------------|---------------|-----------|
| Product storage | PostgreSQL via CRUD service + Cosmos DB provisioned (empty) | **Partial** — CRUD uses PostgreSQL; Cosmos DB account/database exist but no product graph containers |
| ACP export | `/acp/products`, `/acp/products/{id}` in CRUD + `AcpCatalogMapper` + `AcpProduct` schema + ACP Transformation agent | **Good** — ACP feed works end-to-end, needs policy filtering |
| Agent framework | `BaseRetailAgent`, `AgentBuilder`, 3-tier memory, `FastAPIMCPServer`, SLM/LLM routing | **Strong** — Fully reusable for new services |
| Connector contracts | `PIMConnectorBase`, `DAMConnectorBase` + 7 other ABCs in `integrations/contracts.py` | **Good** — Need concrete implementations |
| Connector registry | `ConnectorRegistry` in `integrations/registry.py` | **Good** — Runtime registry with health monitoring |
| App factory | `build_service_app()` in `app_factory.py` | **Strong** — Standard service bootstrap |
| Consistency validation | `product-management-consistency-validation` agent | **Weak** — Only checks 4 fields (name, price sign, currency, image); no completeness scoring |
| Product enrichment | `ecommerce-product-detail-enrichment` agent | **Wrong target** — Enriches PDP display, not PIM attributes |
| Product schemas | `CatalogProduct`, `ProductContext` in `schemas/product.py` | **Partial** — Missing style/variant split, provenance, share policy |
| IaC | Full Bicep stack: AKS, ACR, Cosmos DB, Event Hubs, Redis, Storage, APIM, Key Vault, App Insights, VNet, AI Foundry | **Strong** — All infra provisioned; Cosmos containers empty, Service Bus absent |
| Observability | App Insights + Log Analytics provisioned; structured logging in agents | **Good** — Need dashboards and audit-specific queries |
| Security | Managed Identity, RBAC assignments (AKS→services), Entra ID auth, Key Vault | **Good** — Aligned with spec defaults |
| Configuration | Pydantic BaseSettings + `.env`; `MemorySettings`, `ServiceSettings`, `PostgresSettings` | **Partial** — No tenant-config.json or persistent config store |

### 2.2 Open PRs State

**Active PR** (`issue/30-ci-agent-tests-no-swallow`, PR #86): 18 commits ahead of main. Contains:
- CI fix: agent tests no longer swallowed
- UI homepage slider + chat widget
- Entra auth hardening (anonymous browsing, fallback product listing)
- Next.js proxy for API routes
- PostgreSQL Entra auth rollout

**Impact**: This PR should be **merged first**. The plan below is designed to layer on top of the merged state. No conflicts expected with the Truth Layer work since PR #86 focuses on auth/UI/CI fixes, not data layer.

**Other branches** (stale): `feat/ai-agent-shopper`, `feat/documentation`, `feat/frontend`, `feat/unit-tests` — all merged or superseded by main.

### 2.3 Main Branch State

Latest on `origin/main`: commit `74d56c6` — "Fix APIM routing, postdeploy hooks, cloud UI loading, and agent enrichment (#85)".

---

## 3. Gap Analysis

### 3.1 Critical Gaps (Must-have for v0)

| # | Spec Section | Gap | Severity |
|---|-------------|-----|----------|
| G1 | §3.1 Core Data Plane | No Cosmos DB containers for product graph, candidates, schemas, audit. Cosmos container array is `[]` in Bicep. | **CRITICAL** |
| G2 | §7 Data Model | No `ProductStyle`, `ProductVariant`, `TruthAttribute`, `ProposedAttribute` models. Only flat `CatalogProduct`. | **CRITICAL** |
| G3 | §3.1 Ingestion | No ingestion service. PIM/DAM connector ABCs exist but no concrete connectors or scheduled pull. | **CRITICAL** |
| G4 | §3.1 Completeness Engine | No completeness scoring. Existing validation checks 4 fields. No category schema definitions. | **CRITICAL** |
| G5 | §3.1 Enrichment Orchestrator | No PIM enrichment agent. Existing enrichment targets e-commerce PDP, not product graph. | **CRITICAL** |
| G6 | §3.1 HITL Workflow | Zero implementation. No approval endpoints, no review queue, no UI. | **CRITICAL** |
| G7 | §8 Category Schemas | No `/schemas/` directory. No category-level required attributes or validation rules. | **CRITICAL** |
| G8 | §12 Export (UCP) | No UCP export. ACP export exists but lacks policy filtering and partner profiles. | **HIGH** |
| G9 | §6 Configuration Model | No tenant-config.json, no persistent config store, no connector settings management. | **HIGH** |
| G10 | §4 Job Topics | Event Hubs exist (5 topics) but need additional topics for truth-layer job queues (ingest, gap, enrichment, writeback, export). | **HIGH** |

### 3.2 Moderate Gaps

| # | Spec Section | Gap | Severity |
|---|-------------|-----|----------|
| G11 | §5 Repo Blueprint | No `/samples/` directory (data, connectors, Postman) | **MEDIUM** |
| G12 | §7.2 Audit | CRUD has `audit_logs` in PostgreSQL but no Cosmos audit container for propose→approve→export trail | **MEDIUM** |
| G13 | §14 Acceptance Tests | No end-to-end tests for the truth layer pipeline | **MEDIUM** |
| G14 | §2.1B One-command Deploy | `azd provision` + `azd deploy` works, but no single-command for the truth layer subset | **LOW** |
| G15 | §13 VNet Toggle | VNet already provisioned; needs enterprise-hardening parameter toggle | **LOW** |
| G16 | §12.3 Mapping | No `canonical_to_ucp` or `canonical_to_acp` mapping definitions | **MEDIUM** |

---

## 4. Changes to Existing Code

### 4.1 `lib/src/holiday_peak_lib/schemas/product.py` — EXTEND

**Current**: Flat `CatalogProduct` (sku, name, price, attributes dict).
**Required**: Add spec §7.2 entities while keeping `CatalogProduct` for backward compatibility.

New models to add:
```
ProductStyle       — id, brand, modelName, categoryId, variantIds[], assetIds[], sourceRefs[], updatedAt
ProductVariant     — id, styleId, upc, size, width, color, assetIds[], updatedAt
TruthAttribute     — entityType, entityId, attributeKey, value, unit, source, sharePolicy, provenance, status="official"
ProposedAttribute  — extends TruthAttribute + status(proposed|approved|rejected), confidence, modelRunId, evidenceRefs[], validationErrors[]
GapReport          — entityId, missingKeys[], invalidKeys[], completenessScore, target
```

`CatalogProduct` stays as-is (used by existing CRUD + ACP export). A new `to_catalog_product()` method on `ProductStyle` enables backward-compatible conversion.

### 4.2 `lib/src/holiday_peak_lib/schemas/acp.py` — EXTEND

**Add**: Partner profile policy fields, version field, `share_policy` awareness.
**Add**: `UcpProduct` model (parallel to `AcpProduct`) for UCP export.

### 4.3 `lib/src/holiday_peak_lib/adapters/acp_mapper.py` — EXTEND

**Add**: `UcpCatalogMapper` class.
**Modify**: `AcpCatalogMapper.to_acp_product()` to accept `partner_profile` parameter for policy-filtered output.
**Add**: Generic `ProtocolMapper` base class that `AcpCatalogMapper` and `UcpCatalogMapper` inherit from.

### 4.4 `lib/src/holiday_peak_lib/integrations/contracts.py` — EXTEND

**Add**: `PIMWritebackConnectorBase` ABC (update_product, update_attributes methods).
**Add**: `SchemaStoreBase` ABC (get_category_schema, list_schemas, validate_against_schema).
**Ensure**: `PIMConnectorBase` and `DAMConnectorBase` method signatures match spec's connector framework needs.

### 4.5 `lib/src/holiday_peak_lib/config/settings.py` — EXTEND

**Add**: `TruthLayerSettings` (Cosmos containers for graph, Service Bus connection, schema store path, auto-approve thresholds, export config).
**Add**: `ConnectorSettings` (PIM base URL, auth method, DAM settings).

### 4.6 `lib/src/holiday_peak_lib/app_factory.py` — MINOR MODIFY

**Add**: Optional parameter to register truth-layer specific middleware (audit logging, provenance tracking).
**Add**: Truth-layer Event Hub consumer groups and lifespan helpers for job topics.

### 4.7 `apps/product-management-consistency-validation/` — MAJOR REFACTOR

**Current**: Checks 4 fields (name, price, currency, image).
**Target**: Becomes the **Completeness Engine** (§3.1.3, §8). Must:
- Load category schemas from Cosmos `schemas` container
- Compute `missing = required - truthAttributesPresent`
- Compute `invalid = truthAttributesFailValidation`
- Generate `GapReport` with `completenessScore`
- Publish enrichment job events to Event Hub

Keep existing MCP tools and add new ones:
- `/product/completeness/check` — full gap analysis
- `/product/completeness/score` — score-only endpoint
- `/product/completeness/batch` — batch job trigger

### 4.8 `apps/product-management-acp-transformation/` — EXTEND

**Add**: Support for truth-store sourced products (read from `attributes_truth` Cosmos container, not just PostgreSQL).
**Add**: Partner profile policy filtering.
**Add**: UCP transformation alongside ACP.

### 4.9 `apps/crud-service/src/crud_service/routes/acp_products.py` — EXTEND

**Add**: UCP product endpoints (`/ucp/{version}/products`, `/ucp/{version}/products/{id}`).
**Add**: Policy filtering via partner profile config.
**Add**: `include_proposed` query parameter (default false, for internal sandbox only).

### 4.10 CRUD Service — ADD ROUTES

New route modules:
- `truth_attributes.py` — CRUD for official attributes (GET, POST approval, PUT edit)
- `proposed_attributes.py` — CRUD for candidate attributes (GET list, POST approve/reject)
- `schemas_registry.py` — Category schema management (GET, PUT)
- `completeness.py` — GET completeness scores, trigger batch jobs
- `audit_trail.py` — GET audit events with filtering

### 4.11 `.infra/modules/shared-infrastructure/shared-infrastructure.bicep` — MODIFY

**Change**: Populate `cosmosContainers` array with required containers:
```
products, attributes_truth, attributes_proposed, assets, evidence, schemas, mappings, audit
```

**Add**: Event Hub topics for truth-layer jobs (ingest-jobs, gap-jobs, enrichment-jobs, writeback-jobs, export-jobs) to existing Event Hub namespace.
**Add**: Parameterized toggle for optional modules (VNet hardening, writeback, evidence extraction).

---

## 5. New Features Plan

### 5.1 New Services (under `apps/`)

#### S1: `services/ingestion/` (new app: `truth-ingestion`)

**Spec**: §3.1.2 — Pull from PIM/DAM on schedule.

| Component | Details |
|-----------|---------|
| **Service type** | FastAPI app via `build_service_app()` |
| **Agent** | `IngestionAgent` extending `BaseRetailAgent` |
| **Adapters** | Uses `PIMConnectorBase` + `DAMConnectorBase` via `ConnectorRegistry` |
| **Trigger** | Event Hub `ingest-jobs` topic with consumer group (schedule-triggered or webhook-triggered) |
| **Logic** | 1) Pull products from PIM connector, 2) Pull assets from DAM connector, 3) Upsert into Cosmos `products` container as `ProductStyle`/`ProductVariant`, 4) Store raw payloads in Blob Storage, 5) Publish `gap-jobs` events for each ingested product |
| **Idempotency** | Upsert by `sourceRefs[]`; de-duplicate on re-run |
| **MCP tools** | `/ingest/trigger`, `/ingest/status`, `/ingest/product/{id}` |
| **Config** | PIM/DAM connector selection via `tenant-config.json` |

#### S2: `services/completeness/` (refactored from `product-management-consistency-validation`)

See §4.7 above. The existing service is refactored into the Completeness Engine.

#### S3: `services/enrichment/` (new app: `truth-enrichment`)

**Spec**: §3.1.4, §9 — Calls Azure OpenAI with strict JSON output.

| Component | Details |
|-----------|---------|
| **Service type** | FastAPI app via `build_service_app()` |
| **Agent** | `TruthEnrichmentAgent` extending `BaseRetailAgent` |
| **Trigger** | Event Hub `enrichment-jobs` topic with consumer group |
| **Input** | `GapReport` (entityId, missingKeys, existing attributes, asset URLs) |
| **LLM call** | Azure OpenAI (or Foundry endpoint) with: product context, missing attribute keys + expected types/enums, asset links, strict JSON output schema |
| **Output** | List of `ProposedAttribute` objects written to Cosmos `attributes_proposed` |
| **Validation** | JSON response validated against category schema types/enums before save |
| **Safety** | NEVER writes to `attributes_truth`. Only proposes. |
| **MCP tools** | `/enrich/trigger`, `/enrich/status/{jobId}`, `/enrich/proposals/{entityId}` |

#### S4: `services/hitl/` (new app: `truth-hitl`)

**Spec**: §3.1.5, §10 — Review + approve workflow.

| Component | Details |
|-----------|---------|
| **Service type** | FastAPI app via `build_service_app()` |
| **Endpoints** | `/review/queue` (GET — browse by category/score/status), `/review/{entityId}` (GET — proposed + truth side-by-side), `/review/{entityId}/approve` (POST), `/review/{entityId}/reject` (POST), `/review/{entityId}/edit` (PUT + approve), `/review/{entityId}/policy` (PUT — set share policy) |
| **Logic** | On approve: copy `ProposedAttribute` → `TruthAttribute` in Cosmos, record in `audit` container, optionally publish `writeback-jobs` event |
| **Auto-approve** | If `confidence >= threshold` (configurable, default 0.95), auto-approve with audit log |
| **Escalation** | Items unresolved after configurable timeout escalate to category managers |
| **MCP tools** | `/hitl/pending`, `/hitl/approve`, `/hitl/reject` |

#### S5: `services/export/` (new app: `truth-export`)

**Spec**: §3.1.6, §12 — Versioned UCP/ACP output, policy-filtered.

| Component | Details |
|-----------|---------|
| **Service type** | FastAPI app via `build_service_app()` |
| **Endpoints** | `GET /v1/products/{id}` (internal canonical), `GET /ucp/{version}/products/{id}`, `GET /acp/{version}/products/{id}`, `POST /exports/batch`, `GET /completeness/{id}` |
| **Logic** | 1) Read from `attributes_truth` only (unless `include_proposed=true` for sandbox), 2) Load mapping from Cosmos `mappings` container, 3) Apply partner profile policy, 4) Transform via `ProtocolMapper` subclass |
| **Partner profiles** | Config-driven: partner A gets fields X/Y, partner B gets X only |
| **Versioning** | Protocol version in URL path (`/ucp/v1/`, `/acp/v1/`) |
| **MCP tools** | `/export/canonical/{id}`, `/export/ucp/{id}`, `/export/acp/{id}` |

### 5.2 New Lib Modules

#### L1: `lib/src/holiday_peak_lib/schemas/truth.py`

All spec §7.2 entity models:
- `ProductStyle`, `ProductVariant`, `TruthAttribute`, `ProposedAttribute`, `GapReport`, `AuditEvent`
- Pydantic models with JSON Schema export for Cosmos validation

#### L2: `lib/src/holiday_peak_lib/schemas/ucp.py`

UCP protocol schema (parallel to `acp.py`):
- `UcpProduct` model with UCP-specific fields

#### L3: `lib/src/holiday_peak_lib/adapters/protocol_mapper.py`

- `ProtocolMapper` ABC with `map(style, truth_attrs, mapping_def) → dict`
- `UcpMapper(ProtocolMapper)` — canonical → UCP
- Refactor `AcpCatalogMapper` to extend `ProtocolMapper`

#### L4: `lib/src/holiday_peak_lib/adapters/truth_store.py`

Cosmos DB adapter for the product graph:
- `TruthStoreAdapter` — CRUD operations on `products`, `attributes_truth`, `attributes_proposed`, `schemas`, `mappings`, `audit` containers
- Partition key strategies per container
- Idempotent upserts

#### L5: `lib/src/holiday_peak_lib/integrations/pim_generic_rest.py`

Sample "Generic REST PIM" connector implementing `PIMConnectorBase`:
- Configurable base_url, auth (API key / OAuth), endpoints
- `get_product()`, `list_products()`, `search_products()`, `get_categories()`

#### L6: `lib/src/holiday_peak_lib/integrations/dam_generic.py`

Sample "Generic DAM" connector implementing `DAMConnectorBase`:
- Configurable base_url, auth, transformed URL patterns
- `get_asset()`, `get_assets_by_product()`, `search_assets()`

#### L7: `lib/src/holiday_peak_lib/utils/truth_event_hub.py`

Truth-layer Event Hub helpers (extending existing `event_hub.py`):
- `TruthJobPublisher` — publish job events to truth-layer topics
- `TruthJobConsumer` — consume job events with consumer groups and backoff/retry
- `truth_event_hub_lifespan()` — FastAPI lifespan helper for truth-layer topics

#### L8: `lib/src/holiday_peak_lib/config/tenant_config.py`

Tenant configuration model (§6):
- `TenantConfig` Pydantic model with sections: PIM connector, DAM connector, schema selection, policies, thresholds, partner profiles
- Loader from Cosmos config container or Blob `config/tenant-config.json`

### 5.3 New Schema Files (top-level `/schemas/`)

```
/schemas/
  /canonical/
    attribute_dictionary.v1.json       — Master attribute definitions (key, type, unit, enum values)
  /categories/
    running_shoes.v1.json              — Required attrs for running shoes (§8.1 example)
    casual_shoes.v1.json               — Additional sample category
  /protocols/
    ucp.v1.json                        — UCP protocol field definitions
    acp.v1.json                        — ACP protocol field definitions
  /mappings/
    canonical_to_ucp.v1.json           — Canonical → UCP field paths + transforms
    canonical_to_acp.v1.json           — Canonical → ACP field paths + transforms
```

### 5.4 New Sample Files (top-level `/samples/`)

```
/samples/
  /connectors/
    generic_rest_pim/
      README.md                         — Usage instructions
      config.example.json               — Sample PIM config
    generic_dam/
      README.md
      config.example.json
  /data/
    running_shoes_catalog.json          — 20 sample running shoe products with variants
    running_shoes_assets.json           — Paired asset metadata
  postman_collection.json               — Full API collection for truth layer endpoints
```

### 5.5 New Documentation

```
/docs/
  deployment.md                         — Updated for truth layer modules
  configuration.md                      — Tenant config, connector setup, schema management
  operations.md                         — Operational runbook: monitoring, re-running jobs, troubleshooting
  extending_connectors.md               — How to implement custom PIM/DAM connectors
  extending_schemas.md                  — How to add new category schemas and protocol overlays
```

### 5.6 HITL UI (in `apps/ui/`)

New pages:

| Route | Component | Function |
|-------|-----------|----------|
| `/staff/review` | ReviewDashboard | Browse products by category / completeness / needs-review |
| `/staff/review/[entityId]` | ReviewDetail | Side-by-side proposed vs truth, confidence scores, evidence |
| `/admin/schemas` | SchemaManager | View/edit category schemas and protocol definitions |
| `/admin/connectors` | ConnectorConfig | Configure PIM/DAM connector settings |

Review actions:
- Approve (single attribute or batch)
- Reject (with reason)
- Edit then approve
- Set share policy (internal / allowed partners / public)

---

## 6. Implementation Phases

### Phase 1: Core Data Plane + Schemas (2 weeks)

**Goal**: Cosmos containers populated, data models defined, schema store working.

| Task | Type | Effort |
|------|------|--------|
| Add Cosmos containers to Bicep (`cosmosContainers` array) | IaC modify | 0.5d |
| Add 5 Event Hub topics for truth-layer jobs to Bicep | IaC modify | 0.5d |
| Create `schemas/truth.py` (ProductStyle, ProductVariant, TruthAttribute, ProposedAttribute, GapReport, AuditEvent) | Lib add | 1d |
| Create `schemas/ucp.py` (UcpProduct) | Lib add | 0.5d |
| Create `adapters/truth_store.py` (Cosmos adapter for graph containers) | Lib add | 2d |
| Create `config/tenant_config.py` (TenantConfig model + loader) | Lib add | 1d |
| Create `/schemas/` directory with attribute dictionary + running_shoes.v1 + protocols + mappings | Schema files | 1.5d |
| Create `utils/truth_event_hub.py` (job publisher, consumer, lifespan) | Lib add | 1d |
| Extend `config/settings.py` with `TruthLayerSettings` | Lib modify | 0.5d |
| Unit tests for all new models + adapters | Tests | 1.5d |

**Milestone**: `azd provision` creates Cosmos containers + Event Hub topics. Models importable. Schema files loadable.

### Phase 2: Ingestion + Completeness (2 weeks)

**Goal**: Products ingested from sample connectors, completeness scores generated.

| Task | Type | Effort |
|------|------|--------|
| Create `integrations/pim_generic_rest.py` (Generic REST PIM connector) | Lib add | 1.5d |
| Create `integrations/dam_generic.py` (Generic DAM connector) | Lib add | 1d |
| Create `truth-ingestion` service (FastAPI + agent + adapters) | App add | 2d |
| Refactor `product-management-consistency-validation` into Completeness Engine | App refactor | 2d |
| Create `/samples/data/` with running shoes catalog + assets | Samples add | 0.5d |
| Wire Event Hub job flow: ingest → gap → enrich | Integration | 1d |
| Add ingestion + completeness routes to CRUD service | CRUD modify | 1d |
| Integration tests: ingest sample data → verify completeness scores | Tests | 1.5d |

**Milestone**: `POST /ingest/trigger` pulls sample data → products appear in Cosmos → `GET /completeness/{id}` returns gap report.

### Phase 3: Enrichment + HITL (2 weeks)

**Goal**: AI-proposed attributes, human review workflow.

| Task | Type | Effort |
|------|------|--------|
| Create `truth-enrichment` service (FastAPI + agent + LLM pipeline) | App add | 2.5d |
| Create `truth-hitl` service (FastAPI + approval endpoints) | App add | 2d |
| Implement auto-approve logic (confidence ≥ threshold) | Service logic | 0.5d |
| Create HITL UI pages (`/staff/review`, `/staff/review/[entityId]`) | Frontend add | 2d |
| Wire Event Hub flow: enrichment → hitl → truth | Integration | 1d |
| Audit trail: write to Cosmos `audit` container on every state change | Lib modify | 0.5d |
| End-to-end test: gap → enrich → propose → approve → truth | Tests | 1.5d |

**Milestone**: Products with missing attributes get AI proposals → staff reviews in UI → approved values in truth store.

### Phase 4: Export + Policy + Hardening (1.5 weeks)

**Goal**: UCP/ACP exports with partner policies, observability, samples.

| Task | Type | Effort |
|------|------|--------|
| Create `truth-export` service (or extend CRUD routes) | App add/modify | 1.5d |
| Create `adapters/protocol_mapper.py` (ProtocolMapper, UcpMapper) | Lib add | 1d |
| Refactor `AcpCatalogMapper` to extend `ProtocolMapper` | Lib modify | 0.5d |
| Add partner profile policy filtering | Service logic | 1d |
| Add UCP export endpoints to CRUD (`/ucp/v1/products/`) | CRUD modify | 0.5d |
| Extend ACP export with policy filtering | CRUD modify | 0.5d |
| Create Postman collection | Samples add | 0.5d |
| Create `/docs/` (deployment, configuration, operations, extending_*) | Docs | 1d |
| Add App Insights dashboards + audit KQL queries | Observability | 0.5d |
| Acceptance tests (§14 functional criteria 1–8) | Tests | 1.5d |

**Milestone**: Full pipeline works. `GET /ucp/v1/products/{id}` returns governed, versioned, policy-filtered output.

### Phase 5: Optional Modules + Polish (1 week, stretch)

| Task | Type | Effort |
|------|------|--------|
| PIM writeback module (optional toggle) | App add | 1.5d |
| Evidence extraction from PDFs (Document Intelligence, optional toggle) | App add | 1.5d |
| Admin UI pages (schema manager, connector config) | Frontend add | 1d |
| Enterprise hardening toggle (private endpoints disable public access) | IaC modify | 0.5d |
| CI/CD pipeline for truth-layer services | CI/CD add | 0.5d |

---

## 7. File-Level Work Breakdown

### 7.1 New Files

```
# Lib — Schemas
lib/src/holiday_peak_lib/schemas/truth.py
lib/src/holiday_peak_lib/schemas/ucp.py

# Lib — Adapters
lib/src/holiday_peak_lib/adapters/truth_store.py
lib/src/holiday_peak_lib/adapters/protocol_mapper.py

# Lib — Integrations (sample connectors)
lib/src/holiday_peak_lib/integrations/pim_generic_rest.py
lib/src/holiday_peak_lib/integrations/dam_generic.py

# Lib — Utils
lib/src/holiday_peak_lib/utils/truth_event_hub.py

# Lib — Config
lib/src/holiday_peak_lib/config/tenant_config.py

# Service — Ingestion
apps/truth-ingestion/src/truth_ingestion/__init__.py
apps/truth-ingestion/src/truth_ingestion/main.py
apps/truth-ingestion/src/truth_ingestion/agents.py
apps/truth-ingestion/src/truth_ingestion/adapters.py
apps/truth-ingestion/src/truth_ingestion/event_handlers.py
apps/truth-ingestion/pyproject.toml
apps/truth-ingestion/Dockerfile
apps/truth-ingestion/tests/

# Service — Enrichment
apps/truth-enrichment/src/truth_enrichment/__init__.py
apps/truth-enrichment/src/truth_enrichment/main.py
apps/truth-enrichment/src/truth_enrichment/agents.py
apps/truth-enrichment/src/truth_enrichment/adapters.py
apps/truth-enrichment/src/truth_enrichment/event_handlers.py
apps/truth-enrichment/pyproject.toml
apps/truth-enrichment/Dockerfile
apps/truth-enrichment/tests/

# Service — HITL
apps/truth-hitl/src/truth_hitl/__init__.py
apps/truth-hitl/src/truth_hitl/main.py
apps/truth-hitl/src/truth_hitl/agents.py
apps/truth-hitl/src/truth_hitl/adapters.py
apps/truth-hitl/src/truth_hitl/routes.py
apps/truth-hitl/pyproject.toml
apps/truth-hitl/Dockerfile
apps/truth-hitl/tests/

# Service — Export
apps/truth-export/src/truth_export/__init__.py
apps/truth-export/src/truth_export/main.py
apps/truth-export/src/truth_export/agents.py
apps/truth-export/src/truth_export/adapters.py
apps/truth-export/src/truth_export/routes.py
apps/truth-export/pyproject.toml
apps/truth-export/Dockerfile
apps/truth-export/tests/

# CRUD Service — New routes
apps/crud-service/src/crud_service/routes/truth_attributes.py
apps/crud-service/src/crud_service/routes/proposed_attributes.py
apps/crud-service/src/crud_service/routes/schemas_registry.py
apps/crud-service/src/crud_service/routes/completeness.py
apps/crud-service/src/crud_service/routes/audit_trail.py
apps/crud-service/src/crud_service/routes/ucp_products.py

# Top-level schemas
schemas/canonical/attribute_dictionary.v1.json
schemas/categories/running_shoes.v1.json
schemas/categories/casual_shoes.v1.json
schemas/protocols/ucp.v1.json
schemas/protocols/acp.v1.json
schemas/mappings/canonical_to_ucp.v1.json
schemas/mappings/canonical_to_acp.v1.json

# Samples
samples/connectors/generic_rest_pim/README.md
samples/connectors/generic_rest_pim/config.example.json
samples/connectors/generic_dam/README.md
samples/connectors/generic_dam/config.example.json
samples/data/running_shoes_catalog.json
samples/data/running_shoes_assets.json
samples/postman_collection.json

# Docs
docs/deployment.md
docs/configuration.md
docs/operations.md
docs/extending_connectors.md
docs/extending_schemas.md

# Frontend — HITL pages
apps/ui/app/staff/review/page.tsx
apps/ui/app/staff/review/[entityId]/page.tsx
apps/ui/components/organisms/ReviewDashboard.tsx
apps/ui/components/organisms/ReviewDetail.tsx
apps/ui/components/molecules/AttributeCompare.tsx
apps/ui/components/molecules/ConfidenceBadge.tsx
apps/ui/lib/services/truthService.ts
apps/ui/lib/hooks/useTruth.ts

# IaC
# (Event Hub topics added inline to existing shared-infrastructure.bicep)

# Tests
lib/tests/test_truth_schemas.py
lib/tests/test_truth_store.py
lib/tests/test_protocol_mapper.py
lib/tests/test_tenant_config.py
lib/tests/test_truth_event_hub.py
lib/tests/test_pim_generic_rest.py
lib/tests/test_dam_generic.py
apps/truth-ingestion/tests/test_ingestion.py
apps/truth-enrichment/tests/test_enrichment.py
apps/truth-hitl/tests/test_hitl.py
apps/truth-export/tests/test_export.py
tests/e2e/test_truth_pipeline.py
```

### 7.2 Modified Files

```
# Lib
lib/src/holiday_peak_lib/schemas/product.py          — Add style/variant if needed for backward compat bridge
lib/src/holiday_peak_lib/schemas/acp.py               — Add partner policy + version fields
lib/src/holiday_peak_lib/schemas/__init__.py           — Export new schemas
lib/src/holiday_peak_lib/adapters/acp_mapper.py        — Refactor to extend ProtocolMapper
lib/src/holiday_peak_lib/adapters/__init__.py           — Export new adapters
lib/src/holiday_peak_lib/integrations/contracts.py      — Add PIMWritebackConnectorBase, SchemaStoreBase
lib/src/holiday_peak_lib/integrations/__init__.py       — Export new connectors
lib/src/holiday_peak_lib/config/settings.py             — Add TruthLayerSettings
lib/src/holiday_peak_lib/config/__init__.py             — Export new settings
lib/src/holiday_peak_lib/app_factory.py                 — Add Service Bus lifespan, audit middleware
lib/src/holiday_peak_lib/utils/__init__.py              — Export truth_event_hub utils

# CRUD Service
apps/crud-service/src/crud_service/main.py              — Register new truth-layer route modules
apps/crud-service/src/crud_service/routes/__init__.py   — Import new routes

# Consistency Validation → Completeness Engine
apps/product-management-consistency-validation/src/agents.py     — Major refactor: completeness scoring
apps/product-management-consistency-validation/src/adapters.py   — Add schema loading, gap report generation
apps/product-management-consistency-validation/src/main.py       — Wire Event Hub consumer for gap-jobs

# ACP Transformation
apps/product-management-acp-transformation/src/agents.py   — Add truth-store source option
apps/product-management-acp-transformation/src/adapters.py — Add partner policy handling

# IaC
.infra/modules/shared-infrastructure/shared-infrastructure.bicep — Add Cosmos containers + Service Bus
.infra/azd/main.bicep                                            — Add outputs for new Event Hub topics, new services
azure.yaml                                                        — Add truth-* service definitions

# CI/CD
.github/workflows/test.yml    — Add truth-* services to test matrix
.github/workflows/deploy-azd.yml — Add truth-* services to deploy matrix
```

---

## 8. IaC Changes

### 8.1 Cosmos DB Containers (modify `shared-infrastructure.bicep`)

Current: `var cosmosContainers = []`
New:
```bicep
var cosmosContainers = [
  { name: 'products',            partitionKeyPath: '/categoryId' }
  { name: 'attributes_truth',    partitionKeyPath: '/entityId' }
  { name: 'attributes_proposed', partitionKeyPath: '/entityId' }
  { name: 'assets',              partitionKeyPath: '/productId' }
  { name: 'evidence',            partitionKeyPath: '/entityId' }
  { name: 'schemas',             partitionKeyPath: '/categoryId' }
  { name: 'mappings',            partitionKeyPath: '/protocolVersion' }
  { name: 'audit',               partitionKeyPath: '/entityId' }
  { name: 'config',              partitionKeyPath: '/tenantId' }
]
```

### 8.2 Event Hub Topics (add to `shared-infrastructure.bicep`)

Add truth-layer job topics to the existing Event Hub namespace (alongside `order-events`, `inventory-events`, etc.):

```bicep
var truthLayerEventHubs = [
  'ingest-jobs'
  'gap-jobs'
  'enrichment-jobs'
  'writeback-jobs'
  'export-jobs'
]
```

Each topic gets dedicated consumer groups per service (e.g., `completeness-group` on `gap-jobs`, `enrichment-group` on `enrichment-jobs`).

### 8.3 RBAC (existing assignments sufficient)

- AKS identity → Event Hubs Data Sender + Receiver (already exists)
- AKS identity → Cosmos DB Data Contributor (already exists)

### 8.4 azure.yaml Additions

```yaml
  truth-ingestion:
    project: apps/truth-ingestion/src
    host: aks
    ...
  truth-enrichment:
    project: apps/truth-enrichment/src
    host: aks
    ...
  truth-hitl:
    project: apps/truth-hitl/src
    host: aks
    ...
  truth-export:
    project: apps/truth-export/src
    host: aks
    ...
```

### 8.5 Optional Module Toggles (IaC parameters)

```bicep
@description('Enable PIM writeback module')
param enableWriteback bool = false

@description('Enable evidence extraction (Document Intelligence)')
param enableEvidenceExtraction bool = false

@description('Disable public network access (enterprise hardening)')
param enablePrivateOnly bool = false
```

---

## 9. Open PR Impact

### PR #86 (`issue/30-ci-agent-tests-no-swallow`)

**Recommendation**: Merge before starting this work.

**Conflicts with this plan**: None. PR #86 modifies:
- CI test workflow (no overlap — we add new services to matrix)
- UI homepage (no overlap — we add new HITL pages)
- Entra auth (beneficial foundation — truth-layer services use same auth)
- CRUD auth hardening (beneficial — truth routes use same auth middleware)

### Other Branches

All other remote branches (`feat/ai-agent-shopper`, `feat/documentation`, `feat/frontend`, `feat/unit-tests`, `alert-autofix-*`, `copilot/fix-misspelled-word`) are stale and already merged or superseded. No action needed.

---

## Appendix A: Spec Section → Implementation Mapping

| Spec Section | Implementation |
|-------------|----------------|
| §2.1A Git repo structure | `/schemas/`, `/samples/`, `/docs/` directories created |
| §2.1B One-command deploy | `azd provision && azd deploy` with new services in azure.yaml |
| §2.1C Connector framework | `PIMConnectorBase` + `DAMConnectorBase` (exist) + `ConnectorRegistry` + 2 sample connectors |
| §2.1D HITL UI | `/staff/review` + `/staff/review/[entityId]` pages in apps/ui |
| §3.1.1 Core Data Plane | Cosmos containers: products, attributes_truth, attributes_proposed, schemas, assets, evidence, mappings, audit |
| §3.1.2 Ingestion | `truth-ingestion` service + Generic REST PIM connector + Generic DAM connector |
| §3.1.3 Completeness | Refactored `product-management-consistency-validation` with schema-driven gap detection |
| §3.1.4 Enrichment | `truth-enrichment` service with Azure OpenAI strict JSON output |
| §3.1.5 HITL | `truth-hitl` service + HITL UI pages |
| §3.1.6 Export | `truth-export` service + UCP/ACP versioned endpoints |
| §3.1.7 Observability | App Insights (exists) + audit Cosmos container + KQL dashboards |
| §4 Azure services | AKS (exists) + Cosmos DB (containers added) + Event Hubs (topics added) + APIM (exists) + Storage (exists) + Entra ID (exists) + Azure OpenAI/Foundry (exists) + App Insights (exists) |
| §6 Config model | `TenantConfig` in Cosmos `config` container or Blob `config/tenant-config.json` |
| §7 Data model | `ProductStyle`, `ProductVariant`, `TruthAttribute`, `ProposedAttribute` in `schemas/truth.py` |
| §8 Completeness | Category schemas in `/schemas/categories/`, `GapReport` model, deterministic scoring |
| §9 Enrichment agent | `TruthEnrichmentAgent` with strict JSON output, writes to `attributes_proposed` only |
| §10 HITL | `truth-hitl` endpoints + auto-approve + audit trail |
| §11 PIM writeback | Optional module: `writeback-jobs` Service Bus queue + connector `update_product()` |
| §12 Export | `truth-export` with UCP/ACP/canonical endpoints, partner policy filtering, protocol versioning |
| §13 Security | Managed Identity (exists) + RBAC (exists) + Key Vault (exists) + optional private endpoints toggle |
| §14 Acceptance tests | `tests/e2e/test_truth_pipeline.py` covering all 8 functional criteria |

## Appendix B: Compute Choice Note

The spec suggests **Azure Functions** as easiest for the accelerator, OR **Azure Container Apps** for consistent container deployment. The current repo uses **AKS** with Helm. This plan continues with AKS for consistency with the existing 22 services. To align with the spec's simpler compute option, a future iteration could add a `deployTarget` IaC parameter (`aks` | `functions` | `containerapps`) — but this is a v1+ concern and out of v0 scope.

## Appendix C: Existing vs. Spec Terminology

| Spec Term | Existing Equivalent | Notes |
|-----------|-------------------|-------|
| Product Graph | None (PostgreSQL products table) | New Cosmos containers needed |
| attributes_truth | None | New container |
| attributes_proposed | None | New container |
| Category Schema | None | New `/schemas/categories/` |
| Protocol Overlay | `AcpProduct` schema | Extend to UCP; add versioning |
| Completeness Engine | `consistency-validation` agent | Major refactor needed |
| Enrichment Agent | `product-detail-enrichment` agent | Different purpose; new service needed |
| HITL | None | Fully new |
| Export API | `acp_products.py` routes | Extend with UCP + policy filtering |
| Connector Framework | `integrations/contracts.py` + `registry.py` | Need concrete implementations |
| Tenant Config | `config/settings.py` (env-only) | Need Cosmos/Blob persistent config |
