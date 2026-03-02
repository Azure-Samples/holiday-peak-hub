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
| **Payments** | **Medium** | Payment processing is simulated. Stripe SDK unused. `GET /payments/{id}` returns 501. |
| **Tickets** | **Medium** | Read-only. No create endpoint. Agent ticket creation returns "unsupported". |
| **PIM/DAM** | **Medium** | Issue #34 proposes a full Product Graph + DAM workflow — no CRUD models exist. |
| **Schema alignment** | **Medium** | `id` vs `sku`, `name` vs `title`, `category_id` vs `category` mismatches throughout. |

---

## 2. Current CRUD Service Inventory

### 2.1 Postgres Tables (JSONB-backed)

All tables share the universal schema: `(id TEXT PK, partition_key TEXT, data JSONB, created_at TIMESTAMPTZ, updated_at TIMESTAMPTZ)`.

| Table | Repository | CRUD Endpoints | Write Ops |
|-------|-----------|---------------|-----------|
| `products` | `ProductRepository` | `GET /api/products`, `GET /api/products/{id}` | Seed only |
| `users` | `UserRepository` | `GET /api/users/me`, `PATCH /api/users/me` | Auto-create from JWT |
| `cart` | `CartRepository` | `GET /api/cart`, `POST /api/cart/items`, `DELETE /api/cart/items/{id}`, `DELETE /api/cart` | Full CRUD |
| `orders` | `OrderRepository` | `GET /api/orders`, `GET /api/orders/{id}`, `POST /api/orders`, `PATCH /api/orders/{id}/cancel` | Create + Cancel |
| `checkout_sessions` | `CheckoutSessionRepository` | `POST /acp/checkout/sessions`, `GET .../{id}`, `PATCH .../{id}`, `POST .../complete`, `DELETE .../{id}` | Full CRUD |
| `payment_tokens` | `PaymentTokenRepository` | `POST /acp/payments/delegate` | Create only |
| `categories` | Inline `CategoryRepository` | `GET /api/categories`, `GET /api/categories/{id}` | Seed only |
| `reviews` | Inline `ReviewRepository` | `GET /api/reviews`, `POST /api/reviews`, `DELETE /api/reviews/{id}` | Create + Delete |
| `tickets` | Inline `TicketRepository` | `GET /api/staff/tickets`, `GET /api/staff/tickets/{id}` | **Read-only** |
| `returns` | Inline `ReturnRepository` | `GET /api/staff/returns`, `PATCH /api/staff/returns/{id}/approve` | Approve only |
| `shipments` | Inline `ShipmentRepository` | `GET /api/staff/shipments`, `GET /api/staff/shipments/{id}` | **Read-only** |

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
2. **`GET /payments/{id}` returns 501** — Not implemented.
3. **`PaymentMethodRepository` is an empty class** — `pass` only.
4. **No `payments` table** — Payments are created in-memory and attached to order records.
5. **No payment history or refund tracking**.
6. **ACP checkout sessions not connected to checkout agent** — Agent validates raw item lists, not ACP session models.

---

### 4.8 Support Tickets & Returns

#### Gaps

1. **Tickets are read-only** — No `POST /api/tickets` for customer or agent ticket creation.
2. **`BaseCRUDAdapter._create_ticket()` returns `unsupported_operation`** — All agents' ticket creation attempts fail silently.
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
| #80 — Event-Driven Connector Sync | CDC-based sync between connectors and CRUD data |
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
| 33 | No middleware.ts for route protection | Enhancement | Security gap |
| 34 | PIM/DAM Agentic Workflow | Feature | Requires new CRUD models |

### Connector Issues (#36-78) — 43 issues

Grouped by domain: Commerce (7), Inventory/SCM (6), CRM/CDP (6), PIM (6), DAM (4), Data/Analytics (5), Integration (4), Identity (1), Privacy (1), Workforce (3).

### Architecture Issues (#79-84) — 6 issues

Connector Registry, Event-Driven Sync, Multi-Tenant Config, Protocol Evolution, Data Enrichment Guardrails, Reference Architecture Patterns.
