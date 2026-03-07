# Project Status & Issue Prioritization

> Generated: 2026-03-03 | Version: v1.1.0 | Branch: `main`

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
| `ci.yml` | Latest | ✅ Passing | 635 tests passing, all lint checks green |
| `build-push` | Latest | ✅ Passing | Docker images published to GHCR |
| `deploy-azd` | Latest | ✅ Passing | Azure deployment successful |

---

## Closed Issues (Resolved in v1.1.0)

| # | Title | Severity | Category | Status |
|---|---|---|---|---|
| [#25](https://github.com/Azure-Samples/holiday-peak-hub/issues/25) | CRUD service not registered in APIM | Critical | Infrastructure | ✅ Closed |
| [#26](https://github.com/Azure-Samples/holiday-peak-hub/issues/26) | Agent health endpoints return 500 through APIM | Critical | Agents | ✅ Closed |
| [#27](https://github.com/Azure-Samples/holiday-peak-hub/issues/27) | SWA API proxy returns 404 for all /api/* routes | High | Frontend | ✅ Closed |
| [#31](https://github.com/Azure-Samples/holiday-peak-hub/issues/31) | Payment processing fully stubbed | Medium | Backend | ✅ Closed (PR #153, #157) |
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
| [#79](https://github.com/Azure-Samples/holiday-peak-hub/issues/79) | Connector Registry Pattern | Medium | Architecture | ✅ Closed |
| [#80](https://github.com/Azure-Samples/holiday-peak-hub/issues/80) | Event-Driven Connector Sync | Medium | Architecture | ✅ Closed |
| [#81](https://github.com/Azure-Samples/holiday-peak-hub/issues/81) | Multi-Tenant Connector Config | Medium | Architecture | ✅ Closed |
| [#82](https://github.com/Azure-Samples/holiday-peak-hub/issues/82) | Protocol Interface Evolution | Medium | Architecture | ✅ Closed |
| [#83](https://github.com/Azure-Samples/holiday-peak-hub/issues/83) | Internal Data Enrichment Guardrails | Medium | Architecture | ✅ Closed |

---

## Active Pull Requests (In Progress)

### Truth Layer PRs (Assigned to Copilot Agents)
| # | Title | Phase | Status |
|---|-------|-------|--------|
| [#144](https://github.com/Azure-Samples/holiday-peak-hub/pull/144) | Truth Layer Phase 1 Foundation | 1 | 🔄 Draft |
| [#147](https://github.com/Azure-Samples/holiday-peak-hub/pull/147) | TruthStoreAdapter implementation | 1 | 🔄 Draft |
| [#145](https://github.com/Azure-Samples/holiday-peak-hub/pull/145) | Tenant Configuration model | 1 | 🔄 Draft |
| [#148](https://github.com/Azure-Samples/holiday-peak-hub/pull/148) | UCP schema and category schemas | 1 | 🔄 Draft |
| [#150](https://github.com/Azure-Samples/holiday-peak-hub/pull/150) | Event Hub helpers | 1 | 🔄 Draft |
| [#151](https://github.com/Azure-Samples/holiday-peak-hub/pull/151) | Generic REST PIM connector | 2 | 🔄 Draft |
| [#125](https://github.com/Azure-Samples/holiday-peak-hub/pull/125) | Truth Enrichment service | 3 | 🔄 Draft |
| [#126](https://github.com/Azure-Samples/holiday-peak-hub/pull/126) | Truth HITL service | 3 | 🔄 Draft |
| [#128](https://github.com/Azure-Samples/holiday-peak-hub/pull/128) | Truth Export service | 4 | 🔄 Draft |
| [#129](https://github.com/Azure-Samples/holiday-peak-hub/pull/129) | Truth-layer CRUD routes | 4 | 🔄 Draft |
| [#117](https://github.com/Azure-Samples/holiday-peak-hub/pull/117) | Evidence extraction module | 5 | 🔄 Draft |


---

## Open Issues — Prioritization List

Ordered by **review priority** from highest to lowest.

---

### 🔴 Priority 1 — Platform Quality Bugs (agent: `Platform_Quality`)

Remaining quality issues to address.

| # | Title | Severity | Category |
|---|---|---|---|
| [#30](https://github.com/Azure-Samples/holiday-peak-hub/issues/30) | CI agent tests silently swallowed with `\|\| true` | Medium | CI/CD |
| [#29](https://github.com/Azure-Samples/holiday-peak-hub/issues/29) | 10 lib config tests fail due to schema drift | Medium | Testing |
| [#28](https://github.com/Azure-Samples/holiday-peak-hub/issues/28) | Frontend pages use hardcoded mock data instead of API hooks | High | Frontend |
| [#33](https://github.com/Azure-Samples/holiday-peak-hub/issues/33) | No middleware.ts for server-side route protection | Medium | Frontend |
| [#32](https://github.com/Azure-Samples/holiday-peak-hub/issues/32) | Azure AI Search not provisioned — catalog-search agent non-functional | Medium | Infrastructure |
| [#112](https://github.com/Azure-Samples/holiday-peak-hub/issues/112) | docs: Document Entra ID configuration for local and deployed environments | Low | Documentation |

---

### 🟠 Priority 2 — Product Truth Layer: Remaining Phases (agent: `Truth_Layer_Pipeline`)

**Phase 1 Complete** ✅ (PRs #122, #139, #140, #143 merged). Continuing with Phases 2-5.

| # | Title | Phase | Status |
|---|---|---|---|
| [#87](https://github.com/Azure-Samples/holiday-peak-hub/issues/87) | **Epic: Product Truth Layer** | Epic | In Progress |
| [#91](https://github.com/Azure-Samples/holiday-peak-hub/issues/91) | Phase 1: Truth Store Cosmos DB adapter | 1 | PR #147 (Draft) |
| [#92](https://github.com/Azure-Samples/holiday-peak-hub/issues/92) | Phase 1: Tenant Configuration model | 1 | PR #145 (Draft) |
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
- **16 issues closed** (12 Truth Layer, 3 Connectors, 1 Payment)
- **635 tests** passing (249 new tests)
- **4 Enterprise Connectors** production-ready
- **Enterprise Hardening** complete

### In Progress
- **12 Draft PRs** assigned to Copilot agents (Truth Layer Phases 2-5)
- **6 Platform Quality** issues remaining
- **~35 Connector** issues remaining

### Agent Assignment Summary

| Agent | Completed | In Progress | Priority |
|---|---|---|---|
| `Platform_Quality` | 1 (#31) | 6 (#28-#30, #32-#33, #112) | 🔴 Review First |
| `Truth_Layer_Pipeline` | 12 | 8 (PRs #144-#151, #125-#129) | 🟠 High |
| `Architecture_Patterns` | 5 (#79-#83) | 1 (#84) | 🟡 Medium |
| `Enterprise_Connectors` | 5 | ~35 remaining | 🟡 Low |
| `Truth_Layer_Hardening` | 2 (#107, #110) | 2 (#108, #109) | 🟢 Low / Optional |
