# Project Status & Issue Prioritization

> Generated: 2026-03-03 | Branch: `main` @ `be224bfd`

---

## CI/CD Status

### Failed Job (Root Cause + Fix)

| Workflow | Run | Job | Conclusion | Root Cause |
|---|---|---|---|---|
| `build-push` | [#43](https://github.com/Azure-Samples/holiday-peak-hub/actions/runs/22599442813) | `build` | ❌ failure | `for d in apps/*` iterated over `apps/README.md`, causing `docker build` to fail with `invalid tag "ghcr.io/Azure-Samples/README.md:latest"` |
| `build-push` | [#43](https://github.com/Azure-Samples/holiday-peak-hub/actions/runs/22599442813) | `push` | ⏭ skipped | Skipped because `build` job failed |

**Fix applied** (this PR): Added `[ -d "$d" ] || continue` guard in both `build` and `push` jobs inside `.github/workflows/ci.yml` so non-directory entries (like `apps/README.md`) are skipped.

Once this PR merges to `main` the next push will re-run both jobs successfully.

---

## Closed Issues (Resolved — Review for Completeness)

| # | Title | Severity | Category | Status |
|---|---|---|---|---|
| [#25](https://github.com/Azure-Samples/holiday-peak-hub/issues/25) | CRUD service not registered in APIM — all frontend API calls fail | Critical | Infrastructure | ✅ Closed |
| [#26](https://github.com/Azure-Samples/holiday-peak-hub/issues/26) | Agent health endpoints return 500 through APIM | Critical | Agents | ✅ Closed |
| [#27](https://github.com/Azure-Samples/holiday-peak-hub/issues/27) | SWA API proxy returns 404 for all /api/* routes | High | Frontend | ✅ Closed |

---

## Closed Pull Requests (Merged — Review for Follow-Up)

| # | Title | Merged | Notes |
|---|---|---|---|
| [#114](https://github.com/Azure-Samples/holiday-peak-hub/pull/114) | feat: Seed full demo catalog — users, orders, shipments, reviews, tickets, returns | 2026-03-02 | All 8 CRUD tables seeded; 386 tests passing |

---

## Open Pull Requests

| # | Title | State | Agent |
|---|---|---|---|
| [#161](https://github.com/Azure-Samples/holiday-peak-hub/pull/161) | Review and restart failed job executions | 🔄 Draft | Copilot |

---

## Open Issues — Prioritization List

Ordered by **review priority** from highest to lowest.

---

### 🔴 Priority 1 — Platform Quality Bugs (agent: `Platform_Quality`)

These are blocking stable CI and platform operation. Review and merge agent output first.

| # | Title | Severity | Category |
|---|---|---|---|
| [#30](https://github.com/Azure-Samples/holiday-peak-hub/issues/30) | CI agent tests silently swallowed with `\|\| true` | Medium | CI/CD |
| [#29](https://github.com/Azure-Samples/holiday-peak-hub/issues/29) | 10 lib config tests fail due to schema drift | Medium | Testing |
| [#28](https://github.com/Azure-Samples/holiday-peak-hub/issues/28) | Frontend pages use hardcoded mock data instead of API hooks | High | Frontend |
| [#33](https://github.com/Azure-Samples/holiday-peak-hub/issues/33) | No middleware.ts for server-side route protection | Medium | Frontend |
| [#32](https://github.com/Azure-Samples/holiday-peak-hub/issues/32) | Azure AI Search not provisioned — catalog-search agent non-functional | Medium | Infrastructure |
| [#31](https://github.com/Azure-Samples/holiday-peak-hub/issues/31) | Payment processing fully stubbed (backend + frontend) | Medium | Backend |
| [#112](https://github.com/Azure-Samples/holiday-peak-hub/issues/112) | docs: Document Entra ID configuration for local and deployed environments | Low | Documentation |

---

### 🔴 Priority 2 — Product Truth Layer: Phase 1 Foundation (agent: `Truth_Layer_Foundation`)

These are marked `priority: critical` and block all subsequent Truth Layer phases. Must complete before Phase 2 begins.

| # | Title | Phase |
|---|---|---|
| [#87](https://github.com/Azure-Samples/holiday-peak-hub/issues/87) | **Epic: Product Truth Layer — Agent-Ready Catalog Enrichment + Knowledge Graph** | Epic |
| [#88](https://github.com/Azure-Samples/holiday-peak-hub/issues/88) | Phase 1: Cosmos DB containers (9 containers for Product Graph) | 1 |
| [#89](https://github.com/Azure-Samples/holiday-peak-hub/issues/89) | Phase 1: Event Hub topics (5 job topics) | 1 |
| [#90](https://github.com/Azure-Samples/holiday-peak-hub/issues/90) | Phase 1: Product Graph data models | 1 |
| [#91](https://github.com/Azure-Samples/holiday-peak-hub/issues/91) | Phase 1: Truth Store Cosmos DB adapter | 1 |
| [#92](https://github.com/Azure-Samples/holiday-peak-hub/issues/92) | Phase 1: Tenant Configuration model | 1 |
| [#93](https://github.com/Azure-Samples/holiday-peak-hub/issues/93) | Phase 1: UCP schema and canonical category schemas | 1 |
| [#94](https://github.com/Azure-Samples/holiday-peak-hub/issues/94) | Phase 1: Event Hub helpers for truth-layer jobs | 1 |
| [#95](https://github.com/Azure-Samples/holiday-peak-hub/issues/95) | Phase 1: Extend TruthLayerSettings in config/settings.py | 1 |

---

### 🟠 Priority 3 — Product Truth Layer: Phases 2–4 Pipeline (agent: `Truth_Layer_Pipeline`)

Marked `priority: high`. Depends on Phase 1 completing first.

| # | Title | Phase |
|---|---|---|
| [#96](https://github.com/Azure-Samples/holiday-peak-hub/issues/96) | Phase 2: Generic REST PIM connector | 2 |
| [#97](https://github.com/Azure-Samples/holiday-peak-hub/issues/97) | Phase 2: Generic DAM connector | 2 |
| [#98](https://github.com/Azure-Samples/holiday-peak-hub/issues/98) | Phase 2: Truth Ingestion service | 2 |
| [#99](https://github.com/Azure-Samples/holiday-peak-hub/issues/99) | Phase 2: Completeness Engine refactor (consistency-validation) | 2 |
| [#100](https://github.com/Azure-Samples/holiday-peak-hub/issues/100) | Phase 2: Sample data and seed scripts | 2 |
| [#101](https://github.com/Azure-Samples/holiday-peak-hub/issues/101) | Phase 3: Truth Enrichment service | 3 |
| [#102](https://github.com/Azure-Samples/holiday-peak-hub/issues/102) | Phase 3: Truth HITL service (Human-in-the-Loop) | 3 |
| [#103](https://github.com/Azure-Samples/holiday-peak-hub/issues/103) | Phase 3: HITL Staff Review UI pages | 3 |
| [#104](https://github.com/Azure-Samples/holiday-peak-hub/issues/104) | Phase 4: Truth Export service and Protocol Mappers | 4 |
| [#105](https://github.com/Azure-Samples/holiday-peak-hub/issues/105) | Phase 4: CRUD service truth-layer routes (6 new route modules) | 4 |
| [#106](https://github.com/Azure-Samples/holiday-peak-hub/issues/106) | Phase 4: Postman collection and API documentation | 4 |

---

### 🟡 Priority 4 — Architecture Patterns (agent: `Architecture_Patterns`)

Marked `priority: medium`. Can proceed in parallel with Truth Layer work.

| # | Title |
|---|---|
| [#79](https://github.com/Azure-Samples/holiday-peak-hub/issues/79) | Architecture: Connector Registry Pattern |
| [#80](https://github.com/Azure-Samples/holiday-peak-hub/issues/80) | Architecture: Event-Driven Sync Pattern |
| [#81](https://github.com/Azure-Samples/holiday-peak-hub/issues/81) | Architecture: Multi-Tenant Configuration |
| [#82](https://github.com/Azure-Samples/holiday-peak-hub/issues/82) | Architecture: Protocol Evolution |
| [#83](https://github.com/Azure-Samples/holiday-peak-hub/issues/83) | Architecture: Data Guardrails |
| [#84](https://github.com/Azure-Samples/holiday-peak-hub/issues/84) | Architecture: Reference Architecture Patterns |

---

### 🟡 Priority 5 — Enterprise Connectors (agent: `Enterprise_Connectors`)

Marked `priority: low` (most are not blocking v0). 43 connectors across 10 platform categories. Note: #36 (PIM) and #37 (DAM) are superseded by #96 and #97 in the Truth Layer pipeline.

#### Inventory & SCM
| # | Connector |
|---|---|
| [#36](https://github.com/Azure-Samples/holiday-peak-hub/issues/36) | SAP S/4HANA |
| [#37](https://github.com/Azure-Samples/holiday-peak-hub/issues/37) | Oracle NetSuite |
| [#38](https://github.com/Azure-Samples/holiday-peak-hub/issues/38) | Manhattan WMS |
| [#39](https://github.com/Azure-Samples/holiday-peak-hub/issues/39) | Blue Yonder / JDA |

#### CRM
| # | Connector |
|---|---|
| [#40](https://github.com/Azure-Samples/holiday-peak-hub/issues/40) | Salesforce CRM |
| [#41](https://github.com/Azure-Samples/holiday-peak-hub/issues/41) | Microsoft Dynamics 365 |
| [#42](https://github.com/Azure-Samples/holiday-peak-hub/issues/42) | HubSpot |
| [#43](https://github.com/Azure-Samples/holiday-peak-hub/issues/43) | Adobe Experience Manager |

#### Commerce
| # | Connector |
|---|---|
| [#44](https://github.com/Azure-Samples/holiday-peak-hub/issues/44) | Shopify |
| [#45](https://github.com/Azure-Samples/holiday-peak-hub/issues/45) | Magento / Adobe Commerce |
| [#46](https://github.com/Azure-Samples/holiday-peak-hub/issues/46) | Commercetools |
| [#47](https://github.com/Azure-Samples/holiday-peak-hub/issues/47) | BigCommerce |

#### PIM / DAM
| # | Connector |
|---|---|
| [#48](https://github.com/Azure-Samples/holiday-peak-hub/issues/48) | Akeneo PIM |
| [#49](https://github.com/Azure-Samples/holiday-peak-hub/issues/49) | inRiver PIM |
| [#50](https://github.com/Azure-Samples/holiday-peak-hub/issues/50) | Salsify |
| [#51](https://github.com/Azure-Samples/holiday-peak-hub/issues/51) | Bynder DAM |
| [#52](https://github.com/Azure-Samples/holiday-peak-hub/issues/52) | Cloudinary DAM |

#### Data & Analytics
| # | Connector |
|---|---|
| [#53](https://github.com/Azure-Samples/holiday-peak-hub/issues/53) | Snowflake |
| [#54](https://github.com/Azure-Samples/holiday-peak-hub/issues/54) | Databricks |
| [#55](https://github.com/Azure-Samples/holiday-peak-hub/issues/55) | Google BigQuery |

#### Integration / Middleware
| # | Connector |
|---|---|
| [#56](https://github.com/Azure-Samples/holiday-peak-hub/issues/56) | MuleSoft Anypoint |
| [#57](https://github.com/Azure-Samples/holiday-peak-hub/issues/57) | Dell Boomi |
| [#58](https://github.com/Azure-Samples/holiday-peak-hub/issues/58) | Informatica |
| [#59](https://github.com/Azure-Samples/holiday-peak-hub/issues/59) | Talend |

#### Workforce
| # | Connector |
|---|---|
| [#60](https://github.com/Azure-Samples/holiday-peak-hub/issues/60) | Workday HCM |
| [#61](https://github.com/Azure-Samples/holiday-peak-hub/issues/61) | ADP Workforce |
| [#62](https://github.com/Azure-Samples/holiday-peak-hub/issues/62) | SAP SuccessFactors |

#### Identity
| # | Connector |
|---|---|
| [#63](https://github.com/Azure-Samples/holiday-peak-hub/issues/63) | Okta Identity |
| [#64](https://github.com/Azure-Samples/holiday-peak-hub/issues/64) | Azure Active Directory (Entra) |
| [#65](https://github.com/Azure-Samples/holiday-peak-hub/issues/65) | Ping Identity |

#### Additional Enterprise Connectors
| # | Connector |
|---|---|
| [#66](https://github.com/Azure-Samples/holiday-peak-hub/issues/66) | Zendesk (Support) |
| [#67](https://github.com/Azure-Samples/holiday-peak-hub/issues/67) | ServiceNow |
| [#68](https://github.com/Azure-Samples/holiday-peak-hub/issues/68) | Twilio (Communications) |
| [#69](https://github.com/Azure-Samples/holiday-peak-hub/issues/69) | Klaviyo (Marketing) |
| [#70](https://github.com/Azure-Samples/holiday-peak-hub/issues/70) | OneTrust (Privacy) |
| [#71](https://github.com/Azure-Samples/holiday-peak-hub/issues/71) | Stripe (Payments) |
| [#72](https://github.com/Azure-Samples/holiday-peak-hub/issues/72) | Braintree (Payments) |
| [#73](https://github.com/Azure-Samples/holiday-peak-hub/issues/73) | Narvar (Post-Purchase) |
| [#74](https://github.com/Azure-Samples/holiday-peak-hub/issues/74) | Loop Returns |
| [#75](https://github.com/Azure-Samples/holiday-peak-hub/issues/75) | Returnly |
| [#76](https://github.com/Azure-Samples/holiday-peak-hub/issues/76) | Avalara (Tax) |
| [#77](https://github.com/Azure-Samples/holiday-peak-hub/issues/77) | Vertex (Tax) |
| [#78](https://github.com/Azure-Samples/holiday-peak-hub/issues/78) | FreightQuote / EasyPost (Shipping) |

---

### 🟢 Priority 6 — Product Truth Layer: Phase 5 Hardening (agent: `Truth_Layer_Hardening`)

Marked `priority: low`. Optional modules and polish — do after all higher-priority work is complete.

| # | Title |
|---|---|
| [#107](https://github.com/Azure-Samples/holiday-peak-hub/issues/107) | Phase 5: PIM writeback module (opt-in) |
| [#108](https://github.com/Azure-Samples/holiday-peak-hub/issues/108) | Phase 5: Evidence extraction for AI enrichments |
| [#109](https://github.com/Azure-Samples/holiday-peak-hub/issues/109) | Phase 5: Admin UI pages (schemas, config, analytics) |
| [#110](https://github.com/Azure-Samples/holiday-peak-hub/issues/110) | Phase 5: Enterprise hardening and observability |

---

### 🔵 Background / Superseded Issues

These issues are superseded by the Truth Layer epic or are long-running background features.

| # | Title | Notes |
|---|---|---|
| [#34](https://github.com/Azure-Samples/holiday-peak-hub/issues/34) | Feature: PIM/DAM Agentic Workflow — Product Graph + Digital Asset Management | Superseded by #87 epic |
| [#35](https://github.com/Azure-Samples/holiday-peak-hub/issues/35) | Feature: Retail System Integration Strategy | Background epic, tracked via #36–#84 |

---

## Agent Assignment Summary

| Agent | Issues | Priority |
|---|---|---|
| `Platform_Quality` | #28–#33, #112 | 🔴 Review First |
| `Truth_Layer_Foundation` | #87–#95 | 🔴 Critical |
| `Truth_Layer_Pipeline` | #96–#106 | 🟠 High |
| `Architecture_Patterns` | #79–#84 | 🟡 Medium |
| `Enterprise_Connectors` | #36–#78 | 🟡 Low |
| `Truth_Layer_Hardening` | #107–#110 | 🟢 Low / Optional |
