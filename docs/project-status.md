# Project Status & Issue Prioritization

> Generated: 2026-04-19 | Version: main (post PR #859) | Branch: `main`

## Current Main Snapshot (2026-04-19)

### Recently Merged (April 2026)

| PR | Title | Impact |
|----|-------|--------|
| #859 | Consolidate catalog-search strict-4s pipeline | Strict 4s intelligent pipeline with GPT-5-nano `reasoning_effort="minimal"`, parallel search fan-out, direct product construction, 10/10 live integration tests |
| #802 | Replace FoundryInvoker with FoundryAgentInvoker (MAF runtime) | Fixes silent tool-dropping; upgrades `agent-framework` to 1.0.1 GA |
| #800 | Parallelize memory reads/writes, add memory tools | Concurrent hot/warm/cold I/O via `asyncio.gather` |
| #798 | Add start-dev-environment script | MCAPSGov nightly shutdown recovery automation |
| #797 | Add fix-issues-pipeline prompt | End-to-end issue resolution workflow |
| #796 | Parallelize catalog-search I/O | Eliminates duplicate keyword search, reduces p95 latency |
| #794 | Fix CRUD_SERVICE_URL port 8000→80 | Resolves inter-service connectivity in AKS |
| #793 | Scaffold MkDocs documentation site | Future docs-as-website in `mkdocs/` |
| #792 | Flux Phase B — full GitOps reconciliation | Removes kubectl-apply fallback |
| #789 | API Center governance + APIM MCP strategy | ADR-027 implementation |
| #788 | Namespace isolation (ADR-026) | Separate CRUD and agent Kubernetes namespaces |
| #785 | Flux CD migration (ADR-017) | Declarative manifest reconciliation |
| #776 | Harden CRUD Entra auth rollout | Improved authentication contracts |
| #771 | Complete self-healing epic | Incident lifecycle, remediation policy, audit trail |

### What Changed (Since Last Snapshot)

- **Executive demo homepage refactor (2026-04-28)**: `apps/ui/app/page.tsx` now routes to a single-page, scroll-driven executive demo where the robots are the primary narrative device. The homepage now stages the cold open, hero search, CRM boardroom, discovery duo, truth pipeline, catalog galaxy, cart/checkout, inventory, logistics, returns/support, platform telemetry, and scenario close as one continuous presentation surface. Supporting additions include route-local demo components, a reusable agent profile drawer, and additive `AgentRobot` scene props (`facing`, `pointAt`, `lookAt`, `toolOverride`, `scenePeer`).
- **Commerce journey agent continuity (2026-04-28)**: The storefront drill-down routes now keep visible agent presence past the homepage. `AgentRobotOverlay` accepts semantic size presets and scene-staging props, and category, orders, order detail, cart, search, product, and checkout surfaces now stage primary and secondary agents along the buyer journey.
- **Commerce stage contract + drawer/operator follow-through (2026-04-28)**: Shopping-flow routes now share `apps/ui/components/templates/CommerceAgentLayout.tsx` so the primary-stage robot, side-cast robot, and telemetry chip are declared uniformly. `AgentProfileDrawer` now renders input/output schemas, curated sample payloads, a live sample-run action, and an in-place trace explorer modal; scenario drill-down drawers also receive live monitor metrics instead of static placeholders.
- **Drawer streaming + telemetry completion (2026-04-28)**: `AgentProfileDrawer` sample runs now stream over `/invoke/stream`, commerce telemetry chips now hydrate from persisted `_telemetry` across search, product enrichment, and product-graph summary invoke seams, and `/order/[id]` now keeps `logistics-route-issue-detection` as the default side cast until return flow activation swaps in returns + support.
- **Frontend regression hardening (2026-04-28)**: Added focused drawer unit coverage plus Playwright specs for the executive demo narrative, light/dark visual regression, and admin cockpit readiness (`apps/ui/tests/e2e/demo-narrative.spec.ts`, `apps/ui/tests/e2e/dark-mode-regression.spec.ts`, `apps/ui/tests/e2e/cockpit-readiness.spec.ts`).
- **Scenario drill-down briefs (2026-04-28)**: Added `/scenarios/[id]` route briefs for discovery, customer 360, truth, and checkout flows, backed by shared scenario metadata so the homepage close scene can jump into a dedicated brief before sending users to live product or operator surfaces.
- **Catalog-search strict 4s pipeline (v6)**: Entire intelligent pipeline runs inside `asyncio.wait_for(timeout=4.0)`. Intent classification via GPT-5-nano with `reasoning_effort="minimal"` (1.5s budget). Parallel keyword + hybrid search fan-out. Direct product construction from AI Search documents (no CRUD round-trip). Fire-and-forget history writes. Deployed as `strict-4s-v6` on 2 AKS replicas.
- **`reasoning_effort` parameter support in Foundry pipeline**: `FoundryAgentInvoker` now plumbs `reasoning_effort` through `_PreparedInvocation` → `_request_response_impl` → `run_kwargs["options"]`. Guards ensure the parameter is only sent when explicitly passed.
- **Live integration test suite**: 11 tests (10 parametrized queries + summary report) validate the live APIM→AKS→AI Foundry→AI Search pipeline. 10/10 within budget, avg ~2.77s.
- **FoundryAgentInvoker** replaces legacy `FoundryInvoker`: agent tools are now properly forwarded through the Microsoft Agent Framework `FoundryAgent` runtime instead of being silently dropped.
- `agent-framework` upgraded from unpinned to `>=1.0.1` GA across all 27 Python service packages; resolves `ContextProvider` vs `BaseContextProvider` import incompatibility.
- Memory tier operations parallelized with `asyncio.gather` for reduced latency; new memory tools (`get_memory`, `set_memory`, `search_memory`) and `gather_adapters` helper available.
- AKS deployments now reconcile through Flux CD GitOps (ADR-017); kubectl-apply path removed.
- **ADR-017 Phase 2 (in progress)**: migrating from rendered YAML to Flux HelmRelease CRDs for in-cluster Helm rendering. Pilot: `ecommerce-catalog-search` deployed via HelmRelease; remaining 25 services migrate incrementally. New HelmRelease manifests in `.kubernetes/releases/agents/`.
- CRUD and agent services run in separate Kubernetes namespaces (ADR-026).
- API Center governance and APIM MCP strategy implemented (ADR-027).
- Self-healing runtime completed with incident lifecycle state machine, remediation policy, and audit trail.
- Catalog-search I/O parallelized; duplicate keyword search eliminated.

### Validation

- UI route smoke validation: `yarn test --runInBand tests/unit/pagesRender.test.tsx` in `apps/ui` passes after the executive demo refactor and commerce continuity rollout.
- Drawer/admin/page focused UI validation: `yarn test --runInBand --runTestsByPath tests/unit/AgentProfileDrawer.test.tsx tests/unit/AdminServiceDashboardPage.test.tsx tests/unit/pagesRender.test.tsx` passes after the drawer enrichment and commerce layout rollout.
- Final telemetry seam validation: `yarn test --runInBand --runTestsByPath tests/unit/productService.test.ts tests/unit/ProductGraphCanvas.test.tsx` passes after wiring enrichment-backed product loads and graph-summary invocations into persisted telemetry.
- Full local test run: **1796 passed** (1136 lib + 660 app), 0 failures.
- Catalog-search unit tests: **34 passed** (including 14 intelligent-mode tests), ~3.3s.
- Live integration tests: **10/10 queries within 7s wall-clock budget**, avg ~2.77s.
- CI gate: lint, test, CodeQL, pip-audit, contract-gate all passing on `main`.
- 35 Architecture Decision Records (ADR-001 through ADR-027).

### Note

- Historical sections below preserve earlier v1.1.0 and v2.0.0 planning/trackers for audit context and may include superseded planning entries.

---

## Runtime Hotfix Notes (2026-04-19)

### Catalog Search Strict 4s Intelligent Pipeline (Issue #859)

**Optimizations applied (v1→v6)**:

1. **Skip model answer generation** in strict mode — pipeline returns deterministic response directly.
2. **Fire-and-forget history writes** — `asyncio.create_task()` decouples memory persistence from the response path.
3. **Bounded availability check** — 0.5s timeout with `["unknown"]` fallback per product.
4. **Direct AI Search product construction** — builds `CatalogProduct` from search documents, eliminating CRUD round-trips.
5. **Intent timeout** — 1.5s hard cap on GPT-5-nano classification; falls back to deterministic regex policy.
6. **Keyword search for full docs** — `keyword_search` returns complete `AISearchDocumentResult` with all fields needed for product construction.
7. **`reasoning_effort="minimal"`** — GPT-5 parameter that eliminates most reasoning tokens for fast intent classification.

**Foundry pipeline changes (`lib/src/holiday_peak_lib/agents/foundry.py`)**:
- `_PreparedInvocation` NamedTuple gains `reasoning_effort: str | None = None` field.
- `_prepare_invocation()` extracts `reasoning_effort` from kwargs before discarding transport-only keys.
- `_request_response_impl()` and `_stream_impl()` pass `run_kwargs["options"] = {"reasoning_effort": prep.reasoning_effort}` when not `None`.

**Deployment**: `strict-4s-v6` image deployed to AKS (2 replicas, 0 restarts). APIM gateway endpoint validated.

**Test results**: 34 unit tests passing, 10/10 live integration queries within budget (avg ~2.77s).

---

## v1.1.0 Release Highlights

**Release Date**: 2026-03-03

### Completed Features
- **Enterprise Connectors**: Oracle Fusion Cloud SCM, Salesforce CRM, SAP S/4HANA, Dynamics 365
- **Enterprise Hardening**: Circuit breaker, bulkhead, rate limiter, telemetry integration
- **Product Truth Layer Foundation**: Pydantic v2 models, Truth Store Adapter, Ingestion service
- **PIM Writeback Module**: Opt-in writeback with conflict detection and audit trail
- **HITL Staff Review UI**: Review queue, evidence panel, bulk approval
- **Frontend API Integration**: Enhanced checkout, order tracking, inventory pages
- **Test Coverage**: 635 tests passing (up from 386)

### Runtime Hotfix Notes (2026-03-06)
- **Truth Export Compatibility**: Added a `truth_export.schemas_compat` fallback to keep `truth-export` functional when runtime images resolve an older `holiday-peak-lib` package that does not expose `holiday_peak_lib.schemas.truth`.
- **Notebook Live Checks**: Updated the Product Truth Layer notebook live integration cell to support Cosmos SDK query compatibility differences and improved PostgreSQL sample payload parsing.
- **Lib Config Test Determinism**: Resolved issue #29 by isolating env-file loading in `lib/tests/test_config.py` via `_env_file=None`, preventing local `.env` leakage into test assertions (`python -m pytest lib/tests/test_config.py -q` → `20 passed`).

### Runtime Hotfix Notes (2026-03-12)
- **Mandatory CI Gate Enforcement (Issue #30)**: Required smoke/health checks in deploy workflows now fail deterministically on transport failures and non-200 responses; transport failures are normalized as hard failures in required checks; permissive handling is retained only for advisory/non-gating diagnostics and cleanup paths.
- **Azure AI Search Provisioning/Runtime Activation (Issue #32)**: Shared infrastructure now provisions the Azure AI Search service, `azd` `postprovision` ensures the `catalog-products` index after service readiness, deploy workflow and Helm rendering propagate `AI_SEARCH_ENDPOINT`, `AI_SEARCH_INDEX`, and `AI_SEARCH_AUTH_MODE`, and catalog-search falls back to adapter retrieval when Search is unavailable or empty.

### Runtime Hotfix Notes (2026-03-14)
- **Main Branch Stabilization (Issue #246)**: CRUD semantic search fallback now degrades safely to repository search when semantic payloads are non-canonical; product enrichment now returns `None` when enrichment URL is not explicitly configured, restoring deterministic fallback behavior expected by tests.
- **Quality Gate Revalidation**: Repository validation on `main` now reports `1430 passed, 2 skipped` for pytest and a passing pylint score (`9.87/10`, above fail-under threshold).
- **Branch Hygiene (Issue #248)**: temporary remediation branches/artifacts were pruned from local operations clones to keep stabilization flow aligned to `main`.

### Runtime Hotfix Notes (2026-03-17)
- **AGC Subnet Drift Realignment**: Shared infra defaults now pin the delegated `agc` subnet to `10.0.12.0/24` so `azd provision` matches the live dev VNet layout and stops attempting a destructive subnet replacement during canonical deploy runs.
- **GitHub OIDC Hook Refresh**: Root POSIX `azd` `postprovision` and `postdeploy` hooks now refresh Azure CLI login from the live GitHub Actions OIDC token immediately before Azure/AKS operations, retrying empty or malformed token responses explicitly so remote deploy failures surface as actionable OIDC refresh errors instead of opaque JSON parsing crashes.

### Runtime Hotfix Notes (2026-03-19)
- **Dependency Management Hardening (Issue #316)**: Agent service `pyproject.toml` dependencies now use minimum version constraints for key runtime libraries and include a local editable `holiday-peak-lib` source mapping for development workflows.
- **Lockfile and Build Reproducibility**: App `.dockerignore` files now include `uv.lock` in Docker build context, service Dockerfiles use frozen `uv` sync installs, and CI validates `yarn.lock` / `uv.lock` freshness before linting.
- **Infrastructure Secret and Region Hygiene**: Shared infrastructure now uses a random `newGuid()`-seeded fallback for PostgreSQL admin password generation and parameterizes Azure AI Foundry location instead of hardcoding the region.
- **UI Product Enrichment Monitoring (Issue #352)**: Admin now exposes a dedicated enrichment monitoring route (`/admin/enrichment-monitor`) with real-time stage/job visibility, retry controls on monitor failures/log entries, and throughput + approval-rate visual indicators; search now surfaces explicit mode/intent signal chips; top navigation includes a pipeline status indicator that links directly to the monitor.

### Runtime Hotfix Notes (2026-04-05)
- **Catalog Search Strict AI Search Runtime Hardening (Issue #675)**: Deployment workflow now propagates `CATALOG_SEARCH_REQUIRE_AI_SEARCH=true` for `ecommerce-catalog-search` and `false` for other services, Helm render hooks pass the variable into container manifests, and runtime/docs now codify fail-closed readiness with bounded startup/readiness seeding instead of continuity fallback in AKS strict mode.

### Runtime Hotfix Notes (2026-04-06)
- **CRUD Product Listing Availability Guardrail**: `GET /api/products` now fails open to an empty list when repository access times out or is temporarily unavailable, preventing repeated 503 responses while preserving a stable read contract for storefront and admin surfaces.
- **CRUD Redis Auth Secret Wiring**: Shared infrastructure now persists the Redis primary key into Key Vault (`redis-primary-key`) and propagates `REDIS_PASSWORD_SECRET_NAME` through `azd`/Helm hooks; CRUD startup resolves the secret at runtime and readiness now authenticates Redis pings using the configured secure URL path.

### Runtime Hotfix Notes (2026-04-10)
- **AKS Redis Runtime Contract Hardening**: Helm render hooks now suppress passwordless `REDIS_URL` injection when `REDIS_HOST` is already available, preserving the intended Key Vault secret-resolution path for Redis credentials in deployed services.
- **CRUD Deployment Readiness Smoke Tightening**: `deploy-azd` rollout checks now validate CRUD via `/api/ready` instead of `/api/health`, so PostgreSQL and Redis dependency regressions fail deployment validation instead of passing shallow liveness checks.
- **CRUD Dev Readiness Probe Alignment**: Dev/local Helm rendering no longer downgrades CRUD readiness to `/health`, so dependency outages are surfaced consistently in-cluster instead of being masked by process-only liveness.
- **PostgreSQL Auth Contract Alignment**: `POSTGRES_AUTH_MODE` now drives the Flexible Server auth policy in Bicep and a pre-rollout workflow guard verifies the live server matches the configured runtime auth mode before CRUD is redeployed.
- **CRUD Entra Principal Alignment**: Entra-mode deployment outputs now resolve `POSTGRES_USER` to the CRUD workload identity principal (`<project>-<env>-crud-identity`), matching the pod identity used for token acquisition instead of the legacy agentpool principal.

### Merged PRs (v1.1.0)
| # | Title | Category |
|---|-------|----------|
| #161 | Job execution review and restart | CI/CD |
| #139 | Pydantic v2 truth schema models | Truth Layer |
| #146 | Truth Ingestion service | Truth Layer |
| #115 | Sample data and seeding | Truth Layer |
| #122 | Cosmos DB truth containers | Truth Layer |
| #124 | Generic REST DAM connector | Connectors |
| #121 | SAP S/4HANA connector | Connectors |
| #118 | Dynamics 365 connector | Connectors |
| #142 | Category schema population | Truth Layer |
| #143 | Event Hub topic configuration | Truth Layer |
| #140 | TruthLayerSettings config | Truth Layer |
| #153 | Stripe payment integration | Payments |
| #157 | Stripe checkout flow | Payments |
| #119 | Enterprise hardening patterns | Hardening |
| #116 | PIM writeback module | Truth Layer |
| #127 | HITL staff review UI pages | UI |
| #137 | Frontend API integration | UI |
| #154 | Oracle Fusion Cloud connector | Connectors |
| #156 | Salesforce CRM connector | Connectors |

---

## CI/CD Status

### Build Status
| Workflow | Run | Status | Notes |
|---|---|---|---|
| `ci.yml` | Latest | ✅ Passing | 712 tests passing on main, all lint checks green |
| `build-push` | Latest | ✅ Passing | Docker images published to GHCR |
| `deploy-azd` | Latest | ✅ Passing | Azure deployment successful |

---

## Closed Issues (Resolved in v1.1.0)

| # | Title | Severity | Category | Status |
|---|---|---|---|---|
| [#25](https://github.com/Azure-Samples/holiday-peak-hub/issues/25) | CRUD service not registered in APIM | Critical | Infrastructure | ✅ Closed |
| [#26](https://github.com/Azure-Samples/holiday-peak-hub/issues/26) | Agent health endpoints return 500 through APIM | Critical | Agents | ✅ Closed |
| [#27](https://github.com/Azure-Samples/holiday-peak-hub/issues/27) | SWA API proxy returns 404 for all /api/* routes | High | Frontend | ✅ Closed |
| [#28](https://github.com/Azure-Samples/holiday-peak-hub/issues/28) | Frontend pages use hardcoded mock data instead of API hooks | High | Frontend | ✅ Closed |
| [#31](https://github.com/Azure-Samples/holiday-peak-hub/issues/31) | Payment processing fully stubbed | Medium | Backend | ✅ Closed (PR #153, #157) |
| [#32](https://github.com/Azure-Samples/holiday-peak-hub/issues/32) | Azure AI Search not provisioned — catalog-search agent non-functional | Medium | Infrastructure | ✅ Closed (AI Search provisioning + env propagation + runtime fallback path) |
| [#33](https://github.com/Azure-Samples/holiday-peak-hub/issues/33) | Server-side route protection middleware | Medium | Frontend | ✅ Closed (`apps/ui/middleware.ts`, login redirect messaging polish in `apps/ui/app/auth/login/page.tsx`) |
| [#36](https://github.com/Azure-Samples/holiday-peak-hub/issues/36) | SAP S/4HANA connector | Low | Connectors | ✅ Closed (PR #121) |
| [#40](https://github.com/Azure-Samples/holiday-peak-hub/issues/40) | Salesforce CRM connector | Low | Connectors | ✅ Closed (PR #156) |
| [#41](https://github.com/Azure-Samples/holiday-peak-hub/issues/41) | Microsoft Dynamics 365 connector | Low | Connectors | ✅ Closed (PR #118) |
| [#88](https://github.com/Azure-Samples/holiday-peak-hub/issues/88) | Phase 1: Cosmos DB containers | Critical | Truth Layer | ✅ Closed (PR #122) |
| [#89](https://github.com/Azure-Samples/holiday-peak-hub/issues/89) | Phase 1: Event Hub topics | Critical | Truth Layer | ✅ Closed (PR #143) |
| [#90](https://github.com/Azure-Samples/holiday-peak-hub/issues/90) | Phase 1: Product Graph data models | Critical | Truth Layer | ✅ Closed (PR #139) |
| [#95](https://github.com/Azure-Samples/holiday-peak-hub/issues/95) | Phase 1: TruthLayerSettings config | Critical | Truth Layer | ✅ Closed (PR #140) |
| [#97](https://github.com/Azure-Samples/holiday-peak-hub/issues/97) | Phase 2: Generic DAM connector | High | Truth Layer | ✅ Closed (PR #124) |
| [#100](https://github.com/Azure-Samples/holiday-peak-hub/issues/100) | Phase 2: Sample data and seed scripts | High | Truth Layer | ✅ Closed (PR #115) |
| [#103](https://github.com/Azure-Samples/holiday-peak-hub/issues/103) | Phase 3: HITL Staff Review UI pages | High | Truth Layer | ✅ Closed (PR #127) |
| [#107](https://github.com/Azure-Samples/holiday-peak-hub/issues/107) | Phase 5: PIM writeback module | Low | Truth Layer | ✅ Closed (PR #116) |
| [#110](https://github.com/Azure-Samples/holiday-peak-hub/issues/110) | Phase 5: Enterprise hardening | Low | Hardening | ✅ Closed (PR #119) |
| [#112](https://github.com/Azure-Samples/holiday-peak-hub/issues/112) | docs: Document Entra ID configuration for local and deployed environments | Low | Documentation | ✅ Closed |
| [#29](https://github.com/Azure-Samples/holiday-peak-hub/issues/29) | 10 lib config tests fail due to schema drift | Medium | Testing | ✅ Closed (test env-file isolation in `lib/tests/test_config.py`) |
| [#30](https://github.com/Azure-Samples/holiday-peak-hub/issues/30) | CI agent tests silently swallowed with `\|\| true` | Medium | CI/CD | ✅ Closed (required gates now hard-fail on normalized transport and HTTP failures) |
| [#79](https://github.com/Azure-Samples/holiday-peak-hub/issues/79) | Connector Registry Pattern | Medium | Architecture | ✅ Closed |
| [#80](https://github.com/Azure-Samples/holiday-peak-hub/issues/80) | Event-Driven Connector Sync | Medium | Architecture | ✅ Closed |
| [#81](https://github.com/Azure-Samples/holiday-peak-hub/issues/81) | Multi-Tenant Connector Config | Medium | Architecture | ✅ Closed |
| [#82](https://github.com/Azure-Samples/holiday-peak-hub/issues/82) | Protocol Interface Evolution | Medium | Architecture | ✅ Closed |
| [#83](https://github.com/Azure-Samples/holiday-peak-hub/issues/83) | Internal Data Enrichment Guardrails | Medium | Architecture | ✅ Closed |

---

## Active Pull Requests (In Progress)

### Code-Ready PRs (rebased, tests passing, ready for review)
| # | Title | Category | Tests | Status |
|---|-------|----------|-------|--------|
| [#144](https://github.com/Azure-Samples/holiday-peak-hub/pull/144) | Truth Layer Phase 1 Foundation | Truth Layer | 67 ✅ | ✅ Ready |
| [#147](https://github.com/Azure-Samples/holiday-peak-hub/pull/147) | TruthStoreAdapter + Product Graph models | Truth Layer | 49 ✅ | ✅ Ready |
| [#145](https://github.com/Azure-Samples/holiday-peak-hub/pull/145) | Event Hub Bicep topics | Infrastructure | N/A (Bicep) | ✅ Ready |
| [#148](https://github.com/Azure-Samples/holiday-peak-hub/pull/148) | Tenant Configuration model | Truth Layer | 44 ✅ | ✅ Ready |
| [#150](https://github.com/Azure-Samples/holiday-peak-hub/pull/150) | Event Hub helpers | Truth Layer | 14 ✅ | ✅ Ready |
| [#152](https://github.com/Azure-Samples/holiday-peak-hub/pull/152) | PIM/DAM connectors (Akeneo, Cloudinary, Salsify) | Connectors | 65 ✅ | ✅ Ready |
| [#158](https://github.com/Azure-Samples/holiday-peak-hub/pull/158) | Adobe AEP CRM connector | Connectors | 38 ✅ | ✅ Ready |
| [#159](https://github.com/Azure-Samples/holiday-peak-hub/pull/159) | Braze Customer Engagement connector | Connectors | 35 ✅ | ✅ Ready |

### Planning-Only PRs (rebased, no code yet)
| # | Title | Category | Status |
|---|-------|----------|--------|
| [#134](https://github.com/Azure-Samples/holiday-peak-hub/pull/134) | Protocol interface evolution strategy | Architecture | 📋 Planning |
| [#136](https://github.com/Azure-Samples/holiday-peak-hub/pull/136) | Reference architectures | Architecture | 📋 Planning |
| [#141](https://github.com/Azure-Samples/holiday-peak-hub/pull/141) | Azure AI Search provisioning | Infrastructure | 📋 Planning |
| [#155](https://github.com/Azure-Samples/holiday-peak-hub/pull/155) | Blue Yonder Luminate connector | Connectors | 📋 Planning |
| [#160](https://github.com/Azure-Samples/holiday-peak-hub/pull/160) | Salsify PXM connector | Connectors | 📋 Planning |


---

## Open Issues — Prioritization List

Ordered by **review priority** from highest to lowest.

---

### 🔴 Priority 1 — Platform Quality Bugs (agent: `Platform_Quality`)

No remaining open Platform Quality issues.

---

### 🟠 Priority 2 — Product Truth Layer: Remaining Phases (agent: `Truth_Layer_Pipeline`)

**Phase 1 Complete** ✅ (PRs #122, #139, #140, #143 merged). Continuing with Phases 2-5.

| # | Title | Phase | Status |
|---|---|---|---|
| [#87](https://github.com/Azure-Samples/holiday-peak-hub/issues/87) | **Epic: Product Truth Layer** | Epic | In Progress |
| [#91](https://github.com/Azure-Samples/holiday-peak-hub/issues/91) | Phase 1: Truth Store Cosmos DB adapter | 1 | PR #147 (Draft) |
| [#92](https://github.com/Azure-Samples/holiday-peak-hub/issues/92) | Phase 1: Tenant Configuration model | 1 | PR #148 (Draft) |
| [#93](https://github.com/Azure-Samples/holiday-peak-hub/issues/93) | Phase 1: UCP schema and category schemas | 1 | PR #148 (Draft) |
| [#94](https://github.com/Azure-Samples/holiday-peak-hub/issues/94) | Phase 1: Event Hub helpers | 1 | PR #150 (Draft) |
| [#96](https://github.com/Azure-Samples/holiday-peak-hub/issues/96) | Phase 2: Generic REST PIM connector | 2 | PR #151 (Draft) |
| [#98](https://github.com/Azure-Samples/holiday-peak-hub/issues/98) | Phase 2: Truth Ingestion service | 2 | ✅ Closed (PR #146) |
| [#99](https://github.com/Azure-Samples/holiday-peak-hub/issues/99) | Phase 2: Completeness Engine refactor | 2 | ✅ Closed (PR #123) |
| [#101](https://github.com/Azure-Samples/holiday-peak-hub/issues/101) | Phase 3: Truth Enrichment service | 3 | PR #125 (Draft) |
| [#102](https://github.com/Azure-Samples/holiday-peak-hub/issues/102) | Phase 3: Truth HITL service (Human-in-the-Loop) | 3 |
| [#103](https://github.com/Azure-Samples/holiday-peak-hub/issues/103) | Phase 3: HITL Staff Review UI pages | 3 |
| [#104](https://github.com/Azure-Samples/holiday-peak-hub/issues/104) | Phase 4: Truth Export service and Protocol Mappers | 4 |
| [#105](https://github.com/Azure-Samples/holiday-peak-hub/issues/105) | Phase 4: CRUD service truth-layer routes (6 new route modules) | 4 |
| [#106](https://github.com/Azure-Samples/holiday-peak-hub/issues/106) | Phase 4: Postman collection and API documentation | 4 |

---

### 🟡 Priority 3 — Architecture Patterns (agent: `Architecture_Patterns`)

Marked `priority: medium`. Can proceed in parallel with Truth Layer work.

| # | Title | Status |
|---|---|---|
| [#79](https://github.com/Azure-Samples/holiday-peak-hub/issues/79) | Architecture: Connector Registry Pattern | ✅ Closed |
| [#80](https://github.com/Azure-Samples/holiday-peak-hub/issues/80) | Architecture: Event-Driven Sync Pattern | ✅ Closed |
| [#81](https://github.com/Azure-Samples/holiday-peak-hub/issues/81) | Architecture: Multi-Tenant Configuration | ✅ Closed |
| [#82](https://github.com/Azure-Samples/holiday-peak-hub/issues/82) | Architecture: Protocol Evolution | ✅ Closed |
| [#83](https://github.com/Azure-Samples/holiday-peak-hub/issues/83) | Architecture: Data Guardrails | ✅ Closed |
| [#84](https://github.com/Azure-Samples/holiday-peak-hub/issues/84) | Architecture: Reference Architecture Patterns | Open |

---

### 🟡 Priority 4 — Enterprise Connectors (agent: `Enterprise_Connectors`)

**Completed in v1.1.0**: Oracle Fusion, Salesforce, SAP S/4HANA, Dynamics 365, Generic DAM

#### Inventory & SCM
| # | Connector | Status |
|---|---|---|
| [#36](https://github.com/Azure-Samples/holiday-peak-hub/issues/36) | SAP S/4HANA | ✅ Closed (PR #121) |
| [#37](https://github.com/Azure-Samples/holiday-peak-hub/issues/37) | Oracle NetSuite | Open |
| [#38](https://github.com/Azure-Samples/holiday-peak-hub/issues/38) | Manhattan WMS | Open |
| [#39](https://github.com/Azure-Samples/holiday-peak-hub/issues/39) | Blue Yonder / JDA | Open |

#### CRM
| # | Connector | Status |
|---|---|---|
| [#40](https://github.com/Azure-Samples/holiday-peak-hub/issues/40) | Salesforce CRM | ✅ Closed (PR #156) |
| [#41](https://github.com/Azure-Samples/holiday-peak-hub/issues/41) | Microsoft Dynamics 365 | ✅ Closed (PR #118) |
| [#42](https://github.com/Azure-Samples/holiday-peak-hub/issues/42) | HubSpot | Open |
| [#43](https://github.com/Azure-Samples/holiday-peak-hub/issues/43) | Adobe Experience Manager | Open |

#### Commerce
| # | Connector | Status |
|---|---|---|
| [#44](https://github.com/Azure-Samples/holiday-peak-hub/issues/44) | Shopify | Open |
| [#45](https://github.com/Azure-Samples/holiday-peak-hub/issues/45) | Magento / Adobe Commerce | Open |
| [#46](https://github.com/Azure-Samples/holiday-peak-hub/issues/46) | Commercetools | Open |
| [#47](https://github.com/Azure-Samples/holiday-peak-hub/issues/47) | BigCommerce | Open |

#### PIM / DAM
| # | Connector | Status |
|---|---|---|
| [#48](https://github.com/Azure-Samples/holiday-peak-hub/issues/48) | Akeneo PIM | Open |
| [#49](https://github.com/Azure-Samples/holiday-peak-hub/issues/49) | inRiver PIM | Open |
| [#50](https://github.com/Azure-Samples/holiday-peak-hub/issues/50) | Salsify | Open |
| [#51](https://github.com/Azure-Samples/holiday-peak-hub/issues/51) | Bynder DAM | Open |
| [#52](https://github.com/Azure-Samples/holiday-peak-hub/issues/52) | Cloudinary DAM | Open |
| - | Generic REST DAM | ✅ Closed (PR #124) |

#### Data & Analytics
| # | Connector | Status |
|---|---|---|
| [#53](https://github.com/Azure-Samples/holiday-peak-hub/issues/53) | Snowflake | Open |
| [#54](https://github.com/Azure-Samples/holiday-peak-hub/issues/54) | Databricks | Open |
| [#55](https://github.com/Azure-Samples/holiday-peak-hub/issues/55) | Google BigQuery | Open |

#### Integration / Middleware
| # | Connector | Status |
|---|---|---|
| [#56](https://github.com/Azure-Samples/holiday-peak-hub/issues/56) | MuleSoft Anypoint | Open |
| [#57](https://github.com/Azure-Samples/holiday-peak-hub/issues/57) | Dell Boomi | Open |
| [#58](https://github.com/Azure-Samples/holiday-peak-hub/issues/58) | Informatica | Open |
| [#59](https://github.com/Azure-Samples/holiday-peak-hub/issues/59) | Talend | Open |

#### Workforce
| # | Connector | Status |
|---|---|---|
| [#60](https://github.com/Azure-Samples/holiday-peak-hub/issues/60) | Workday HCM | Open |
| [#61](https://github.com/Azure-Samples/holiday-peak-hub/issues/61) | ADP Workforce | Open |
| [#62](https://github.com/Azure-Samples/holiday-peak-hub/issues/62) | SAP SuccessFactors | Open |

#### Identity
| # | Connector | Status |
|---|---|---|
| [#63](https://github.com/Azure-Samples/holiday-peak-hub/issues/63) | Okta Identity | Open |
| [#64](https://github.com/Azure-Samples/holiday-peak-hub/issues/64) | Azure Active Directory (Entra) | Open |
| [#65](https://github.com/Azure-Samples/holiday-peak-hub/issues/65) | Ping Identity | Open |

#### Additional Enterprise Connectors
| # | Connector | Status |
|---|---|---|
| [#66](https://github.com/Azure-Samples/holiday-peak-hub/issues/66) | Zendesk (Support) | Open |
| [#67](https://github.com/Azure-Samples/holiday-peak-hub/issues/67) | ServiceNow | Open |
| [#68](https://github.com/Azure-Samples/holiday-peak-hub/issues/68) | Twilio (Communications) | Open |
| [#69](https://github.com/Azure-Samples/holiday-peak-hub/issues/69) | Klaviyo (Marketing) | Open |
| [#70](https://github.com/Azure-Samples/holiday-peak-hub/issues/70) | OneTrust (Privacy) | Open |
| [#71](https://github.com/Azure-Samples/holiday-peak-hub/issues/71) | Stripe (Payments) | ✅ Closed (PR #153, #157) |
| [#72](https://github.com/Azure-Samples/holiday-peak-hub/issues/72) | Braintree (Payments) | Open |
| [#73](https://github.com/Azure-Samples/holiday-peak-hub/issues/73) | Narvar (Post-Purchase) | Open |
| [#74](https://github.com/Azure-Samples/holiday-peak-hub/issues/74) | Loop Returns | Open |
| [#75](https://github.com/Azure-Samples/holiday-peak-hub/issues/75) | Returnly | Open |
| [#76](https://github.com/Azure-Samples/holiday-peak-hub/issues/76) | Avalara (Tax) | Open |
| [#77](https://github.com/Azure-Samples/holiday-peak-hub/issues/77) | Vertex (Tax) | Open |
| [#78](https://github.com/Azure-Samples/holiday-peak-hub/issues/78) | FreightQuote / EasyPost (Shipping) | Open |

---

### 🟢 Priority 5 — Product Truth Layer: Phase 5 Hardening (agent: `Truth_Layer_Hardening`)

**Completed in v1.1.0**: PIM writeback module, Enterprise hardening

| # | Title | Status |
|---|---|---|
| [#107](https://github.com/Azure-Samples/holiday-peak-hub/issues/107) | Phase 5: PIM writeback module (opt-in) | ✅ Closed (PR #116) |
| [#108](https://github.com/Azure-Samples/holiday-peak-hub/issues/108) | Phase 5: Evidence extraction for AI enrichments | PR #117 (Draft) |
| [#109](https://github.com/Azure-Samples/holiday-peak-hub/issues/109) | Phase 5: Admin UI pages (schemas, config, analytics) | Open |
| [#110](https://github.com/Azure-Samples/holiday-peak-hub/issues/110) | Phase 5: Enterprise hardening and observability | ✅ Closed (PR #119) |

---

### 🔵 Background / Superseded Issues

These issues are superseded by the Truth Layer epic or are long-running background features.

| # | Title | Notes |
|---|---|---|
| [#34](https://github.com/Azure-Samples/holiday-peak-hub/issues/34) | Feature: PIM/DAM Agentic Workflow | Superseded by #87 epic |
| [#35](https://github.com/Azure-Samples/holiday-peak-hub/issues/35) | Feature: Retail System Integration Strategy | Background epic, tracked via #36–#84 |

---

## v1.1.0 Summary

### Completed
- **20 PRs merged** (19 feature PRs + 1 CI fix)
- **27 issues closed** across Truth Layer, Connectors, Payment, and Platform Quality workstreams
- **635 tests** passing (249 new tests)
- **4 Enterprise Connectors** production-ready
- **Enterprise Hardening** complete

### In Progress
- **12 Draft PRs** assigned to Copilot agents (Truth Layer Phases 2-5)
- **0 Platform Quality** issues remaining
- **~35 Connector** issues remaining

### Agent Assignment Summary

| Agent | Completed | In Progress | Priority |
|---|---|---|---|
| `Platform_Quality` | 7 (#28, #29, #30, #31, #32, #33, #112) | 0 | ✅ Complete |
| `Truth_Layer_Pipeline` | 12 | 8 (PRs #144-#151, #125-#129) | 🟠 High |
| `Architecture_Patterns` | 5 (#79-#83) | 1 (#84) | 🟡 Medium |
| `Enterprise_Connectors` | 5 | ~35 remaining | 🟡 Low |
| `Truth_Layer_Hardening` | 2 (#107, #110) | 2 (#108, #109) | 🟢 Low / Optional |
