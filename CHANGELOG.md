# Changelog

All notable changes to the Holiday Peak Hub project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Issue #29: made `lib/tests/test_config.py` deterministic by isolating settings env-file loading in tests only (`_env_file=None`), preventing local `.env` values from affecting `MemorySettings`, `ServiceSettings`, `PostgresSettings`, and `TruthLayerSettings` test outcomes.

- Issue #246: stabilized `main` quality gates after dependency updates by restoring deterministic product-search fallback and enrichment URL guard behavior in CRUD (`apps/crud-service/src/crud_service/routes/products.py`, `apps/crud-service/src/crud_service/integrations/agent_client.py`), resolving regressions in `test_list_products_with_search` and `test_get_product_enrichment_no_agent_url`.

- Issue #248: completed branch/artifact hygiene for remediation flow by pruning temporary local branches and cleanup artifacts so local working clones retain only `main` for stabilization operations.


### Changed

- Dependabot remediation merged for security/tooling maintenance: PR #245 (`pyjwt` bump to `2.12.0`) and PR #222 (`black` bump to `26.3.1`) are now integrated on `main`, with lint/test checks revalidated after merge.

- Documentation updates for issue #32: business scenario, architecture, and status docs now reflect implemented Azure AI Search provisioning (`catalog-products` index), deploy-time env propagation (`AI_SEARCH_ENDPOINT`, `AI_SEARCH_INDEX`, `AI_SEARCH_AUTH_MODE`), and runtime query/index fallback behavior in `ecommerce-catalog-search`, with optional hardening (vector/hybrid tuning, relevance/load gates) tracked separately.

- Documentation updates for issue #28: business scenario, architecture, and roadmap docs now state that dashboard/profile supported paths use UI API hooks, and previously hardcoded values without backend contracts were removed in favor of explicit unavailable/unsupported UI states.

- Documentation updates for issue #30: architecture/governance/status/roadmap now explicitly reflect CI fail-fast behavior where required smoke/test gates do not swallow failures, transport errors are normalized and treated as hard failures in required checks, and advisory diagnostics are separated from blocking gates.

- Documentation updates for issue #33: status/roadmap/governance tracking now reflects implemented server-side route protection middleware in the UI (`apps/ui/middleware.ts`) for closure-readiness alignment.

- Documentation updates for issue #112: Entra ID setup guidance now includes deployed CRUD environment wiring (`ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`) and where to set values in deployed env/workflow/Key Vault references.

- Documentation updates for issue #217: business scenario and architecture docs now reflect the implemented returns/refund lifecycle with deterministic transitions (`requested -> approved|rejected -> received -> restocked -> refunded`), customer/staff API contracts (`/api/returns/*`, `/api/staff/returns/*`), and emitted events (`ReturnRequested|Approved|Rejected|Received|Restocked|Refunded`, `RefundIssued`).

- Documentation updates for issue #216: scenario 04 business and architecture docs now reflect the implemented inventory reservation lifecycle in checkout (`POST /api/inventory/reservations`, `GET /api/inventory/reservations/{id}`, `POST /api/inventory/reservations/{id}/confirm`, `POST /api/inventory/reservations/{id}/release`, `GET /api/inventory/health`) including enforced state transitions (`created -> confirmed|released`, terminal `confirmed/released`).

- Documentation updates for issue #215: business scenario and architecture docs now describe the implemented brand-shopping personalization contract chain (`GET /api/catalog/products/{sku}`, `GET /api/customers/{customer_id}/profile`, `POST /api/pricing/offers`, `POST /api/recommendations/rank`, `POST /api/recommendations/compose`) and the orchestration split (CRUD owns contracts, UI orchestrates execution flow).

- Documentation updates for issue #214: business scenario and architecture coverage now explicitly describe dual auth mode (Entra ID primary + non-production dev mock fail-safe), role-based demo enablement, and production safeguards for mock auth endpoints.

- Documentation updates for issue #210: business scenario and architecture docs now capture the real checkout orchestration (`/api/checkout/validate` → `/api/orders` → `/api/payments/intent` → Stripe confirmation → `/api/payments/confirm-intent`) and payment retrieval path (`GET /api/payments/{payment_id}`), replacing stubbed-flow assumptions.

### Added

- CRUD support ticket lifecycle APIs for staff/admin: `POST /api/staff/tickets`, `PATCH /api/staff/tickets/{id}`, `POST /api/staff/tickets/{id}/resolve`, and `POST /api/staff/tickets/{id}/escalate`, including audit/status history metadata for workflow traceability.

- `GET /api/payments/{payment_id}` now returns persisted payment details with ownership checks (customer can read own payment, staff/admin can read any), replacing prior `501` behavior.

- Inventory persistence and reservation APIs in CRUD service: `GET/PATCH /api/inventory/{sku}`, `PATCH /api/inventory/{sku}/thresholds`, `GET /api/inventory/health`, `POST /api/inventory/reservations`, `GET /api/inventory/reservations/{id}`, `POST /api/inventory/reservations/{id}/confirm`, and `POST /api/inventory/reservations/{id}/release`, with explicit transitions, idempotent confirm/release semantics, and persisted status/audit history.

## [2.0.0] - 2026-03-04

> **Release**: `v2.0.0`
> **Theme**: Single-path completeness operations (breaking compatibility removal)

### Changed

- Product consistency validation service now uses a **single canonical operation path**:
  - schema-driven completeness evaluation only
  - no legacy 4-field validator path
  - no legacy `product-events` compatibility subscription

### Removed

- Legacy compatibility components removed from `product-management-consistency-validation`:
  - legacy validator logic (`missing_name`, `negative_price`, `missing_currency`, `missing_image`)
  - legacy event processing module for `product-events`
  - legacy MCP tools:
    - `/product/consistency/check`
    - `/product/consistency/product`

### Added

- Canonical MCP operation for completeness:
  - `/product/completeness/evaluate`

### Migration Notes

- Any integration relying on the removed consistency MCP tools must switch to `/product/completeness/evaluate`.
- Event-driven completeness processing now requires publishing to `completeness-jobs` (consumer group `completeness-engine`).
- This release intentionally removes backward compatibility to guarantee a single operation model.

## [1.1.0] - 2026-03-03

> **Release**: [v1.1.0](https://github.com/Azure-Samples/holiday-peak-hub/releases/tag/v1.1.0)
> **Theme**: Enterprise Connectors, Product Truth Layer, HITL Review System

### Added

#### Product Truth Layer (Foundation)
- **Phase 1**: Pydantic v2 data models for product truth records [`377923a`]
  - `TruthAttribute`, `ProposedAttribute`, `GapReport`, `AuditEvent`
  - `ProductStyle`, `ProductVariant`, `Provenance` models
  - `AssetMetadata`, `CategorySchema` for hierarchy management
- **Phase 2**: Truth Ingestion service with Cosmos DB integration [`f311ea4`]
  - Event Hub job queue processing
  - Sample data and category schema seeding [`9bc28d2`]
  - Cosmos DB container population script [`7ebdf98`]

#### Enterprise System Connectors
- **Oracle Fusion Cloud SCM** connector [`252363d`]
  - Authentication: OAuth 2.0 with JWKS
  - Endpoints: Inventory, Purchase Orders, Shipments
  - Field mappings to canonical models
- **Salesforce CRM & Marketing Cloud** connector [`5d110fb`]
  - Authentication: OAuth 2.0 + refresh token
  - Endpoints: Contacts, Accounts, Leads, Campaigns
  - Bi-directional sync with CRM agents
- **SAP S/4HANA Inventory & SCM** connector [`f0e5dc1`]
  - OData v4 with SAP authentication
  - Material master, inventory positions, purchase orders
- **Dynamics 365 Customer Engagement** connector [`875a634`]
  - Dataverse Web API integration
  - Contact, Account, Opportunity, Case entities
- **Generic REST DAM** connector [`d027b0f`]
  - Configurable endpoint mapping
  - OAuth/API key authentication

#### Enterprise Hardening (PR #110) [`652490f`]
- **Circuit Breaker** (`lib/utils/circuit_breaker.py`)
  - Configurable failure threshold and recovery timeout
  - Half-open state with gradual recovery
  - Metrics integration for monitoring
- **Bulkhead Pattern** (`lib/utils/bulkhead.py`)
  - Semaphore-based resource isolation
  - Per-service concurrency limits
  - Queue overflow protection
- **Rate Limiter** (`lib/utils/rate_limiter.py`)
  - Token bucket algorithm
  - Configurable burst and replenishment
  - Async-first implementation
- **Telemetry Integration** (`lib/utils/telemetry.py`)
  - OpenTelemetry spans and metrics
  - Automatic trace propagation
  - Custom attribute injection
- **Health Probes** (enhanced `routes/health.py`)
  - Kubernetes liveness/readiness endpoints
  - Dependency health aggregation
  - Graceful degradation reporting

#### PIM Writeback Module (PR #107) [`d0f1126`]
- **Opt-in Configuration** (`TenantConfig`)
  - Per-tenant writeback enable/disable
  - Field-level allow lists
  - Dry-run mode for validation
- **Circuit Breaker Protection**
  - Automatic PIM API isolation on failures
  - Configurable reset timeout
- **Conflict Detection**
  - Version comparison before writes
  - Automatic conflict resolution strategies
- **Audit Trail**
  - All writeback operations logged
  - Failure reason capture
  - Timestamp and actor tracking

#### HITL Staff Review UI (PR #103) [`c83fbd7`]
- **Review Queue** (`/staff/review`)
  - Filterable table with pagination
  - Status badges (pending, approved, rejected)
  - Bulk action support
- **Entity Detail Review** (`/staff/review/[entityId]`)
  - Side-by-side current vs proposed view
  - Confidence scoring visualization
  - One-click approve/reject
- **UI Components** (`components/truth/`)
  - `ReviewQueueTable` - Sortable queue display
  - `ProposalCard` - Attribute comparison cards
  - `ConfidenceBadge` - AI confidence indicators
  - `CompletenessBar` - Data quality progress
  - `AuditTimeline` - Change history visualization
- **Hooks** (`lib/hooks/useTruth.ts`)
  - `useReviewQueue` - Queue data fetching
  - `useProductReview` - Entity detail loading
  - `useReviewActions` - Approve/reject mutations

#### Admin UI for Truth Layer [`2eebe63`]
- **Schema Management** (`/admin/schemas`)
  - Category hierarchy editor
  - Field definition CRUD
- **Tenant Configuration** (`/admin/config`)
  - Writeback settings per tenant
  - Connector toggle switches
- **Analytics Dashboard** (`/admin/analytics`)
  - Completeness metrics by category
  - Pipeline throughput charts
  - AI vs human contribution ratios

#### Frontend Enhancements
- **Stripe Checkout Integration** [`a17c5ba`]
  - Payment intent creation
  - Card element with validation
  - Success/failure handling
- **Live API Integration** [`c254785`]
  - Dashboard with real data hooks
  - Profile page API connection
  - Checkout flow completion
- **Server-Side Route Protection** [`7de1bfe`]
  - Next.js middleware for auth guards
  - Role-based page access control

#### Authentication & Documentation
- **Entra ID Configuration Guide** [`33bf896`]
  - Local development setup
  - Azure deployment configuration
  - Token validation troubleshooting

#### Demo Data & Seeding
- **Full Retail Catalog** [`07bbee9`]
  - Curated users, orders, shipments
  - Product reviews with ratings
  - Support tickets and returns history
- **Legacy Asset Cleanup** [`3601ba8`]
  - Removed Faker-generated data
  - Replaced with realistic retail scenarios

### Changed

- **Stripe SDK**: Fixed `stripe.Stripe` → `stripe.StripeClient` [`3ac9915`]
- **CI Pipeline**: Fail on app test failures (no silent swallowing) [`fc32dc3`, `6f5f291`]
- **Docker Build**: Guard loop against non-directory entries [`0cc8f16`]
- **Git Workflow**: ADR-022 for branch naming convention [`ba353c8`]

### Testing

- **508 tests passing** (↑343 from v1.0.0)
  - Lib unit tests: 287 tests
  - Connector tests: 96 tests (Oracle, Salesforce, SAP, Dynamics)
  - Enterprise hardening tests: 50 tests
  - PIM writeback tests: 25 tests
  - Integration tests: 50 tests
- **Coverage**: 73% lib statements
- **New Test Files**:
  - `test_circuit_breaker.py` - 15 tests
  - `test_bulkhead.py` - 12 tests
  - `test_rate_limiter.py` - 10 tests
  - `test_telemetry.py` - 8 tests
  - `test_pim_writeback.py` - 25 tests
  - `test_connectors/inventory_scm/oracle_scm/` - 48 tests
  - `test_connectors/crm_loyalty/salesforce/` - 48 tests

### Dependencies

**New Backend Dependencies**:
- `circuitbreaker>=2.0` - Circuit breaker pattern
- `tenacity>=8.2` - Retry with backoff
- `opentelemetry-api>=1.20` - Telemetry integration
- `stripe>=7.0` - Payment processing

**New Frontend Dependencies**:
- `@stripe/stripe-js@2.4` - Stripe Elements
- `@stripe/react-stripe-js@2.4` - React bindings

---

## [1.0.0] - 2026-02-27

> **Release**: [v1.0.0](https://github.com/Azure-Samples/holiday-peak-hub/releases/tag/v1.0.0)
> **Tag**: `7eaa28e` — First stable release of the Holiday Peak Hub framework.

### Added

- **CRUD Service** — 31 REST endpoints across 15 route modules (FastAPI + PostgreSQL/asyncpg) [`cbb6db9`]
- Complete frontend API integration layer: 6 TypeScript services, 5 React Query hooks [`ec219df`]
- Microsoft Entra ID authentication via MSAL (SSR-safe) [`ec219df`]
- Event publishing integration with Azure Event Hubs (5 topics) [`ec219df`]
- CRUD Service implementation documentation [`4f81fd0`]
- Infrastructure governance and compliance guidelines [`94ac73e`, `0058dbe`]
- Static Web App deployment workflow and SWA config [`5c0a999`, `b54b3d4`]
- Seed demo data script for PostgreSQL [`7eaa28e`]
- `staticwebapp.config.json` for SWA API routing [`b54b3d4`]

### Changed

#### Data Layer: Cosmos DB → PostgreSQL
- Migrated CRUD Service from Azure Cosmos DB to PostgreSQL (asyncpg) [`cbb6db9`]
  - `BaseRepository` uses shared `asyncpg.Pool` with configurable pool sizes
  - JSONB columns with GIN + B-tree indexes; auto-creates tables on first request
  - Removed `azure-cosmos` SDK dependency; added `asyncpg`
- New PostgreSQL settings: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DATABASE`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_SSL`, `POSTGRES_MIN_POOL`, `POSTGRES_MAX_POOL`

#### Agent Client: APIM-Routed Resilient Integration
- Rewrote `agent_client.py` with APIM gateway routing, circuit breaker, and retry [`7eaa28e`]
  - 12 domain-specific methods routed through Azure API Management
  - `circuitbreaker` (failure_threshold=5, recovery_timeout=60s) + `tenacity` retry (3 attempts, 1–10s)
  - `httpx.AsyncClient` with graceful degradation (returns `None` on circuit-open)

#### Authentication: JWKS-Based JWT Validation
- Rewrote `auth/dependencies.py` with JWKS key caching and kid-based matching [`7eaa28e`]
  - Fetches signing keys from Entra ID JWKS endpoint, caches for 1 hour
  - Replaced `msal`-based validation with direct `PyJWT` + JWKS

#### Frontend
- Replaced stubbed login/signup pages with Entra ID-only auth [`ec219df`]
- Updated Next.js to 16.2.0-canary.17; downgraded Tailwind CSS to 3.4.0 [`ec219df`]

#### CI/CD & Deployment
- `deploy-azd.yml` — 8-job pipeline: provision, deploy-foundry-models, deploy-crud, deploy-ui, deploy-agents, sync-apim, ensure-foundry-agents, seed-demo-data [`7eaa28e`]
- PostgreSQL outputs added to provision job [`7eaa28e`]
- AKS module: enabled public network access, disabled local accounts [`c60ca77`]

### Fixed
- `BaseRepository` JSONB serialization: `json.loads()` / `json.dumps()` for asyncpg [`bad1c75`]
- `seed_demo_data.py` JSONB insertion (asyncpg requires string) [`bad1c75`]
- Circuit breaker reset: `cb.close()` → `cb.reset()` via `CircuitBreakerMonitor` [`bad1c75`]
- Integration test event loop reuse with per-test `TestClient` fixture [`bad1c75`]
- MSAL SSR compatibility (window undefined during server rendering) [`ec219df`]
- Next.js 15 params promise unwrapping, CSS `::hover` → `:hover` for Turbopack [`ec219df`]
- Image remotePatterns migration, viewport metadata, favicon path [`ec219df`]
- PostCSS nesting plugin compatibility (downgraded to v12.1.5) [`ec219df`]
- OTel semantic conventions compatibility shim for agent-framework [`6af9c16`, `d4c4895`]
- Graceful startup without memory/model env vars [`8ce9b25`, `a80f6fb`]
- Indentation error in crm-profile-aggregation agents.py [`6b44680`]
- Uvicorn module path in agent Dockerfiles [`847e52a`]
- Stale build artifacts and OpenTelemetry pinning [`40dfc43`]

### Testing
- **165 tests passing** (lib + agent services + CRUD integration)
- 87 backend tests (unit + integration) — coverage floor: 75%
- Lib coverage: 73% (1895 statements)
- Integration tests run against live PostgreSQL (Azure Flexible Server)

### Dependencies

**Frontend**: @azure/msal-browser@5.1.0, @azure/msal-react@5.0.3, @tanstack/react-query@5.90.20, axios@1.7.9, next@16.2.0-canary.17, tailwindcss@3.4.0

**Backend**: fastapi@0.115+, asyncpg, azure-eventhub@5.12+, azure-identity@1.19+, pydantic@2.10+, httpx, circuitbreaker, tenacity, PyJWT

---

## [0.10.0] - 2026-01-30

> **Commits**: `ec219df` (PR #23 — Feat/api layer)
> First API integration layer: frontend services, backend CRUD endpoints, MSAL auth.

### Added
- CRUD Service core: FastAPI with lifespan, CORS, global exception handling, structured logging [`ec219df`]
- Entra ID JWT validation with RBAC (4 roles: anonymous, customer, staff, admin) [`ec219df`]
- Base repository pattern with Cosmos DB integration and Managed Identity [`ec219df`]
- 31 API routes: health (3), auth (3), users (2), products (2), categories (2), cart (4), orders (4), checkout/payments (3), reviews (2), staff analytics (1), staff support (2), staff logistics (2) [`ec219df`]
- Event publishing to 5 Event Hubs topics (user, product, order, inventory, payment) [`ec219df`]
- MCP agent client for optional enrichment calls [`ec219df`]
- Frontend Axios client with JWT interceptors and error handling [`ec219df`]
- 6 TypeScript services: product, cart, order, auth, user, checkout [`ec219df`]
- 5 React Query hooks: useProducts, useCart, useOrders, useCheckout, useUser [`ec219df`]
- MSAL configuration (SSR-safe), AuthContext with popup login, token refresh [`ec219df`]
- QueryProvider (React Query), AuthProvider (MSAL) [`ec219df`]
- `INTEGRATION.md` in `apps/ui/` [`ec219df`]
- Shared infrastructure Bicep with Azure Verified Modules (AVM) [`378226c`]
- Infrastructure summary, deployment scripts, Bicep modules [`733280b`]

---

## [0.9.0] - 2026-01-29

> **Commits**: `53c5fb5`..`d30ef0f` (PRs #1–#9, #21–#22)
> Framework stabilization: CI, security, linting, unit tests, governance.

### Added
- Unit test suite for lib framework [`d30ef0f`]
- Infrastructure governance and compliance guidelines [`94ac73e`, `0058dbe`]
- CI/CD workflows: build, lint, test, CodeQL analysis [`f72558b`, `81e42ff`]
- Security policy documentation [`f72558b`]
- Foundry agent configuration across all 21 services [`b11c020`]

### Fixed
- Base agent: typo fix, reduced boilerplate, improved routing logic [`b1dcaab`]
- Explicit returns mixed with implicit fall-through [`9ff5ec8`]
- Empty except clauses [`1950fc7`]
- Variable defined multiple times [`3061219`]
- Workflow permission declarations (code scanning alerts #3–#6) [`1bc6829`, `c13b068`, `7ccaf49`, `53c5fb5`]

---

## [0.8.0] - 2026-01-28

> **Commits**: `bbe6590`..`efb7ca3`
> Domain agent implementation across all 5 verticals.

### Added
- **E-commerce agents** (5): cart-intelligence, checkout-support, order-status, product-detail-enrichment, catalog-search [`30c3c02`]
- **CRM agents** (4): profile-aggregation, segmentation-personalization, campaign-intelligence, support-assistance [`bbe6590`]
- **Inventory agents** (4): health-check, jit-replenishment, reservation-validation, alerts-triggers [`0006dcf`]
- **Logistics agents** (4): eta-computation, carrier-selection, returns-support, route-issue-detection [`853ee1e`]
- **Product management agents** (4): normalization-classification, acp-transformation, consistency-validation, assortment-optimization [`2c8cd98`]
- App component documentation for all domains [`efb7ca3`]
- Operational playbooks for resilience and performance [`39e6586`]

### Changed
- Memory components enhanced with connection pooling and builder support [`7a7fd4b`]
- Added `MemoryBuilder` and `MemoryClient` for cascading memory management [`e1ad45d`]

---

## [0.7.0] - 2026-01-27

> **Commit**: `fc5439f`
> Codebase refactoring for maintainability.

### Changed
- Refactored code structure for improved readability and maintainability [`fc5439f`]

---

## [0.6.0] - 2026-01-13

> **Commits**: `0c18b4d`, `bafa28b`
> Adapter-to-connector migration.

### Changed
- Refactored adapters to connectors with canonical interfaces [`0c18b4d`]

---

## [0.5.0] - 2026-01-06

> **Commit**: `da27e3b`
> Documentation updates.

### Changed
- Updated business summary documentation [`da27e3b`]

---

## [0.1.0] - 2025-12-31

> **Commits**: `9e7baf4`, `8bd01c4`
> Project inception.

### Added
- Initial commit with repository scaffolding [`9e7baf4`]
- Base documentation and project structure [`8bd01c4`]
- Agent framework (`holiday_peak_lib`) — adapters, agents, memory, orchestration, schemas, utils
- Three-tier memory architecture: Redis (hot), Cosmos DB (warm), Blob Storage (cold)
- Frontend UI scaffolding (Next.js with 13 pages, 52 components)
- Shared infrastructure Bicep modules
- Architecture documentation (20 ADRs)
- Backend implementation plan

### Infrastructure
- AKS configuration (3 node pools)
- ACR with geo-replication
- Cosmos DB schemas (10 containers)
- Event Hubs namespace (5 topics)
- Redis Cache Premium
- Key Vault integration
- Virtual Network with Private Endpoints
- GitHub Actions CI/CD pipelines

---

## Notes

### Version Strategy
- **Major** (X.0.0): Breaking changes, major feature releases
- **Minor** (0.X.0): New features, non-breaking changes
- **Patch** (0.0.X): Bug fixes, documentation updates

### Links
- [GitHub Releases](https://github.com/Azure-Samples/holiday-peak-hub/releases)
- [Implementation Roadmap](docs/IMPLEMENTATION_ROADMAP.md)
- [CRUD Service Documentation](docs/architecture/crud-service-implementation.md)
- [Frontend Integration Guide](apps/ui/INTEGRATION.md)
- [Architecture Documentation](docs/README.md)
