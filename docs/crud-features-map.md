# CRUD Service Features Map — Gap Analysis & Roadmap

> **Generated**: 2026-02-28  
> **Scope**: All 21 agent apps, shared lib schemas, 59 open issues  
> **Purpose**: Document every capability gap between the CRUD service and the agent ecosystem, propose new Postgres models, adapter integrations, and issues for feature parity.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current CRUD Service Inventory](#2-current-crud-service-inventory)
3. [Lib Schema Inventory — Agent Data Models](#3-lib-schema-inventory--agent-data-models)
4. [Domain-by-Domain Gap Analysis](#4-domain-by-domain-gap-analysis)
   - 4.1 [Products & Catalog](#41-products--catalog)
   - 4.2 [Inventory & Warehouse](#42-inventory--warehouse)
   - 4.3 [CRM — Contacts, Accounts, Interactions](#43-crm--contacts-accounts-interactions)
   - 4.4 [Logistics & Shipments](#44-logistics--shipments)
   - 4.5 [Pricing](#45-pricing)
   - 4.6 [Funnel & Campaign Analytics](#46-funnel--campaign-analytics)
   - 4.7 [Payments & Checkout](#47-payments--checkout)
   - 4.8 [Support Tickets & Returns](#48-support-tickets--returns)
   - 4.9 [Product Management (PIM/DAM)](#49-product-management-pimdam)
5. [New Postgres Tables Required](#5-new-postgres-tables-required)
6. [New Adapters Required (lib & CRUD)](#6-new-adapters-required-lib--crud)
7. [New Agents to Consider](#7-new-agents-to-consider)
8. [BaseCRUDAdapter MCP Tool Gaps](#8-basecrudadapter-mcp-tool-gaps)
9. [AgentClient Method Gaps](#9-agentclient-method-gaps)
10. [Event Hub Coverage Gaps](#10-event-hub-coverage-gaps)
11. [Schema Mismatches & Field Mapping Issues](#11-schema-mismatches--field-mapping-issues)
12. [Proposed Issues](#12-proposed-issues)
13. [Appendix — Open Issues Reference](#13-appendix--open-issues-reference)
14. [Enterprise API Schema Grounding](#14-enterprise-api-schema-grounding)
    - 14.1 [Methodology & Sources](#141-methodology--sources)
    - 14.2 [Product & Catalog — Enterprise Comparison](#142-product--catalog--enterprise-comparison)
    - 14.3 [Inventory & Warehouse — Enterprise Comparison](#143-inventory--warehouse--enterprise-comparison)
    - 14.4 [Customer & CRM — Enterprise Comparison](#144-customer--crm--enterprise-comparison)
    - 14.5 [Pricing — Enterprise Comparison](#145-pricing--enterprise-comparison)
    - 14.6 [Orders — Enterprise Comparison](#146-orders--enterprise-comparison)
    - 14.7 [Logistics & Shipments — Enterprise Comparison](#147-logistics--shipments--enterprise-comparison)
    - 14.8 [PIM & DAM — Enterprise Comparison](#148-pim--dam--enterprise-comparison)
    - 14.9 [Cross-Platform Convergence Summary](#149-cross-platform-convergence-summary)
    - 14.10 [Recommended Schema Additions](#1410-recommended-schema-additions)

---

## 1. Executive Summary

The CRUD service currently manages **11 JSONB-backed Postgres tables** and exposes **36 REST endpoints**. However, the 21 agent services operate on **6 domain connector types** (CRM, Product, Inventory, Logistics, Pricing, Funnel) backed by **mock adapters only**. The enterprise integration contracts define **8 additional connector ABCs** (PIM, DAM, Commerce, Analytics, Integration, Identity, Workforce, CRM-enterprise). There are **59 open issues** spanning infrastructure bugs, connector requests, and architecture enhancements.

### Key Findings

| Category | Gap Severity | Summary |
|----------|-------------|---------|
| **Inventory** | **Critical** | No dedicated inventory table/endpoints. All 4 inventory agents rely on mocks. |
| **CRM** | **Critical** | No contacts, accounts, or interactions tables. All 4 CRM agents use mocks. |
| **Pricing** | **High** | No pricing table. Checkout and cart agents can't resolve real prices. |
| **Logistics** | **High** | Shipment table is read-only. No write path for agent-produced tracking data. |
| **Funnel/Campaign** | **High** | No campaign or funnel tables. Campaign intelligence agent fully mocked. |
| **Product Management** | **High** | No CRUD integration for any of the 4 product-management agents. |
| **Payments** | **Medium** | Payment processing persists API-created payment records and `GET /api/payments/{id}` now supports role/ownership checks. Refund/history gaps remain. |
| **Tickets** | **Medium** | Staff/admin ticket lifecycle is mutable (`create`, `update`, `resolve`, `escalate`) with audit metadata. Customer-facing creation remains a gap. |
| **PIM/DAM** | **Medium** | Issue #34 proposes a full Product Graph + DAM workflow — no CRUD models exist. |
| **Schema alignment** | **Medium** | `id` vs `sku`, `name` vs `title`, `category_id` vs `category` mismatches throughout. |

---

## 2. Current CRUD Service Inventory

### 2.1 Postgres Tables (JSONB-backed)

All tables share the universal schema: `(id TEXT PK, partition_key TEXT, data JSONB, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`.

| Table | Repository | CRUD Endpoints | Write Ops |
|-------|-----------|---------------|-----------|
| `products` | `ProductRepository` | `GET /api/products`, `GET /api/products/{id}`, `POST /api/products/{id}/trigger-enrichment` | Seed + enrichment trigger |
| `users` | `UserRepository` | `GET /api/users/me`, `PATCH /api/users/me` | Auto-create from JWT |
| `cart` | `CartRepository` | `GET /api/cart`, `POST /api/cart/items`, `DELETE /api/cart/items/{id}`, `DELETE /api/cart` | Full CRUD |
| `orders` | `OrderRepository` | `GET /api/orders`, `GET /api/orders/{id}`, `POST /api/orders`, `PATCH /api/orders/{id}/cancel` | Create + Cancel |
| `checkout_sessions` | `CheckoutSessionRepository` | `POST /acp/checkout/sessions`, `GET .../{id}`, `PATCH .../{id}`, `POST .../complete`, `DELETE .../{id}` | Full CRUD |
| `payment_tokens` | `PaymentTokenRepository` | `POST /acp/payments/delegate` | Create only |
| `categories` | Inline `CategoryRepository` | `GET /api/categories`, `GET /api/categories/{id}` | Seed only |
| `reviews` | Inline `ReviewRepository` | `GET /api/reviews`, `POST /api/reviews`, `DELETE /api/reviews/{id}` | Create + Delete |
| `tickets` | Inline `TicketRepository` | `GET /api/staff/tickets`, `GET /api/staff/tickets/{id}`, `POST /api/staff/tickets`, `PATCH /api/staff/tickets/{id}`, `POST /api/staff/tickets/{id}/resolve`, `POST /api/staff/tickets/{id}/escalate` | Create + Update + Resolve + Escalate |
| `returns` | Inline `ReturnRepository` | `GET /api/staff/returns`, `PATCH /api/staff/returns/{id}/approve` | Approve only |
| `shipments` | Inline `ShipmentRepository` | `GET /api/staff/shipments`, `GET /api/staff/shipments/{id}` | **Read-only** |
| `brand_shopping` | `ProductRepository` + `UserRepository` + `AgentClient` | `GET /api/catalog/products/{sku}`, `GET /api/customers/{customer_id}/profile`, `POST /api/pricing/offers`, `POST /api/recommendations/rank`, `POST /api/recommendations/compose` | Contract-only, additive |

### 2.2 Agent Integrations (via `AgentClient`)

| AgentClient Method | Target Agent | CRUD Route That Calls It |
|---|---|---|
| `semantic_search()` | ecommerce-catalog-search | `GET /products` (search fallback) |
| `get_user_recommendations()` | ecommerce-cart-intelligence | `GET /cart/recommendations` |
| `get_product_enrichment()` | ecommerce-product-detail-enrichment | `GET /products/{id}` |
| `calculate_dynamic_pricing()` | ecommerce-checkout-support | `GET /products/{id}` |
| `get_inventory_status()` | inventory-health-check | `POST /checkout/validate` |
| `validate_reservation()` | inventory-reservation-validation | `POST /cart/items` |
| `get_order_status()` | ecommerce-order-status | `GET /orders/{id}` |
| `get_delivery_eta()` | logistics-eta-computation | `GET /orders/{id}` |
| `get_carrier_recommendation()` | logistics-carrier-selection | `GET /orders/{id}` |
| `get_return_plan()` | logistics-returns-support | `GET /orders/{id}/returns` |
| `get_customer_profile()` | crm-profile-aggregation | `GET /users/me/crm` |
| `get_personalization()` | crm-segmentation-personalization | `GET /users/me/crm` |

**Missing integrations** (agents with no `AgentClient` method):
- `crm-campaign-intelligence`
- `crm-support-assistance`
- `inventory-alerts-triggers`
- `inventory-jit-replenishment`
- `logistics-route-issue-detection`
- `product-management-acp-transformation` (all 4 product-management agents)
- `product-management-assortment-optimization`
- `product-management-consistency-validation`
- `product-management-normalization-classification`

---

## 3. Lib Schema Inventory — Agent Data Models

These are the Pydantic models agents consume/produce. If a model has no CRUD backing, agents rely on mock adapters.

### 3.1 Domain Connector Models

| Domain | Models | CRUD Backing? |
|--------|--------|--------------|
| **Product** | `CatalogProduct` (sku, name, description, brand, category, price, currency, image_url, rating, tags, attributes, variants), `ProductContext` | Partial — CRUD `ProductResponse` lacks brand, currency, tags, attributes, variants |
| **Inventory** | `InventoryItem` (sku, available, reserved, backorder_date, safety_stock, lead_time_days, status, attributes), `WarehouseStock` (warehouse_id, available, reserved, location, updated_at), `InventoryContext` | **None** — No inventory table |
| **CRM** | `CRMContact` (13 fields), `CRMAccount` (8 fields), `CRMInteraction` (11 fields), `CRMContext` | **None** — No CRM tables |
| **Logistics** | `Shipment` (11 fields), `ShipmentEvent` (5 fields), `LogisticsContext` | **Partial** — Shipment table exists (read-only), no events table |
| **Pricing** | `PriceEntry` (12 fields), `PriceContext` | **None** — No pricing table |
| **Funnel** | `FunnelMetric` (6 fields), `FunnelContext` | **None** — No funnel/campaign tables |

### 3.2 Enterprise Integration Contracts (ABCs — No Implementations)

| Contract | Entity Types | Relevant Connector Issues |
|----------|-------------|--------------------------|
| `PIMConnectorBase` | `ProductData`, `AssetData` | #46-49, #74-75 (Salsify, inRiver, Akeneo, Pimcore, SAP Hybris, Informatica) |
| `DAMConnectorBase` | `AssetData` | #50-52, #76 (Cloudinary, Adobe AEM, Bynder, Sitecore) |
| `InventoryConnectorBase` | `InventoryData` | #36-40, #77 (SAP, Oracle, Manhattan, Blue Yonder, Dynamics 365, Infor) |
| `CRMConnectorBase` | `CustomerData`, `SegmentData`, `OrderData` | #41-45, #78 (Salesforce, Dynamics 365, Adobe, Braze, Twilio, Oracle CX) |
| `CommerceConnectorBase` | `OrderData`, `ProductData` | #53-59 (Shopify, commercetools, Salesforce CC, Adobe/Magento, SAP CC, Manhattan OMS, VTEX) |
| `AnalyticsConnectorBase` | Raw dicts | #60-64 (Synapse, Snowflake, Databricks, GA4, Adobe Analytics) |
| `IntegrationConnectorBase` | Raw dicts | #65-68 (MuleSoft, Kafka, Boomi, IBM Sterling) |
| `IdentityConnectorBase` | Raw dicts | #69 (Okta/Auth0) |
| `WorkforceConnectorBase` | Raw dicts | #71-73 (UKG/Kronos, Zebra Reflexis, WorkJam/Yoobic) |

---

## 4. Domain-by-Domain Gap Analysis

### 4.1 Products & Catalog

**Agents that consume product data**: ecommerce-catalog-search, ecommerce-product-detail-enrichment, ecommerce-cart-intelligence, ecommerce-checkout-support, all 4 product-management agents (8 agents total).

#### Field Mapping: CRUD `ProductResponse` vs Lib `CatalogProduct`

| Field | CRUD `ProductResponse` | Lib `CatalogProduct` | Status |
|-------|----------------------|---------------------|--------|
| `id` / `sku` | `id: str` | `sku: str` | **Mismatch** — different field names |
| `name` / `title` | `name: str` | `name: str` | Match |
| `description` | `description: str` | `description: Optional[str]` | Match |
| `price` | `price: float` | `price: Optional[float]` | Match (type differs slightly) |
| `category_id` / `category` | `category_id: str` | `category: Optional[str]` | **Mismatch** — FK vs string |
| `image_url` | `image_url: str?` | `image_url: Optional[str]` | Match |
| `in_stock` | `in_stock: bool` | — | **Missing from CatalogProduct** |
| `rating` | `rating: float?` | `rating: Optional[float]` | Match |
| `review_count` | `review_count: int?` | — | **Missing from CatalogProduct** |
| `features` | `features: list[str]?` | — | **Missing from CatalogProduct** (goes in attributes) |
| `media` | `media: list[dict]?` | — | **Missing from CatalogProduct** |
| `inventory` | `inventory: dict?` | — | **Missing from CatalogProduct** (separate schema) |
| `related` | `related: list[dict]?` | — | **Missing from CatalogProduct** (in ProductContext) |
| `brand` | — | `brand: Optional[str]` | **Missing from ProductResponse** |
| `currency` | — | `currency: Optional[str]` | **Missing from ProductResponse** |
| `tags` | — | `tags: list[str]` | **Missing from ProductResponse** |
| `attributes` | — | `attributes: dict` | **Missing from ProductResponse** |
| `variants` | — | `variants: list[dict]` | **Missing from ProductResponse** |

#### ACP Format Mismatch

The catalog-search agent returns ACP-formatted products with `item_id`, `title`, `price` as string ("10.00 usd"). CRUD's product list route passes these directly to `ProductResponse` validation, which expects `id`, `name`, `price: float`. This will fail Pydantic validation.

#### Gaps

1. **ProductResponse missing 5 fields**: `brand`, `currency`, `tags`, `attributes`, `variants`
2. **Seed data is minimal**: Only `id`, `name`, `description`, `price`, `category_id`, `image_url`, `in_stock` are seeded. No `brand`, `currency`, `tags`, `attributes`, `variants`.
3. **No product write endpoints**: No `POST /api/products` or `PATCH /api/products/{id}` — products are seed-only.
4. **No product event publishing**: Product CRUD changes don't publish to `product-events` Event Hub. All 4 product-management agents subscribe to `product-events` but nothing publishes to it.
5. **ACP search results require mapping layer** before CRUD can serve them.

---

### 4.2 Inventory & Warehouse

**Agents that consume inventory data**: inventory-alerts-triggers, inventory-health-check, inventory-jit-replenishment, inventory-reservation-validation, ecommerce-cart-intelligence, ecommerce-checkout-support (6 agents).

#### What Agents Need

| Entity | Fields Required | CRUD Has? |
|--------|----------------|-----------|
| `InventoryItem` | sku, available, reserved, backorder_date, safety_stock, lead_time_days, status, attributes | **No** — Only `in_stock: bool` on products |
| `WarehouseStock` | warehouse_id, sku, available, reserved, location, updated_at | **No** |
| Reservation ledger | reservation_id, sku, qty, approved, expires_at | **No** |

#### Gaps

1. **No `inventory` table** — Critical. All 4 inventory agents are non-functional with real data.
2. **No `warehouse_stock` table** — health-check agent flags `"no_warehouse_stock"` but there's no source.
3. **No inventory CRUD endpoints** — No `GET/POST/PATCH /api/inventory/{sku}`.
4. **No reservation persistence** — Reservation validation is ephemeral.
5. **`BaseCRUDAdapter._get_inventory()` fallback is broken** — reads product's `.inventory` sub-field which is only populated by agent enrichment, not stored natively.
6. **Reservation field name mismatch** — Agent returns `approved`, CRUD cart route checks for `valid`.
7. **No inventory event publishing from CRUD** — `publish_inventory_reserved()` method exists but is never called.
8. **No alerts/replenishment agent URL settings in CRUD** — Only `inventory_health_agent_url` and `inventory_reservation_agent_url` exist.

---

### 4.3 CRM — Contacts, Accounts, Interactions

**Agents that consume CRM data**: crm-campaign-intelligence, crm-profile-aggregation, crm-segmentation-personalization, crm-support-assistance (4 agents).

#### What Agents Need

| Entity | Fields | CRUD Has? |
|--------|--------|-----------|
| `CRMContact` | contact_id, account_id, email, phone, locale, timezone, marketing_opt_in, first_name, last_name, title, tags, preferences, attributes | **No** |
| `CRMAccount` | account_id, name, region, owner, industry, tier, lifecycle_stage, attributes | **No** |
| `CRMInteraction` | interaction_id, contact_id, account_id, channel, occurred_at, duration_seconds, outcome, subject, summary, sentiment, metadata | **No** |

The CRUD `users` table stores: `id, email, name, phone, entra_id, created_at` — a flat user profile with no CRM-level data (accounts, interactions, marketing preferences, segments, lifecycle stages).

#### Gaps

1. **No CRM tables at all** — This is the biggest gap for CRM agents.
2. **User ↔ Contact mapping is implicit** — `AgentClient` passes `user_id` as `contact_id` with no formal mapping.
3. **No account entity** — B2B scenarios (tiers, industries, lifecycle stages) have no backing store.
4. **No interaction history** — Agents can't retrieve real interaction data for sentiment, support briefs, or segmentation.
5. **No agent URL settings for campaign and support agents** — Only `crm_profile_agent_url` and `crm_segmentation_agent_url` exist.
6. **No persistence for agent enrichments** — Segments, engagement scores, personalization rules, support briefs, campaign ROI are all transient.

---

### 4.4 Logistics & Shipments

**Agents that consume logistics data**: logistics-carrier-selection, logistics-eta-computation, logistics-returns-support, logistics-route-issue-detection, ecommerce-order-status (5 agents).

#### What Agents Need

| Entity | Fields | CRUD Has? |
|--------|--------|-----------|
| `Shipment` | tracking_id, order_id, carrier, status, eta, last_updated, origin, destination, service_level, weight_kg, attributes | **Partial** — read-only shipments table with fewer fields |
| `ShipmentEvent` | code, description, occurred_at, location, metadata | **No** |

#### CRUD Shipment Model (current)

| Field | In CRUD | In Lib `Shipment` |
|-------|---------|-------------------|
| `id` | Yes | `tracking_id` |
| `order_id` | Yes | Yes |
| `status` | Yes | Yes |
| `carrier` | Yes | Yes |
| `tracking_number` | Yes | — (uses `tracking_id`) |
| `created_at` | Yes | — |
| `eta` | — | Yes |
| `last_updated` | — | Yes |
| `origin` | — | Yes |
| `destination` | — | Yes |
| `service_level` | — | Yes |
| `weight_kg` | — | Yes |
| `attributes` | — | Yes |

#### Gaps

1. **Shipment table is read-only** — No `POST` or `PATCH` endpoints. Agents can't write back carrier recommendations, ETAs, or issue detections.
2. **No shipment events table** — `ShipmentEvent` (tracking milestones) has no persistence.
3. **No `ShipmentEvent` endpoints** — For real-time tracking visibility.
4. **Shipment fields missing**: `eta`, `origin`, `destination`, `service_level`, `weight_kg`.
5. **`OrderTrackingResolver` in order-status agent is a stub** — Returns `T-{order_id}` instead of looking up real tracking data.
6. **No logistics agent subscribes to `shipment-events`** — All subscribe to `order-events` only.
7. **`logistics-route-issue-detection` completely disconnected** — No `AgentClient` method, no settings URL, no CRUD route consumes it.
8. **No shipment MCP tools in `BaseCRUDAdapter`** — Agents can't read shipments via MCP.
9. **No customer-facing returns creation** — `POST /api/orders/{id}/returns` doesn't exist. Returns agent's plans are not actionable.

---

### 4.5 Pricing

**Agents that consume pricing data**: ecommerce-cart-intelligence, ecommerce-checkout-support (2 agents).

#### What Agents Need

| Entity | Fields | CRUD Has? |
|--------|--------|-----------|
| `PriceEntry` | sku, currency, amount, list_amount, discount_code, channel, region, tax_included, promotional, effective_from, effective_to, attributes | **No** |
| `PriceContext` | sku, active (PriceEntry), offers (list[PriceEntry]) | **No** |

CRUD stores `price: float` directly on the product document. There is no price history, promotional pricing, currency support, regional pricing, or discount management.

#### Gaps

1. **No pricing table** — Agents can't resolve real dynamic prices, promotional offers, or multi-currency amounts.
2. **No pricing CRUD endpoints** — No `GET/POST/PATCH /api/pricing/{sku}`.
3. **Hardcoded shipping & tax** — Checkout uses hardcoded `$9.99` shipping and `8%` tax.
4. **No discount/coupon system** — `PriceEntry.discount_code` has no backing infrastructure.

---

### 4.6 Funnel & Campaign Analytics

**Agents that consume funnel data**: crm-campaign-intelligence (1 agent).

#### What Agents Need

| Entity | Fields | CRUD Has? |
|--------|--------|-----------|
| `FunnelMetric` | stage, count, conversion_rate, channel, stage_time_ms, attributes | **No** |
| `FunnelContext` | campaign_id, account_id, metrics, updated_at | **No** |
| Campaign metadata | campaign_id, name, status, spend, budget, start_date, end_date | **No** |

#### Gaps

1. **No campaign table** — Campaign intelligence agent is fully mocked.
2. **No funnel metrics table** — No conversion funnel tracking.
3. **Staff analytics endpoint returns zeros** — `GET /api/staff/analytics/summary` is a stub.
4. **No campaign ROI persistence** — Agent computes ROI but results are discarded.

---

### 4.7 Payments & Checkout

**Relevant issues**: #31 (payments stubbed).

#### Gaps

1. **Payment processing is simulated** — `stripe` SDK listed but never imported/used.
2. **`GET /api/payments/{id}` ownership model is strict** — Customer can only read own payment; staff/admin can read any.
3. **`PaymentMethodRepository` is an empty class** — `pass` only.
4. **Payments are persisted for API-processed payments** — Webhook-only payment history and refunds remain limited.
5. **No payment history or refund tracking**.
6. **ACP checkout sessions not connected to checkout agent** — Agent validates raw item lists, not ACP session models.

---

### 4.8 Support Tickets & Returns

#### Gaps

1. **Customer/agent ticket creation route is still missing** — Staff/admin lifecycle endpoints exist, but there is no customer-facing create route.
2. **`BaseCRUDAdapter._create_ticket()` returns `unsupported_operation`** — Agent-side ticket creation remains unresolved.
3. **Returns lack customer-facing creation** — Only staff can view/approve. No `POST /api/orders/{id}/returns`.
4. **Returns model misaligned with agent output** — CRUD stores `{id, order_id, user_id, status, reason, created_at}`. Agent produces `{eligible_for_return, next_steps}`.

---

### 4.9 Product Management (PIM/DAM)

**Agents**: product-management-acp-transformation, product-management-assortment-optimization, product-management-consistency-validation, product-management-normalization-classification. **Relevant issue**: #34 (PIM/DAM workflow).

#### Gaps

1. **Zero CRUD integration for all 4 product-management agents** — No `AgentClient` methods, no settings URLs.
2. **Agent outputs are fire-and-forget** — ACP payloads, assortment scores, validation results, normalization/classification data are all logged but never persisted.
3. **No product write path** — Agents can't update product data (normalized names, classifications) back through CRUD.
4. **No `ProductData`/`AssetData` tables** — Issue #34's Product Graph and DAM requests have no backing models.
5. **No product versioning or audit trail** — Issue #34 requires immutable snapshots and rollback.
6. **No confidence scoring model** — Issue #34 requires per-field confidence scores for HITL workflows.

---

## 5. New Postgres Tables Required

Based on the full gap analysis, these tables should be added to the CRUD service. All follow the existing JSONB pattern: `(id TEXT PK, partition_key TEXT, data JSONB, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`.

### Priority 1 — Critical (Unblocks agents from mocks)

| Table | Partition Key | Key JSONB Fields | Consumers |
|-------|-------------|-----------------|-----------|
| **`inventory`** | `sku` | sku, available, reserved, backorder_date, safety_stock, lead_time_days, status, attributes | 4 inventory agents, checkout-support, cart-intelligence |
| **`warehouse_stock`** | `sku` | warehouse_id, sku, available, reserved, location, updated_at | inventory-health-check, inventory-alerts-triggers |
| **`contacts`** | `account_id` | contact_id, account_id, email, phone, locale, timezone, marketing_opt_in, first_name, last_name, title, tags, preferences, attributes | 4 CRM agents |
| **`accounts`** | `account_id` | account_id, name, region, owner, industry, tier, lifecycle_stage, attributes | 4 CRM agents |
| **`interactions`** | `contact_id` | interaction_id, contact_id, account_id, channel, occurred_at, duration_seconds, outcome, subject, summary, sentiment, metadata | 4 CRM agents |
| **`prices`** | `sku` | sku, currency, amount, list_amount, discount_code, channel, region, tax_included, promotional, effective_from, effective_to, attributes | checkout-support, cart-intelligence |

### Priority 2 — High (Persistence for agent enrichments + operational data)

| Table | Partition Key | Key JSONB Fields | Consumers |
|-------|-------------|-----------------|-----------|
| **`shipment_events`** | `tracking_id` | code, description, occurred_at, location, metadata | order-status, logistics agents |
| **`inventory_reservations`** | `sku` | reservation_id, sku, requested_qty, approved, effective_available, backorder_qty, created_at, expires_at | reservation-validation agent |
| **`inventory_alerts`** | `sku` | alert_id, sku, alert_type, threshold, status, severity, created_at, resolved_at | alerts-triggers agent |
| **`replenishment_plans`** | `sku` | plan_id, sku, target_stock, recommended_reorder_qty, lead_time_days, safety_stock, created_at, status | jit-replenishment agent |
| **`campaigns`** | `account_id` | campaign_id, name, status, spend, budget, start_date, end_date, account_id | campaign-intelligence agent |
| **`funnel_metrics`** | `campaign_id` | stage, count, conversion_rate, channel, stage_time_ms, campaign_id, account_id, updated_at | campaign-intelligence agent |
| **`payments`** | `user_id` | payment_id, order_id, user_id, amount, currency, status, provider, transaction_id, method_id, created_at, refunded_at | checkout, order flow |

### Priority 3 — Medium (Agent enrichment persistence + PIM/DAM)

| Table | Partition Key | Key JSONB Fields | Consumers |
|-------|-------------|-----------------|-----------|
| **`customer_segments`** | `contact_id` | contact_id, segment, interaction_count, personalization, tags, account_tier, computed_at | segmentation-personalization |
| **`profile_summaries`** | `contact_id` | contact_id, account_id, marketing_opt_in, interaction_count, recent_channels, engagement_score, tags, computed_at | profile-aggregation |
| **`campaign_roi`** | `campaign_id` | campaign_id, account_id, conversions, revenue, spend, roi, computed_at | campaign-intelligence |
| **`support_briefs`** | `contact_id` | contact_id, account_id, last_interaction_at, sentiment, risk, issue_summary, next_best_actions, computed_at | support-assistance |
| **`product_validations`** | `sku` | sku, issues, status, validated_at | consistency-validation |
| **`product_normalizations`** | `sku` | sku, normalized_name, normalized_category, tags, classification, computed_at | normalization-classification |
| **`assortment_scores`** | `sku` | sku, name, rating, price, score, recommendation (keep/drop), scored_at | assortment-optimization |
| **`acp_product_feeds`** | `sku` | Full ACP payload (item_id, title, price, availability, etc.), generated_at | acp-transformation |
| **`product_graph_nodes`** | `sku` | sku, node_type, relationships, version, confidence_scores, audit_log | Issue #34 (PIM/DAM) |
| **`digital_assets`** | `sku` | asset_id, sku, url, content_type, alt_text, quality_score, processed_variants, cdn_url | Issue #34 (DAM) |

---

## 6. New Adapters Required (lib & CRUD)

### 6.1 CRUD-Backed Adapters for Lib Connectors

Each lib connector currently binds to a mock adapter. To make agents production-ready, adapters that call CRUD API endpoints should be created.

| Connector | New Adapter | Calls CRUD Endpoint | Replaces |
|-----------|------------|-------------------|----------|
| `ProductConnector` | `CRUDProductAdapter` | `GET /api/products/{sku}` | `MockProductAdapter` |
| `InventoryConnector` | `CRUDInventoryAdapter` | `GET /api/inventory/{sku}` (new) | `MockInventoryAdapter` |
| `PricingConnector` | `CRUDPricingAdapter` | `GET /api/prices/{sku}` (new) | `MockPricingAdapter` |
| `LogisticsConnector` | `CRUDLogisticsAdapter` | `GET /api/staff/shipments/{id}` + `GET /api/shipment-events/{id}` (new) | `MockLogisticsAdapter` |
| `CRMConnector` | `CRUDCRMAdapter` | `GET /api/contacts/{id}`, `GET /api/accounts/{id}`, `GET /api/interactions` (all new) | `MockCRMAdapter` |
| `FunnelConnector` | `CRUDFunnelAdapter` | `GET /api/funnel-metrics`, `GET /api/campaigns/{id}` (all new) | `MockFunnelAdapter` |

### 6.2 Enterprise Connector Implementations

These implement the ABCs defined in `integrations/contracts.py`. They are not CRUD adapters but external system connectors. Each maps to one or more open connector issues (#36-#78).

| Contract | Priority Implementations | Relevant Issues |
|----------|------------------------|-----------------|
| `PIMConnectorBase` | Akeneo (#48), Salsify (#46) | #46-49, #74-75 |
| `DAMConnectorBase` | Cloudinary (#50), Bynder (#52) | #50-52, #76 |
| `InventoryConnectorBase` | SAP S/4HANA (#36), Dynamics 365 (#40) | #36-40, #77 |
| `CRMConnectorBase` | Salesforce (#41), Dynamics 365 (#42) | #41-45, #78 |
| `CommerceConnectorBase` | Shopify Plus (#53), commercetools (#54) | #53-59 |
| `AnalyticsConnectorBase` | Azure Synapse (#60), Snowflake (#61) | #60-64 |
| `IntegrationConnectorBase` | Confluent Kafka (#66) | #65-68 |
| `IdentityConnectorBase` | Okta/Auth0 (#69) | #69 |
| `WorkforceConnectorBase` | UKG/Kronos (#71) | #71-73 |

### 6.3 Architecture Issues for Adapter Infrastructure

| Issue | Description |
|-------|------------|
| #79 — Connector Registry Pattern | Runtime discovery + DI for adapters (partially exists as `ConnectorRegistry`) |
| #80 — Event-Driven Connector Sync | CDC-based sync between connectors and CRUD data; implemented with typed connector events, webhook ingress, consumer idempotency, dead-letter, and replay endpoints |
| #81 — Multi-Tenant Connector Config | Per-tenant adapter configuration |
| #82 — Protocol Interface Evolution | Versioning strategy for connector contracts |
| #83 — Internal Data Enrichment Guardrails | Quality gates for agent-produced enrichments |
| #84 — Reference Architecture Patterns | Documentation of connector + adapter patterns |

---

## 7. New Agents to Consider

Based on gap analysis and open issues, these new agents would fill functional gaps:

| Agent | Domain | Purpose | Prerequisites |
|-------|--------|---------|--------------|
| **inventory-demand-forecasting** | Inventory | Predict demand using order history + seasonality | `orders` + `inventory` tables, analytics connector |
| **crm-lifecycle-management** | CRM | Automate lifecycle stage transitions | `contacts` + `accounts` + `interactions` tables |
| **product-graph-enrichment** | PIM/DAM | Issue #34's enrichment pipeline (ingest → enrich → classify → validate) | `product_graph_nodes` + `digital_assets` tables |
| **product-asset-processing** | PIM/DAM | Issue #34's DAM pipeline (image processing, alt-text, quality scoring) | Azure Blob storage + AI Vision |
| **product-distribution** | PIM/DAM | Issue #34's platform distribution (SAP, Oracle, Salsify) | Enterprise connector implementations |
| **payment-processing** | Payments | Real Stripe integration replacing the stub | `payments` table, Stripe API keys |
| **analytics-aggregation** | Staff | Real sales analytics replacing the stub | `orders` + `payments` tables |
| **workforce-scheduling** | Workforce | Staff scheduling for peak periods | Workforce connector (#71-73) |

---

## 8. BaseCRUDAdapter MCP Tool Gaps

Current MCP tools registered by `BaseCRUDAdapter`:

| Tool | Status | Issue |
|------|--------|-------|
| `/crud/products/get` | Working | `id` vs `sku` mismatch |
| `/crud/products/list` | Working | — |
| `/crud/products/batch` | Working | Sequential GETs (N+1 problem) |
| `/crud/orders/get` | Working | — |
| `/crud/orders/list` | Working | — |
| `/crud/orders/cancel` | Working | — |
| `/crud/orders/update-status` | **Broken** | Only supports cancel; returns "unsupported" for other statuses |
| `/crud/cart/get` | Working | — |
| `/crud/cart/recommendations` | Working | — |
| `/crud/users/me` | Working | — |
| `/crud/inventory/get` | **Broken** | Reads product `.inventory` sub-field (usually null) |
| `/crud/tickets/create` | **Stub** | Returns `unsupported_operation` |

### MCP Tools to Add

| Tool | CRUD Endpoint (new) | Purpose |
|------|-------------------|---------|
| `/crud/inventory/get` (fix) | `GET /api/inventory/{sku}` | Real inventory data |
| `/crud/inventory/reserve` | `POST /api/inventory/{sku}/reserve` | Create reservation |
| `/crud/inventory/release` | `POST /api/inventory/{sku}/release` | Release reservation |
| `/crud/shipments/get` | `GET /api/staff/shipments/{id}` | Shipment lookup |
| `/crud/shipments/list` | `GET /api/staff/shipments` | Shipment listing |
| `/crud/shipment-events/list` | `GET /api/shipment-events/{tracking_id}` | Tracking events |
| `/crud/contacts/get` | `GET /api/contacts/{id}` | CRM contact |
| `/crud/accounts/get` | `GET /api/accounts/{id}` | CRM account |
| `/crud/interactions/list` | `GET /api/interactions?contact_id=` | CRM interactions |
| `/crud/prices/get` | `GET /api/prices/{sku}` | Pricing data |
| `/crud/tickets/create` (fix) | `POST /api/tickets` | Real ticket creation |
| `/crud/returns/create` | `POST /api/orders/{id}/returns` | Return initiation |
| `/crud/orders/update-status` (fix) | `PATCH /api/orders/{id}/status` | Arbitrary status updates |
| `/crud/products/update` | `PATCH /api/products/{id}` | Product updates (for enrichments) |

---

## 9. AgentClient Method Gaps

Methods to add to `AgentClient` in `crud_service/integrations/agent_client.py`:

| Method | Target Agent | Settings Field | CRUD Route |
|--------|-------------|---------------|------------|
| `get_campaign_intelligence()` | crm-campaign-intelligence | `crm_campaign_agent_url` | New `GET /api/campaigns/{id}/intelligence` |
| `get_support_brief()` | crm-support-assistance | `crm_support_agent_url` | New `GET /api/tickets/{id}/brief` |
| `get_inventory_alerts()` | inventory-alerts-triggers | `inventory_alerts_agent_url` | New `GET /api/inventory/{sku}/alerts` |
| `get_replenishment_plan()` | inventory-jit-replenishment | `inventory_replenishment_agent_url` | New `GET /api/inventory/{sku}/replenishment` |
| `get_route_issues()` | logistics-route-issue-detection | `logistics_route_agent_url` | Enrich `OrderTrackingResponse` |
| `transform_to_acp()` | product-management-acp-transformation | `product_acp_agent_url` | New `POST /api/products/{sku}/acp` |
| `get_assortment_score()` | product-management-assortment-optimization | `product_assortment_agent_url` | New `POST /api/products/assortment` |
| `validate_product()` | product-management-consistency-validation | `product_validation_agent_url` | New `GET /api/products/{sku}/validate` |
| `normalize_product()` | product-management-normalization-classification | `product_normalization_agent_url` | New `GET /api/products/{sku}/normalize` |

---

## 10. Event Hub Coverage Gaps

### Current Publishing (CRUD → Event Hubs)

| Event Hub | Events Published | Published By |
|-----------|-----------------|-------------|
| `order-events` | `OrderCreated`, `OrderCancelled` | Orders route |
| `payment-events` | `PaymentProcessed` | Payments route |
| `inventory-events` | — | **Never published** (method exists, never called) |
| `shipment-events` | — | **Never published** (method exists, never called) |
| `user-events` | — | **Never published** (method exists, never called) |
| `product-events` | — | **Does not exist** |

### Current Subscriptions (Agents ← Event Hubs)

| Event Hub | Subscribing Agents |
|-----------|-------------------|
| `order-events` | 15 of 21 agents |
| `inventory-events` | 3 inventory agents, checkout-support |
| `payment-events` | campaign-intelligence |
| `product-events` | 5 agents (catalog-search, enrichment, 4 product-management) |
| `shipment-events` | **No agent subscribes** |
| `user-events` | campaign-intelligence, profile-aggregation |

### Actions Needed

1. **Publish `inventory-events`** when inventory changes (reserves, releases, adjustments)
2. **Publish `shipment-events`** when shipments are created/updated  
3. **Publish `user-events`** when users register or update profiles
4. **Add `product-events` publishing** for product CRUD operations
5. **Subscribe logistics agents to `shipment-events`** (natural trigger for tracking)
6. **Subscribe order-status agent to `shipment-events`** for real-time tracking

---

## 11. Schema Mismatches & Field Mapping Issues

| Area | CRUD Uses | Agents Use | Impact |
|------|----------|-----------|--------|
| Product ID | `id` | `sku` | All agent ↔ CRUD product references need mapping |
| Product category | `category_id` (FK) | `category` (string) | Category resolution required |
| Cart item ID | `product_id` | `sku` | Cart route manually maps; fragile |
| Reservation approval | — | Agent returns `approved` | CRUD cart checks `valid` — always passes |
| ACP search results | Expects `id`, `name`, `price: float` | Returns `item_id`, `title`, `price: "10.00 usd"` | Pydantic validation failure |
| Shipment ID | `tracking_number` field | `tracking_id` field | Different naming |
| Order tracking | `tracking_id` on order doc | Agent generates `T-{order_id}` stub | Never resolves real tracking |

---

## 12. Proposed Issues

These are the issues that should be filed to bring the CRUD service to full feature parity with the agent ecosystem.

### Infrastructure & Critical Fixes

| # | Title | Priority | Category |
|---|-------|----------|----------|
| New | CRUD: Add `inventory` and `warehouse_stock` tables with full CRUD endpoints | Critical | Backend |
| New | CRUD: Add `contacts`, `accounts`, `interactions` tables with full CRUD endpoints | Critical | Backend |
| New | CRUD: Add `prices` table with multi-currency, promotional pricing CRUD endpoints | High | Backend |
| New | CRUD: Fix `BaseCRUDAdapter._get_inventory()` to use new inventory endpoint | Critical | Lib |
| New | CRUD: Fix reservation validation field mismatch (`approved` → `valid`) | High | Backend |
| New | CRUD: Fix ACP search result → `ProductResponse` mapping in products route | High | Backend |

### New Endpoints & Write Paths

| # | Title | Priority | Category |
|---|-------|----------|----------|
| New | CRUD: Add `POST /api/tickets` endpoint + fix `BaseCRUDAdapter._create_ticket()` | High | Backend |
| New | CRUD: Add `POST /api/orders/{id}/returns` customer-facing return creation | High | Backend |
| New | CRUD: Add `PATCH /api/orders/{id}/status` for arbitrary status updates | Medium | Backend |
| New | CRUD: Add shipment write endpoints (`POST/PATCH /api/shipments`) + events table | High | Backend |
| New | CRUD: Add product write endpoints (`POST/PATCH /api/products`) | High | Backend |
| New | CRUD: Implement real payments persistence + `GET /payments/{id}` | Medium | Backend |
| New | CRUD: Implement staff analytics aggregation (replace stub) | Medium | Backend |

### Agent Integration

| # | Title | Priority | Category |
|---|-------|----------|----------|
| New | CRUD: Add `AgentClient` methods for 9 unintegrated agents | High | Backend |
| New | CRUD: Add settings URLs for campaign, support, alerts, replenishment, route, 4 product-mgmt agents | High | Config |
| New | CRUD: Extend `BaseCRUDAdapter` with 14 new MCP tools | High | Lib |
| New | CRUD: Fix `orders/update-status` MCP tool to support all statuses | Medium | Lib |

### Schema Alignment

| # | Title | Priority | Category |
|---|-------|----------|----------|
| New | CRUD: Add `brand`, `currency`, `tags`, `attributes`, `variants` to `ProductResponse` | High | Backend |
| New | CRUD: Align `id`/`sku` and `category_id`/`category` across CRUD ↔ agents | Medium | Backend + Lib |
| New | CRUD: Align shipment `tracking_number` ↔ `tracking_id` naming | Medium | Backend |

### Event Hub Publishing

| # | Title | Priority | Category |
|---|-------|----------|----------|
| New | CRUD: Publish `inventory-events` on reserve/release/adjustment | High | Backend |
| New | CRUD: Publish `shipment-events` on shipment create/update | High | Backend |
| New | CRUD: Publish `user-events` on user registration/update | Medium | Backend |
| New | CRUD: Add `product-events` Event Hub topic + publish on product changes | High | Backend + Infra |

### Enrichment Persistence

| # | Title | Priority | Category |
|---|-------|----------|----------|
| New | CRUD: Add tables for agent enrichment persistence (segments, profiles, scores, briefs) | Medium | Backend |
| New | CRUD: Add tables for product-management outputs (validations, normalizations, ACP feeds, assortment scores) | Medium | Backend |

### PIM/DAM (Issue #34)

| # | Title | Priority | Category |
|---|-------|----------|----------|
| New | CRUD: Add `product_graph_nodes` and `digital_assets` tables for PIM/DAM workflow | Medium | Backend |
| New | CRUD: Implement HITL approval endpoints with confidence scoring | Low | Backend |
| New | CRUD: Add product versioning and audit trail CRUD endpoints | Low | Backend |

### Seed Data

| # | Title | Priority | Category |
|---|-------|----------|----------|
| New | CRUD: Extend seed script with demo data for inventory, CRM, pricing, shipments, campaigns | High | Backend |
| New | CRUD: Seed `brand`, `currency`, `tags`, `attributes` on existing product demo data | Medium | Backend |

---

## 13. Appendix — Open Issues Reference

### Core Issues (#25-34)

| # | Title | Status | CRUD Impact |
|---|-------|--------|-------------|
| 25 | CRUD service not registered in APIM | Bug | Frontend can't reach CRUD API |
| 26 | Agent health endpoints return 500 through APIM | Bug | Agent calls from CRUD may fail |
| 27 | SWA API proxy returns 404 for /api/* routes | Bug | Frontend ↔ CRUD broken |
| 28 | Frontend uses hardcoded mock data instead of API hooks | Enhancement | Frontend doesn't call CRUD |
| 29 | 10 lib config tests fail due to schema drift | Bug | Test reliability |
| 30 | CI agent tests silently swallowed with \|\| true | Bug | CI reliability |
| 31 | Payment processing fully stubbed | Enhancement | Payment features non-functional |
| 32 | Azure AI Search not provisioned | Enhancement | Catalog search agent non-functional |
| 33 | Route protection middleware implemented (issue #33 resolved) | Resolved | Closed via UI middleware with login redirect messaging polish |
| 34 | PIM/DAM Agentic Workflow | Feature | Requires new CRUD models |

### Connector Issues (#36-78) — 43 issues

Grouped by domain: Commerce (7), Inventory/SCM (6), CRM/CDP (6), PIM (6), DAM (4), Data/Analytics (5), Integration (4), Identity (1), Privacy (1), Workforce (3).

### Architecture Issues (#79-84) — 6 issues

Connector Registry, Event-Driven Sync, Multi-Tenant Config, Protocol Evolution, Data Enrichment Guardrails, Reference Architecture Patterns.

---

## 14. Enterprise API Schema Grounding

> This section validates every proposed CRUD table and lib schema from Sections 4–5 against **real enterprise ecommerce API data models**. Each domain cross-references multiple platforms, identifies convergent field patterns, and recommends schema adjustments grounded in production-grade systems.

### 14.1 Methodology & Sources

#### Platforms Analyzed

| Platform | Domain | API Style | Auth | Connector Issue |
|----------|--------|-----------|------|-----------------|
| **Shopify Plus** | Commerce, Inventory, Orders | REST + GraphQL (Admin API) | OAuth 2.0 | #53 |
| **commercetools** | Commerce, Inventory, Orders, Customer | REST + GraphQL (Composable Commerce) | OAuth 2.0 (client_credentials) | #54 |
| **SAP S/4HANA** | Inventory, SCM | OData v4 | OAuth 2.0 | #36 |
| **Oracle Fusion Cloud SCM** | Inventory, Orders, Shipments | REST JSON | OAuth 2.0 JWT | #37 |
| **Manhattan Active Omni** | Inventory, Orders, Fulfillment | REST + Events | OAuth 2.0 | #38 |
| **Salesforce** | CRM (Contact, Account, Case) | REST + GraphQL | OAuth 2.0 JWT | #41 |
| **Dynamics 365 CE** | CRM (Contact, Account, Incident) | OData v4 | Azure AD OAuth | #42 |
| **Salsify PXM** | PIM (Products, Assets, Catalogs) | REST | API Key | #46 |
| **Akeneo PIM** | PIM (Products, Attributes, Families) | REST | OAuth 2.0 | #48 |
| **Cloudinary** | DAM (Images, Transformations) | REST | API Key + Secret | #50 |
| **Azure Synapse Analytics** | Analytics (SQL Pools, Pipelines) | REST + SQL | Azure AD | #60 |

#### Schema Retrieval

- **Primary sources**: Shopify Admin REST API docs, commercetools HTTP API docs (fetched via web), SAP OData entity definitions from issue #36, Oracle Fusion endpoint specs from issue #37.
- **Secondary sources**: Connector issue bodies (#36–#60) which contain endpoint specifications, entity structures, and protocol requirements.
- **Validation approach**: Each proposed CRUD table is checked for (1) field-level coverage against ≥2 enterprise platforms, (2) naming convention alignment, and (3) missing enterprise-standard fields.

---

### 14.2 Product & Catalog — Enterprise Comparison

#### Cross-Platform Product Entity Comparison

| Field Concept | Shopify `Product` | commercetools `Product` | Salsify `product` | Akeneo `product` | Lib `CatalogProduct` | Lib `ProductData` |
|---|---|---|---|---|---|---|
| **Primary ID** | `id` (INT64) | `id` (UUID) | `salsify:id` | `identifier` | `sku` | `sku` |
| **SKU** | `variants[].sku` | `masterVariant.sku` | custom property | `identifier` | `sku` | `sku` |
| **Name/Title** | `title` | `name` (LocalizedString) | `salsify:name` | per-attribute | `name` | `title` |
| **Description** | `body_html` | `description` (LocalizedString) | custom property | per-attribute | `description` | `description` |
| **Short Description** | — | `metaDescription` (Localized) | — | per-attribute | — | `short_description` |
| **Brand/Vendor** | `vendor` | via attribute | custom property | per-attribute | `brand` | `brand` |
| **Product Type** | `product_type` | `productType` (Reference) | `salsify:category` | `family` | `category` | `category_path[]` |
| **Category Path** | — (tags-based) | `categories[]` (References) | `catalog` hierarchy | `categories[]` | `category` (flat) | `category_path[]` |
| **Status** | `status` (active/draft/archived) | via `masterData.published` | `salsify:status` | `enabled` (bool) | — | `status` |
| **Handle/Slug** | `handle` | `slug` (LocalizedString) | — | — | — | — |
| **Tags** | `tags` (comma-separated string) | — (via attributes) | `salsify:tag` array | — | `tags[]` | — |
| **Images** | `images[]` (src, position, variant_ids) | `masterVariant.images[]` (url, dimensions, label) | `digital_assets[]` | `media-files` | `image_url` (single) | `images[]` |
| **Variants** | `variants[]` (price, sku, barcode, weight, inventory_qty) | `variants[]` + `masterVariant` (sku, prices[], attributes[], images[], availability) | — (flat products) | — (product models) | `variants[]` | `variants[]` |
| **Options** | `options[]` (up to 3: e.g., Color, Size) | — (attributes define options) | properties | attribute groups | — | — |
| **Price** | `variants[].price` | `variants[].prices[]` (multi-currency, channel-scoped) | custom property | — | `price` | — |
| **Attributes** | via metafields | `variants[].attributes[]` (name/value typed) | properties (key/value) | attributes (typed, per locale/channel) | `attributes{}` | `attributes{}` |
| **Source System** | — | — | — | — | — | `source_system` |
| **Created/Modified** | `created_at`, `updated_at` | `createdAt`, `lastModifiedAt` | `salsify:updated_at` | `created`, `updated` | — | `last_modified` |
| **Versioning** | — | `version` (Int, optimistic concurrency) | — | — | — | — |
| **Localization** | — | All text fields are `LocalizedString` | — | Attributes scoped by locale+channel | — | — |
| **Tax Category** | — | `taxCategory` (Reference) | — | — | — | — |
| **Review Stats** | — | `reviewRatingStatistics` | — | — | `rating` | — |

#### Validation of Proposed CRUD `products` Table Against Enterprise Models

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `sku` | ✅ Universal (all platforms use SKU, often at variant level) | **Confirmed** |
| `name` | ✅ Universal (Shopify `title`, commercetools `name`) | **Confirmed** |
| `description` | ✅ Universal | **Confirmed** |
| `brand` | ✅ Shopify `vendor`, commercetools via attribute, PIM via attribute | **Confirmed** |
| `category` | ⚠️ Enterprise uses category paths/hierarchies, not flat strings | **Needs upgrade — use `category_path[]`** |
| `price` | ⚠️ Enterprise prices are variant-level + multi-currency. Separate table preferred | **Confirmed for simple; see §14.5 for full** |
| `currency` | ✅ Shopify whole-store, commercetools per-price, both support multi | **Confirmed** |
| `image_url` | ⚠️ Enterprise supports image arrays, not single URL | **Needs upgrade — use `images[]`** |
| `rating` | ✅ commercetools has `reviewRatingStatistics` | **Confirmed** |
| `tags` | ✅ Shopify `tags`, commercetools uses attributes | **Confirmed** |
| `attributes` | ✅ Universal (metafields, attributes, properties) | **Confirmed** |
| `variants` | ✅ Universal (Shopify max ~100, commercetools max 100) | **Confirmed** |
| — | `status` (all platforms), `handle/slug` (Shopify + commercetools), `product_type` (strong typing) | **Missing — Add `status`, `slug`, `product_type_ref`** |
| — | `version` (commercetools optimistic concurrency) | **Missing — Add `version` for optimistic locking** |
| — | Localized text fields (commercetools, Akeneo) | **Missing — Add `localized_names{}`, `localized_descriptions{}`** |
| — | `source_system` (multi-connector provenance) | **Missing — Add from `ProductData`** |

#### Recommendations

1. **Upgrade `category` to `category_path: list[str]`** — Both commercetools (`categories[]` references) and Akeneo (category trees) model hierarchical categories. A flat string loses the path context needed by assortment-optimization and normalization-classification agents.
2. **Upgrade `image_url` to `images: list[dict]`** — Every platform stores multiple images with metadata (position, dimensions, variant association). The single-URL approach prevents DAM workflows (issue #34).
3. **Add `status` field** — Shopify (`active`/`draft`/`archived`), commercetools (`published`/`unpublished`), Salsify, and Akeneo all have product lifecycle status. Essential for PIM agents.
4. **Add `version: int`** — commercetools requires this for optimistic concurrency. Essential for multi-agent writes to avoid conflicts.
5. **Add `source_system: str`** — Already on `ProductData` contract. Required when products come from multiple enterprise connectors simultaneously.
6. **Add `slug: str`** — Shopify `handle` and commercetools `slug` are used for SEO-friendly URLs. Needed when CRUD serves the frontend catalog.

---

### 14.3 Inventory & Warehouse — Enterprise Comparison

#### Cross-Platform Inventory Entity Comparison

| Field Concept | Shopify `InventoryLevel` | commercetools `InventoryEntry` | SAP S/4HANA `A_MatlStkInAcctMod` | Oracle Fusion `inventoryBalances` | Manhattan `inventory/availability` | Lib `InventoryItem` | Lib `InventoryData` |
|---|---|---|---|---|---|---|---|
| **SKU/Material** | via `inventory_item_id` → variant.sku | `sku` (String) | `Material` | `ItemNumber` | `itemId` | `sku` | `sku` |
| **Location** | `location_id` | `supplyChannel` (ChannelRef) | `Plant` + `StorageLocation` | `OrganizationId` + `SubinventoryCode` | `facilityId` | — | `location_id` |
| **Location Name** | via Location API | via Channel name | `PlantName` | `SubinventoryName` | `facilityName` | — | `location_name` |
| **Available Qty** | `available` (Int) | `availableQuantity` (Int) | `MatlWrhsStkQtyInMatlBaseUnit` | `AvailableQuantity` | `availableQuantity` | `available` | `available_qty` |
| **Total/On-hand** | — (available only) | `quantityOnStock` (Int) | `TotalStock` | `OnhandQuantity` | `onHandQuantity` | — | — |
| **Reserved Qty** | — (tracked separately) | — (computed: onStock − available) | `GRBlockedStock` | `ReservedQuantity` | `reservedQuantity` | `reserved` | `reserved_qty` |
| **On-Order Qty** | — | — | `StockInTransfer` | `InTransitQuantity` | `inTransitQuantity` | — | `on_order_qty` |
| **Reorder Point** | — | — | `ReorderPoint` | `ReorderPoint` | `reorderPoint` | `safety_stock` | `reorder_point` |
| **Lead Time** | — | `restockableInDays` (Int) | `PlannedDeliveryTimeInDays` | `LeadTime` | — | `lead_time_days` | — |
| **Expected Delivery** | — | `expectedDelivery` (DateTime) | from PO schedule | from PO | — | `backorder_date` | — |
| **Min/Max Cart Qty** | — | `minCartQuantity`, `maxCartQuantity` | — | — | — | — | — |
| **Status** | — | — | `AvailabilityStatus` | — | — | `status` | — |
| **Last Updated** | `updated_at` | `lastModifiedAt` | — | `LastUpdateDate` | `lastModified` | — | `last_updated` |
| **Unit of Measure** | — | — | `MaterialBaseUnit` | `PrimaryUomCode` | `unitOfMeasure` | — | — |
| **Lot/Batch** | — | — | `Batch` | `LotNumber` | `lotNumber` | — | — |
| **Custom Fields** | — | `custom` (CustomFields) | — | Flex fields | — | `attributes{}` | — |

#### Validation of Proposed CRUD Tables

**`inventory` table:**

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `sku` | ✅ Universal | **Confirmed** |
| `available` | ✅ Universal | **Confirmed** |
| `reserved` | ✅ SAP, Oracle, Manhattan explicit; commercetools derived | **Confirmed** |
| `backorder_date` | ✅ commercetools `expectedDelivery`, SAP/Oracle via PO | **Confirmed** |
| `safety_stock` | ✅ SAP `ReorderPoint`, Oracle `ReorderPoint` | **Confirmed** (rename to `reorder_point` for clarity) |
| `lead_time_days` | ✅ commercetools `restockableInDays`, SAP `PlannedDeliveryTimeInDays` | **Confirmed** |
| `status` | ⚠️ Only SAP has explicit `AvailabilityStatus` | **Confirmed** (lib has it) |
| `attributes` | ✅ commercetools `custom`, SAP flex fields | **Confirmed** |
| — | `quantity_on_stock` (commercetools), `total_stock` (SAP) — on-hand total | **Missing — Add `on_hand_qty`** |
| — | `on_order_qty` (Oracle, Manhattan) — in-transit stock | **Missing — Add `on_order_qty`** |
| — | `unit_of_measure` (SAP, Oracle, Manhattan) | **Missing — Add `unit_of_measure`** |
| — | `lot_number` / `batch` (SAP, Oracle, Manhattan) | **Missing — Add `lot_number`** for traceability |
| — | `min_cart_qty`, `max_cart_qty` (commercetools) | **Consider adding** for B2B use cases |

**`warehouse_stock` table:**

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `warehouse_id` | ✅ Shopify `location_id`, commercetools `supplyChannel`, SAP `Plant`, Oracle `OrganizationId`, Manhattan `facilityId` | **Confirmed** |
| `sku` | ✅ Universal | **Confirmed** |
| `available` | ✅ Universal per-location availability | **Confirmed** |
| `reserved` | ✅ SAP/Oracle/Manhattan per-location reservation | **Confirmed** |
| `location` | ⚠️ Enterprise distinguishes warehouse ID from location name. Split into `location_name` | **Rename to `location_name`** |
| `updated_at` | ✅ Universal | **Confirmed** |
| — | `on_hand_qty` separate from `available` (SAP, Oracle) | **Missing — Add `on_hand_qty`** |
| — | `location_type` (warehouse, store, distribution center) | **Missing — Add `location_type`** for Manhattan/Oracle patterns |

#### Recommendations

1. **Add `on_hand_qty` to `inventory` table** — Enterprise platforms (SAP, Oracle, Manhattan) distinguish between total on-hand stock and available-to-promise. Formula: `available = on_hand - reserved - allocated`. This is critical for inventory-health-check agent accuracy.
2. **Add `on_order_qty`** — Oracle and Manhattan track in-transit inventory. The jit-replenishment agent needs this to avoid over-ordering.
3. **Add `unit_of_measure`** — SAP and Oracle enforce UoM. Without it, the CRUD layer can't normalize quantities from different connectors (one reports "EA", another "CASE").
4. **Add `lot_number`** — SAP `Batch`, Oracle `LotNumber`. Required for traceability in regulated retail (food, pharma).
5. **Rename `safety_stock` to `reorder_point`** — Better alignment with SAP/Oracle naming. The `InventoryData` contract already uses `reorder_point`.
6. **Add `location_type` to `warehouse_stock`** — Manhattan Active Omni distinguishes facility types (DC, store, vendor-direct). Essential for carrier-selection and fulfillment routing agents.

---

### 14.4 Customer & CRM — Enterprise Comparison

#### Cross-Platform Customer/CRM Entity Comparison

| Field Concept | Salesforce `Contact` | Dynamics 365 `contact` | commercetools `Customer` | Lib `CRMContact` | Lib `CustomerData` |
|---|---|---|---|---|---|
| **Primary ID** | `Id` (18-char) | `contactid` (GUID) | `id` (UUID) | `contact_id` | `customer_id` |
| **External ID** | `ExternalId__c` (custom) | — | `externalId`, `customerNumber` | — | — |
| **Email** | `Email` | `emailaddress1` | `email` (unique per Project/Store) | `email` | `email` |
| **First Name** | `FirstName` | `firstname` | `firstName` | `first_name` | `first_name` |
| **Last Name** | `LastName` | `lastname` | `lastName` | `last_name` | `last_name` |
| **Phone** | `Phone`, `MobilePhone` | `telephone1`, `mobilephone` | — (in addresses) | `phone` | `phone` |
| **Title** | `Title` | `jobtitle` | `title` | `title` | — |
| **Date of Birth** | `Birthdate` | `birthdate` | `dateOfBirth` | — | — |
| **Company** | via `Account.Name` | via `parentcustomerid` | `companyName` | — | — |
| **Locale** | — | — | `locale` | `locale` | — |
| **Marketing Opt-In** | `HasOptedOutOfEmail` (inverse) | `donotemail` (inverse) | — (via custom fields) | `marketing_opt_in` | `consent{}` |
| **Segments** | via Campaign Members | via Marketing Lists | `customerGroup`, `customerGroupAssignments[]` | `tags[]` | `segments[]` |
| **Loyalty Tier** | custom field | `msdyn_loyaltyprogram` (D365 extension) | `customerGroup` | — | `loyalty_tier` |
| **Lifetime Value** | custom / calculated | calculated | — | — | `lifetime_value` |
| **Addresses** | `MailingAddress`, `OtherAddress` | `address1_*`, `address2_*` | `addresses[]` (array, with default shipping/billing) | — | — |
| **Preferences** | custom fields | custom fields | `custom` (CustomFields) | `preferences{}` | `preferences{}` |
| **Verified Email** | — | — | `isEmailVerified` | — | — |
| **Stores** | — | — | `stores[]` (multi-store assignment) | — | — |
| **Auth Mode** | — | — | `authenticationMode` (Password/ExternalAuth) | — | — |
| **Last Activity** | `LastActivityDate` | `lastusedincampaign` | `lastModifiedAt` | — | `last_activity` |
| **Tags** | via Topics / Tags | via Tags | — | `tags[]` | — |
| **Created/Modified** | `CreatedDate`, `LastModifiedDate` | `createdon`, `modifiedon` | `createdAt`, `lastModifiedAt` | — | — |

#### Account Entity Comparison

| Field Concept | Salesforce `Account` | Dynamics 365 `account` | Lib `CRMAccount` |
|---|---|---|---|
| **ID** | `Id` | `accountid` | `account_id` |
| **Name** | `Name` | `name` | `name` |
| **Industry** | `Industry` | `industrycode` | `industry` |
| **Region** | `BillingState`/`BillingCountry` | `address1_stateorprovince` | `region` |
| **Owner** | `OwnerId` | `ownerid` | `owner` |
| **Tier** | Custom/`Rating` | `customertypecode` | `tier` |
| **Lifecycle Stage** | `StageName` (Opportunity-based) | `statecode` | `lifecycle_stage` |
| **Revenue** | `AnnualRevenue` | `revenue` | — |
| **Employee Count** | `NumberOfEmployees` | `numberofemployees` | — |
| **Website** | `Website` | `websiteurl` | — |
| **Parent Account** | `ParentId` | `parentaccountid` | — |

#### Interaction Entity Comparison

| Field Concept | Salesforce `Task`/`Event` | Dynamics 365 `task`/`phonecall` | Lib `CRMInteraction` |
|---|---|---|---|
| **ID** | `Id` | `activityid` | `interaction_id` |
| **Contact Ref** | `WhoId` | `regardingobjectid` | `contact_id` |
| **Account Ref** | `AccountId` | via contact relationship | `account_id` |
| **Channel** | `Type` (Call, Email, Meeting) | entity type (task, phonecall, email) | `channel` |
| **Occurred At** | `ActivityDate` | `actualstart` | `occurred_at` |
| **Duration** | `CallDurationInSeconds` | `actualdurationminutes` | `duration_seconds` |
| **Outcome** | `CallDisposition` | `statuscode` | `outcome` |
| **Subject** | `Subject` | `subject` | `subject` |
| **Summary** | `Description` | `description` | `summary` |
| **Sentiment** | — (custom) | — (custom) | `sentiment` |
| **Priority** | `Priority` | `prioritycode` | — |

#### Validation of Proposed CRUD Tables

**`contacts` table:**

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `contact_id` | ✅ Universal | **Confirmed** |
| `account_id` | ✅ Salesforce `AccountId`, Dynamics via relationship | **Confirmed** |
| `email` | ✅ Universal | **Confirmed** |
| `phone` | ✅ Universal (Salesforce has multiple phone fields) | **Confirmed** |
| `locale` | ✅ commercetools `locale` | **Confirmed** |
| `timezone` | ⚠️ Only Salesforce has native timezone (user-level) | **Confirmed** (lib has it) |
| `marketing_opt_in` | ✅ Universal (inverted in Salesforce/Dynamics) | **Confirmed** |
| `first_name`, `last_name` | ✅ Universal | **Confirmed** |
| `title` | ✅ Universal | **Confirmed** |
| `tags` | ✅ Salesforce Topics, Dynamics Tags | **Confirmed** |
| `preferences` | ✅ Custom fields on all platforms | **Confirmed** |
| `attributes` | ✅ Extensibility pattern on all platforms | **Confirmed** |
| — | `date_of_birth` (Salesforce, Dynamics, commercetools) | **Missing — Add `date_of_birth`** |
| — | `company_name` (commercetools) or via Account | **Consider adding** for B2C without accounts |
| — | `addresses[]` (commercetools, Salesforce) — structured address array | **Missing — Add `addresses[]`** |
| — | `external_id` (cross-system identity) | **Missing — Add `external_id`** |
| — | `email_verified` (commercetools) | **Consider adding** |
| — | `loyalty_tier` (Dynamics `msdyn_loyaltyprogram`, `CustomerData`) | **Missing — Add `loyalty_tier`** |
| — | `lifetime_value` (`CustomerData.lifetime_value`) | **Missing — Add `lifetime_value`** |
| — | `segments[]` (`CustomerData.segments`) | **Missing — Add `segments[]`** |
| — | `consent{}` (`CustomerData.consent`) | **Missing — Add `consent{}`** |

**`accounts` table:**

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `account_id` | ✅ Universal | **Confirmed** |
| `name` | ✅ Universal | **Confirmed** |
| `region` | ✅ Salesforce `BillingCountry`, Dynamics address fields | **Confirmed** |
| `owner` | ✅ Salesforce `OwnerId`, Dynamics `ownerid` | **Confirmed** |
| `industry` | ✅ Universal | **Confirmed** |
| `tier` | ✅ Salesforce `Rating`, Dynamics `customertypecode` | **Confirmed** |
| `lifecycle_stage` | ✅ Both platforms have stage concepts | **Confirmed** |
| `attributes` | ✅ Custom fields on all platforms | **Confirmed** |
| — | `annual_revenue` (Salesforce, Dynamics) | **Missing — Add `annual_revenue`** |
| — | `website` (Salesforce, Dynamics) | **Consider adding** |
| — | `parent_account_id` (hierarchical accounts) | **Missing — Add `parent_account_id`** |
| — | `employee_count` (Salesforce, Dynamics) | **Consider adding** |

**`interactions` table:**

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `interaction_id` | ✅ Universal | **Confirmed** |
| `contact_id` | ✅ Universal | **Confirmed** |
| `account_id` | ✅ Universal | **Confirmed** |
| `channel` | ✅ Salesforce `Type`, Dynamics entity type | **Confirmed** |
| `occurred_at` | ✅ Universal | **Confirmed** |
| `duration_seconds` | ✅ Universal (Dynamics uses minutes — normalize in adapter) | **Confirmed** |
| `outcome` | ✅ Salesforce `CallDisposition`, Dynamics `statuscode` | **Confirmed** |
| `subject` | ✅ Universal | **Confirmed** |
| `summary` | ✅ Universal (`Description`) | **Confirmed** |
| `sentiment` | ⚠️ Not native — typically computed by AI agents | **Confirmed** (agent-enriched) |
| `metadata` | ✅ Custom fields on all platforms | **Confirmed** |
| — | `priority` (Salesforce, Dynamics) | **Missing — Add `priority`** |
| — | `direction` (inbound/outbound — standard CRM pattern) | **Missing — Add `direction`** |

#### Recommendations

1. **Add `addresses[]` to `contacts`** — commercetools stores a full address array with default shipping/billing IDs. Salesforce has `MailingAddress` and `OtherAddress`. Addresses are critical for logistics agents (carrier-selection, ETA) and checkout.
2. **Add `loyalty_tier` and `lifetime_value` to `contacts`** — Already on `CustomerData` contract. Dynamics 365 has native loyalty support (`msdyn_loyaltyprogram`). Required by segmentation-personalization agent.
3. **Add `segments[]` and `consent{}` to `contacts`** — Already on `CustomerData` contract. commercetools has `customerGroup`/`customerGroupAssignments`. Required by campaign-intelligence and GDPR compliance.
4. **Add `external_id` to `contacts`** — When multiple CRM connectors coexist, the external system's ID must be preserved alongside the internal `contact_id`. commercetools supports `externalId` + `customerNumber` natively.
5. **Add `parent_account_id` to `accounts`** — Both Salesforce and Dynamics support account hierarchies. Essential for B2B enterprise retail with subsidiary relationships.
6. **Add `priority` and `direction` to `interactions`** — Standard CRM fields. Salesforce `Priority` and all CRM platforms distinguish inbound vs outbound interactions. Improves support-assistance agent triage.

---

### 14.5 Pricing — Enterprise Comparison

#### Cross-Platform Pricing Model Comparison

| Field Concept | Shopify `variants[].price` | commercetools `Price` | SAP `ConditionRecord` | Lib `PriceEntry` |
|---|---|---|---|---|
| **SKU ref** | via `variant.sku` | via parent `ProductVariant.sku` | `Material` | `sku` |
| **Amount** | `price` (string, e.g., "29.99") | `value.centAmount` (Int) + `value.currencyCode` | `ConditionAmount` | `amount` (float) |
| **Compare-at/List** | `compare_at_price` | — (modeled as separate price) | `ListPrice` | `list_amount` |
| **Currency** | store-level (single currency per store) | per-price `currencyCode` | `Currency` | `currency` |
| **Country/Region** | — | `country` (per price) | `SalesOrganization` | `region` |
| **Channel** | — (Shopify Markets) | `channel` (ChannelReference) | `DistributionChannel` | `channel` |
| **Customer Group** | — | `customerGroup` (Reference) | `CustomerGroup` | — |
| **Discount Code** | via discount rules (separate API) | via Cart Discounts (separate API) | `ConditionType` | `discount_code` |
| **Tax Included** | price includes tax setting | `country` determines tax | Tax via separate condition | `tax_included` |
| **Validity Period** | — | `validFrom`, `validUntil` | `ValidFrom`, `ValidTo` | `effective_from`, `effective_to` |
| **Promotional** | — | — (via discounts) | Condition type flag | `promotional` |
| **Tiers/Quantity Breaks** | — | `tiers[]` (minQuantity → value) | Quantity scales | — |

#### Validation of Proposed CRUD `prices` Table

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `sku` | ✅ Universal | **Confirmed** |
| `currency` | ✅ Universal (commercetools per-price, Shopify per-store) | **Confirmed** |
| `amount` | ✅ Universal | **Confirmed** |
| `list_amount` | ✅ Shopify `compare_at_price`, SAP `ListPrice` | **Confirmed** |
| `discount_code` | ⚠️ Enterprise discounts are separate entities, not price fields | **Keep as reference — but note limitation** |
| `channel` | ✅ commercetools `channel`, SAP `DistributionChannel` | **Confirmed** |
| `region` | ✅ commercetools `country`, SAP `SalesOrganization` | **Confirmed** |
| `tax_included` | ✅ Enterprise standard | **Confirmed** |
| `promotional` | ✅ SAP condition type, general pattern | **Confirmed** |
| `effective_from`, `effective_to` | ✅ commercetools `validFrom`/`validUntil`, SAP `ValidFrom`/`ValidTo` | **Confirmed** |
| `attributes` | ✅ Extensibility | **Confirmed** |
| — | `customer_group` (commercetools, SAP) — group-specific pricing | **Missing — Add `customer_group`** |
| — | `quantity_tiers[]` (commercetools tiers, SAP quantity scales) | **Missing — Add `quantity_tiers[]`** |
| — | `price_type` (standard/promotional/clearance/employee) | **Missing — Add `price_type`** |

#### Recommendations

1. **Add `customer_group`** — commercetools natively supports customer-group-specific prices. SAP uses `CustomerGroup` in condition records. Essential for B2B tiered pricing.
2. **Add `quantity_tiers[]`** — commercetools `tiers` allow different prices at quantity thresholds (e.g., buy 10+ at $5.00 each). Common in wholesale/B2B retail.
3. **Add `price_type`** — Distinguishes between standard, promotional, clearance, and employee pricing. Helps checkout-support agent apply correct pricing logic.
4. **Note**: Enterprise discount management (Shopify Discount API, commercetools Cart Discounts, SAP Condition Types) is deep enough to warrant a separate `discounts` table rather than overloading `PriceEntry.discount_code`.

---

### 14.6 Orders — Enterprise Comparison

#### Cross-Platform Order Entity Comparison

| Field Concept | Shopify `Order` | commercetools `Order` | Oracle Fusion `salesOrders` | Manhattan `orders` | Lib `OrderData` | CRUD `orders` table |
|---|---|---|---|---|---|---|
| **Order ID** | `id` (INT64) | `id` (UUID) | `HeaderId` | `orderId` | `order_id` | `id` |
| **Customer Ref** | `customer.id` (nullable) | `customerId` | `CustomerId` | `customerId` | `customer_id` | `user_id` |
| **Status** | `financial_status` + `fulfillment_status` | `orderState` + `paymentState` + `shipmentState` | `StatusCode` | `orderStatus` | `status` | `status` |
| **Total** | `total_price` (string) | `totalPrice` (Money) | `OrderTotal` | `totalAmount` | `total` | in `data` JSONB |
| **Currency** | `currency` (ISO) | `totalPrice.currencyCode` | `CurrencyCode` | `currency` | `currency` | — |
| **Line Items** | `line_items[]` (product_id, variant_id, sku, title, price, quantity, fulfillment_status) | `lineItems[]` (productId, variant, name, quantity, price, state, custom) | `lines[]` (ItemNumber, Quantity, UnitPrice) | `orderLines[]` | `items[]` | in `data` JSONB |
| **Shipping Address** | `shipping_address{}` | `shippingAddress{}` | `ShipToAddress` | `shipToAddress` | `shipping_address{}` | — |
| **Billing Address** | `billing_address{}` | `billingAddress{}` | `BillToAddress` | `billToAddress` | `billing_address{}` | — |
| **Fulfillment** | `fulfillments[]` (status, tracking_number, line_items) | `shippingInfo` + Delivery objects | Fulfillment Lines | `fulfillmentOrders[]` | — | — |
| **Payment** | `transactions[]` (kind, status, amount) | `paymentInfo.payments[]` | PaymentSchedules | `payments[]` | — | — |
| **Confirmation #** | `confirmation_number` | `orderNumber` | `OrderNumber` | `orderNumber` | — | — |
| **Tags/Notes** | `tags`, `note`, `note_attributes[]` | `custom` fields | Flex fields | — | — | — |
| **Cancel** | `cancel_reason`, `cancelled_at` | `orderState: Cancelled` | `CancelledFlag` | `cancelReason` | — | cancel endpoint |
| **Created/Modified** | `created_at`, `updated_at` | `createdAt`, `lastModifiedAt` | `CreationDate`, `LastUpdateDate` | `createdDate` | `created_at`, `updated_at` | `created_at`, `updated_at` |
| **Discounts** | `discount_codes[]`, `discount_applications[]` | Cart Discount refs | — | — | — | — |
| **Metafields** | `metafields[]` | `custom` | — | — | — | — |

#### Validation of CRUD `orders` Table (existing)

The orders table already exists but uses a generic JSONB model. Comparing with enterprise schemas:

| Enterprise Standard | CRUD Status | Gap |
|---|---|---|
| Multi-status model (financial + fulfillment + shipment) | Single `status` field in JSONB | ⚠️ Enterprise uses compound status — consider `financial_status`, `fulfillment_status`, `shipment_status` |
| Currency as explicit field | Stored in JSONB `data` | ⚠️ Should be a first-class field for multi-currency support |
| Structured line items with variant/sku references | In JSONB `data` | ✅ Flexible via JSONB |
| Shipping + billing addresses | In JSONB `data` | ✅ Flexible via JSONB |
| Order number / confirmation number | Not explicit | ⚠️ **Missing** — Add `order_number` for human-readable reference |
| Fulfillment tracking | Not linked | ⚠️ **Missing** — Add `fulfillment_status` or link to `shipments` table |
| Discount/coupon references | Not modeled | ⚠️ **Missing** — Add `discount_codes[]` |
| Refund tracking | Not modeled | ⚠️ **Missing** — Required by returns-support agent |

#### Recommendations

1. **Add compound status fields** — Shopify separates `financial_status` and `fulfillment_status`. commercetools separates `orderState`, `paymentState`, and `shipmentState`. The order-status agent currently returns a single status string but needs granular states for accurate tracking.
2. **Add `order_number`** — Every enterprise platform assigns a human-readable order number (Shopify `#1001`, commercetools `orderNumber`). Currently, the CRUD service only has the internal UUID `id`.
3. **Add `currency`** — All enterprise platforms include currency at the order level. Essential for multi-region retail.
4. **Link orders to shipments** — Shopify `fulfillments[]` and Manhattan `fulfillmentOrders[]` create an explicit order → shipment relationship. The CRUD shipments table has `order_id` but there's no reverse lookup endpoint.

---

### 14.7 Logistics & Shipments — Enterprise Comparison

#### Cross-Platform Shipment Entity Comparison

| Field Concept | Shopify `Fulfillment` | Oracle Fusion `shipments` | Manhattan `shipments` | Lib `Shipment` |
|---|---|---|---|---|
| **Tracking ID** | `tracking_number` | `TrackingNumber` | `trackingNumber` | `tracking_id` |
| **Order Ref** | `order_id` | `SourceOrderNumber` | `orderId` | `order_id` |
| **Carrier** | `tracking_company` | `CarrierName` | `carrierId` + `carrierName` | `carrier` |
| **Status** | `status` (success/cancelled/error/pending) | `ShipmentStatus` | `status` | `status` |
| **ETA** | — (no native ETA) | `ExpectedDeliveryDate` | `estimatedDeliveryDate` | `eta` |
| **Origin** | `origin_address` | `ShipFromLocation` | `originFacility` | `origin` |
| **Destination** | — (via order shipping address) | `ShipToLocation` | `destinationAddress` | `destination` |
| **Service Level** | — | `ShippingMethod` | `serviceType` | `service_level` |
| **Weight** | `total_weight` | `Weight` + `WeightUom` | `totalWeight` | `weight_kg` |
| **Tracking Events** | `tracking_details[]` (created_at, status, message) | — (via status history) | `events[]` (eventType, timestamp, location) | — (in `ShipmentEvent`) |
| **Created** | `created_at` | `CreationDate` | `createdDate` | — |
| **Line Items** | `line_items[]` (variant, quantity, sku) | `ShipmentLines[]` | `shipmentLines[]` | — |

#### Validation of Proposed CRUD Tables

**`shipments` table** (existing, read-only — needs enhancement):

| Enterprise Standard | CRUD Status | Gap |
|---|---|---|
| Write operations (create + update) | Read-only | ⚠️ **Critical** — Add `POST/PATCH /api/shipments` |
| `eta` / `estimatedDeliveryDate` | Missing | ⚠️ **Add `eta`** — Oracle and Manhattan have it natively |
| `origin` / `destination` | Missing | ⚠️ **Add `origin`, `destination`** |
| `service_level` | Missing | ⚠️ **Add `service_level`** |
| `weight` + UoM | Missing | ⚠️ **Add `weight_kg`** (or `weight` + `weight_uom`) |
| Shipment line items | Missing | ⚠️ **Consider `line_items[]`** for partial fulfillment |

**`shipment_events` table** (proposed):

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `code` | ✅ Shopify `status`, Manhattan `eventType` | **Confirmed** |
| `description` | ✅ Shopify `message`, Manhattan `eventDescription` | **Confirmed** |
| `occurred_at` | ✅ Universal | **Confirmed** |
| `location` | ✅ Manhattan `location`, carrier tracking feeds | **Confirmed** |
| `metadata` | ✅ Extensibility | **Confirmed** |
| — | `carrier_code` (carrier's internal event code) | **Consider adding** for multi-carrier normalization |

#### Recommendations

1. **Unlock shipment writes** — This is the most critical logistics gap. Every enterprise OMS (Manhattan, Oracle) provides full CRUD on shipments. Without write access, carrier-selection and ETA-computation agents can't persist recommendations.
2. **Add `line_items[]` to shipments** — Shopify fulfillments and Manhattan shipments track which line items are in each shipment. Enables partial fulfillment (split shipments), which is standard in enterprise retail.
3. **Add `carrier_code` to `shipment_events`** — When route-issue-detection agent processes events from multiple carriers, each carrier uses different event code systems. A raw `carrier_code` alongside the normalized `code` enables debugging.

---

### 14.8 PIM & DAM — Enterprise Comparison

#### PIM Cross-Platform Comparison

| Field Concept | Salsify PXM | Akeneo PIM | Lib `ProductData` |
|---|---|---|---|
| **Product ID** | `salsify:id` | `identifier` | `sku` |
| **Title** | `salsify:name` | attribute value (locale-scoped) | `title` |
| **Description** | custom property | attribute value (locale/channel-scoped) | `description` |
| **Short Description** | custom property | attribute value | `short_description` |
| **Brand** | custom property | attribute value | `brand` |
| **Category** | `catalog` hierarchy | `categories[]` | `category_path[]` |
| **Attributes** | properties (typed, multi-value) | attributes (per family, typed, locale/channel-scoped) | `attributes{}` |
| **Images** | `digital_assets[]` (linked) | `media-files` (attribute type = image) | `images[]` |
| **Variants** | — (flat products, relationships via properties) | product models → products | `variants[]` |
| **Status** | `salsify:status` | `enabled` (bool) | `status` |
| **Families/Product Types** | — | `family` (defines required attributes) | — |
| **Attribute Groups** | property groups | attribute groups | — |
| **Completeness** | readiness score | completeness % (per locale/channel) | — |
| **Source System** | — | — | `source_system` |
| **Locale Scoping** | — | attributes scoped by locale + channel | — |

#### DAM Cross-Platform Comparison

| Field Concept | Cloudinary | Salsify (linked assets) | Akeneo (media files) | Lib `AssetData` |
|---|---|---|---|---|
| **Asset ID** | `public_id` | `salsify:digital_asset_id` | attribute reference | `id` |
| **URL** | `secure_url` (+ dynamic transforms) | asset URL | media file URL | `url` |
| **Content Type** | `resource_type` (image/video/raw) | file type | mime type | `content_type` |
| **Filename** | `original_filename` | `salsify:name` | filename | `filename` |
| **Size** | `bytes` | — | — | `size_bytes` |
| **Dimensions** | `width`, `height` | — | — | `width`, `height` |
| **Alt Text** | `context.alt` | custom property | — | `alt_text` |
| **Tags** | `tags[]` | — | — | `tags[]` |
| **Transformations** | URL-based (`/w_400,h_300,c_fill/`) | — | — | — |
| **CDN URL** | auto-generated from `public_id` | — | — | — |
| **Folder** | `folder` | — | — | — |
| **Format** | `format` (jpg, png, webp, avif) | — | — | — |
| **Quality Score** | — (can be computed via AI) | — | — | — |

#### Validation of Proposed CRUD Tables

**`product_graph_nodes` table** (proposed for Issue #34):

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `sku` | ✅ Universal product identifier | **Confirmed** |
| `node_type` | ⚠️ Enterprise PIM uses families/product types, not graph node types | **Adjust — rename to `product_type` and add `family`** |
| `relationships` | ✅ Salsify property-based relationships, Akeneo product models | **Confirmed** |
| `version` | ⚠️ commercetools has native versioning; PIM systems use revision history | **Confirmed** |
| `confidence_scores` | ⚠️ Not native to PIM platforms — agent-computed field | **Confirmed** (agent enrichment) |
| `audit_log` | ⚠️ Enterprise PIM has built-in audit; here it's per-record | **Confirmed** |
| — | `completeness` (Akeneo completeness %, Salsify readiness) | **Missing — Add `completeness_score`** |
| — | `locale_data{}` (Akeneo locale+channel scoped attributes) | **Missing — Add `locale_data{}`** |
| — | `family` / `product_type` (Akeneo families, defining required attributes) | **Missing — Add `family`** |

**`digital_assets` table** (proposed for Issue #34):

| Proposed JSONB Field | Enterprise Coverage | Status |
|---|---|---|
| `asset_id` | ✅ Cloudinary `public_id`, Salsify asset ID | **Confirmed** |
| `sku` | ✅ Product association | **Confirmed** |
| `url` | ✅ Universal | **Confirmed** |
| `content_type` | ✅ Universal | **Confirmed** |
| `alt_text` | ✅ Cloudinary `context.alt` | **Confirmed** |
| `quality_score` | ⚠️ Agent-computed (not native to DAM platforms) | **Confirmed** (agent enrichment) |
| `processed_variants` | ⚠️ Cloudinary generates variants via URL transforms, not stored variants | **Adjust — store as `transform_presets{}` map** |
| `cdn_url` | ✅ Cloudinary auto-generates; standard for DAMs | **Confirmed** |
| — | `filename` (Universal) | **Missing — Add `filename`** |
| — | `size_bytes` (Cloudinary `bytes`) | **Missing — Add `size_bytes`** |
| — | `width`, `height` (Cloudinary, standard) | **Missing — Add `width`, `height`** |
| — | `format` (jpg, png, webp — Cloudinary `format`) | **Missing — Add `format`** |
| — | `folder` (Cloudinary `folder`) | **Missing — Add `folder`** for asset organization |

#### Recommendations

1. **Add `completeness_score`** to `product_graph_nodes` — Akeneo's completeness metric (% of required attributes filled per locale/channel) is the industry standard for PIM quality. The consistency-validation agent should compute and persist this.
2. **Add `locale_data{}`** — Akeneo scopes every attribute by locale and channel. The normalization-classification agent needs this to handle localized product data from multi-region connectors.
3. **Add full `AssetData` fields to `digital_assets`** — The `AssetData` contract already defines `filename`, `size_bytes`, `width`, `height`. Cloudinary provides all of these. They should be persisted for asset management UI and DAM agent workflows.
4. **Rename `processed_variants` to `transform_presets{}`** — Cloudinary and modern DAMs handle image variants via transformation rules (e.g., `thumbnail: w_200,h_200`), not pre-generated files. Storing the preset definitions rather than output URLs is more maintainable.

---

### 14.9 Cross-Platform Convergence Summary

This matrix shows which proposed fields are confirmed by multiple enterprise platforms suggesting they are **industry-standard** and should be prioritized.

#### Fields Confirmed by 3+ Enterprise Platforms

| Domain | Field | Confirmed By | Priority |
|--------|-------|-------------|----------|
| **Product** | `sku`, `name/title`, `description`, `price`, `variants[]`, `images[]`, `attributes{}`, `status`, `created_at` | Shopify, commercetools, Salsify, Akeneo | **Critical** |
| **Product** | `brand/vendor`, `category_path[]`, `tags[]` | Shopify, commercetools, Salsify | **High** |
| **Product** | `slug/handle`, `version` | Shopify, commercetools | **Medium** |
| **Inventory** | `sku`, `available_qty`, `location_id`, `reserved_qty`, `last_updated` | Shopify, commercetools, SAP, Oracle, Manhattan | **Critical** |
| **Inventory** | `on_hand_qty`, `lead_time_days`, `reorder_point` | commercetools, SAP, Oracle | **High** |
| **Inventory** | `on_order_qty`, `unit_of_measure`, `lot_number` | SAP, Oracle, Manhattan | **High** |
| **Customer** | `email`, `first_name`, `last_name`, `phone`, `addresses[]` | Salesforce, Dynamics 365, commercetools | **Critical** |
| **Customer** | `date_of_birth`, `company`, `title`, `segments/groups` | Salesforce, Dynamics 365, commercetools | **High** |
| **Customer** | `loyalty_tier`, `lifetime_value`, `consent` | Dynamics 365, commercetools, industry standard | **High** |
| **Pricing** | `sku`, `amount`, `currency`, `effective_from/to` | Shopify, commercetools, SAP | **Critical** |
| **Pricing** | `channel`, `region`, `customer_group` | commercetools, SAP | **High** |
| **Order** | `order_id`, `customer_ref`, `status`, `total`, `currency`, `line_items[]`, `addresses` | Shopify, commercetools, Oracle, Manhattan | **Critical** |
| **Order** | `order_number`, `discount_codes[]`, compound status | Shopify, commercetools, Oracle | **High** |
| **Shipment** | `tracking_number`, `carrier`, `status`, `origin`, `destination`, `eta` | Shopify, Oracle, Manhattan | **Critical** |
| **Shipment** | `service_level`, `weight`, `line_items[]` (partial fulfillment) | Oracle, Manhattan | **High** |
| **PIM** | `sku`, `title`, `attributes{}`, `category_path[]`, `status`, `images[]` | Salsify, Akeneo | **Critical** |
| **DAM** | `asset_id`, `url`, `content_type`, `filename`, `dimensions`, `alt_text`, `tags[]` | Cloudinary, Salsify | **Critical** |

#### Enterprise Patterns NOT in Current Lib Schemas

These patterns are common across enterprise platforms but entirely absent from both lib schemas and proposed CRUD tables:

| Pattern | Platforms | Impact | Recommendation |
|---------|----------|--------|----------------|
| **Localized text fields** | commercetools (all text fields), Akeneo (locale+channel scoped attributes) | Cannot support multi-language retail | Add `localized_*` dict fields or locale-scoped attribute pattern |
| **Optimistic concurrency** | commercetools (`version` on every entity, required for updates) | Multi-agent write conflicts will cause data loss | Add `version: int` to all mutable entities |
| **Channel/Store scoping** | commercetools (`stores[]`, channel-scoped prices/inventory), Shopify (Markets) | Single-store assumption breaks multi-channel retail | Add `channel` or `store_id` scoping to products, prices, inventory |
| **Quantity tiers** | commercetools (price tiers), SAP (quantity scales) | Cannot support B2B wholesale pricing | Add `quantity_tiers[]` to prices table |
| **Partial fulfillment** | Shopify (multiple fulfillments per order), Manhattan (split shipments) | Cannot model orders shipped in multiple packages | Add `fulfillments[]` or order-shipment junction |
| **Attribute families/types** | Akeneo (families define required attributes), commercetools (ProductType) | No product schema enforcement or validation rules | Add `product_type` / `family` reference to products |
| **Completeness scoring** | Akeneo (% per locale/channel) | No PIM quality metrics | Add `completeness_score` to product_graph_nodes |

---

### 14.10 Recommended Schema Additions

Based on the enterprise grounding analysis, these fields should be added to the proposed tables from Section 5. Changes are grouped by impact level.

#### Tier 1 — High-Impact Additions (Required for Enterprise Connector Compatibility)

| Table | Add Field | Type | Justification |
|-------|-----------|------|---------------|
| `inventory` | `on_hand_qty` | `int` | SAP, Oracle, Manhattan all distinguish on-hand from available-to-promise |
| `inventory` | `on_order_qty` | `int` | Oracle, Manhattan track in-transit stock; needed by jit-replenishment |
| `inventory` | `unit_of_measure` | `str` | SAP, Oracle, Manhattan enforce UoM; needed for cross-system normalization |
| `contacts` | `addresses[]` | `list[dict]` | commercetools, Salesforce store structured address arrays; needed by logistics agents |
| `contacts` | `loyalty_tier` | `str` | Dynamics 365, `CustomerData` contract; needed by segmentation agent |
| `contacts` | `lifetime_value` | `float` | `CustomerData` contract; needed by campaign-intelligence |
| `contacts` | `segments[]` | `list[str]` | `CustomerData` contract, commercetools `customerGroupAssignments` |
| `contacts` | `consent{}` | `dict` | `CustomerData` contract; GDPR compliance requirement |
| `contacts` | `external_id` | `str` | Multi-connector identity mapping (commercetools `externalId`) |
| `prices` | `customer_group` | `str` | commercetools, SAP natively support group-specific pricing |
| `products` (enhanced) | `status` | `str` | Universal lifecycle field (active/draft/archived) |
| `products` (enhanced) | `version` | `int` | commercetools requires for optimistic concurrency; prevents agent write conflicts |
| `products` (enhanced) | `images[]` | `list[dict]` | Replace `image_url: str` with array; every platform supports multiple images |
| `products` (enhanced) | `category_path[]` | `list[str]` | Replace `category: str` with hierarchy; matches commercetools, Akeneo |

#### Tier 2 — Medium-Impact Additions (Improve Enterprise Alignment)

| Table | Add Field | Type | Justification |
|-------|-----------|------|---------------|
| `inventory` | `lot_number` | `str` | SAP `Batch`, Oracle `LotNumber`; required for regulated retail |
| `warehouse_stock` | `location_type` | `str` | Manhattan facility types (DC/store/vendor); supports routing decisions |
| `warehouse_stock` | `on_hand_qty` | `int` | Separate from `available` per enterprise standard |
| `contacts` | `date_of_birth` | `date` | Salesforce, Dynamics 365, commercetools; marketing personalization |
| `accounts` | `parent_account_id` | `str` | Salesforce, Dynamics 365 account hierarchy |
| `accounts` | `annual_revenue` | `float` | Salesforce, Dynamics 365; B2B account scoring |
| `interactions` | `priority` | `str` | Salesforce, Dynamics 365; support triage |
| `interactions` | `direction` | `str` | Standard CRM pattern (inbound/outbound) |
| `prices` | `quantity_tiers[]` | `list[dict]` | commercetools tiers, SAP quantity scales; B2B pricing |
| `prices` | `price_type` | `str` | Distinguish standard/promotional/clearance/employee |
| `products` (enhanced) | `slug` | `str` | Shopify `handle`, commercetools `slug`; SEO URLs |
| `products` (enhanced) | `source_system` | `str` | `ProductData` contract; multi-connector provenance |
| `shipment_events` | `carrier_code` | `str` | Raw carrier event code for multi-carrier normalization |
| `digital_assets` | `filename` | `str` | Cloudinary `original_filename`; `AssetData` contract field |
| `digital_assets` | `size_bytes` | `int` | Cloudinary `bytes`; `AssetData` contract field |
| `digital_assets` | `width`, `height` | `int` | Cloudinary dimensions; `AssetData` contract field |
| `digital_assets` | `format` | `str` | Cloudinary `format` (jpg/png/webp); file type management |
| `digital_assets` | `folder` | `str` | Cloudinary `folder`; asset organization |
| `product_graph_nodes` | `completeness_score` | `float` | Akeneo completeness %; PIM quality metric |
| `product_graph_nodes` | `family` | `str` | Akeneo product families; attribute schema enforcement |
| `product_graph_nodes` | `locale_data{}` | `dict` | Akeneo locale+channel scoped attributes |

#### Tier 3 — Future Considerations (Enterprise-Scale Patterns)

| Pattern | Tables Affected | Justification |
|---------|----------------|---------------|
| Localized text fields (`localized_names{}`, `localized_descriptions{}`) | `products`, `product_graph_nodes` | Required for multi-language retail (commercetools, Akeneo) |
| Channel/store scoping (`store_id`, `channel`) | `products`, `prices`, `inventory` | Required for multi-channel retail (commercetools Stores, Shopify Markets) |
| Attribute families/product types (`product_type_ref`) | `products`, `product_graph_nodes` | Required for schema enforcement (Akeneo families, commercetools ProductType) |
| Discount entities (separate `discounts` table) | New table | Enterprise discount management (Shopify Discounts API, commercetools Cart Discounts, SAP Condition Types) |
| Fulfillment junction (`order_fulfillments`) | New table | Partial fulfillment support (Shopify multiple fulfillments, Manhattan split shipments) |
| Order compound status (`financial_status`, `fulfillment_status`, `shipment_status`) | `orders` | Shopify, commercetools both use multi-dimensional status |
| Order human-readable number (`order_number`) | `orders` | Every platform assigns a display number (#1001, ORD-2024-001) |

> **Implementation priority**: Tier 1 fields should be included in the initial table creation PRs proposed in Section 12. Tier 2 fields should be filed as follow-up issues. Tier 3 patterns should be tracked in the architecture roadmap (issues #79–84) and implemented when multi-region/multi-channel support is prioritized.
