# Event Hub topology matrix

_Last updated: 2026-04-02_

## Purpose

This document is the architecture coverage contract for Event Hubs topology alignment (issue #299). It records topic-level publisher/subscriber reality and expected wiring coverage.

## Active topology

| Topic | Primary publishers | Active subscribers |
|---|---|---|
| `order-events` | CRUD `orders` routes, ACP checkout completion | `crm-*`, `ecommerce-*`, `inventory-*`, `logistics-*`, `product-management-*` services |
| `payment-events` | CRUD `payments` routes, Stripe webhook, ACP checkout completion | `crm-campaign-intelligence` |
| `return-events` | CRUD customer/staff returns lifecycle routes | `logistics-returns-support`, `crm-support-assistance` |
| `inventory-events` | CRUD `cart` route (successful reservation publish path) | `ecommerce-checkout-support`, `inventory-health-check`, `inventory-alerts-triggers`, `inventory-jit-replenishment` |
| `user-events` | CRUD `users` route (`PATCH /api/users/me` as `UserUpdated`) | `crm-campaign-intelligence`, `crm-profile-aggregation` |
| `shipment-events` | CRUD integration (`publish_shipment_created`) | `logistics-carrier-selection`, `logistics-eta-computation`, `ecommerce-order-status` |
| `product-events` | CRUD integration (`publish(..., ProductUpdated, ...)`) | `ecommerce-catalog-search`, `ecommerce-product-detail-enrichment`, `product-management-*` services |
| `completeness-jobs` | `truth-ingestion` completeness adapter publish path | `product-management-consistency-validation` (`completeness-engine`) |

## Coverage contract status

| Topic | Contract expectation | Current state | Coverage status | Implementation issue path |
|---|---|---|---|---|
| `order-events` | CRUD emits order lifecycle events and agents consume | Publisher/subscriber paths active | Aligned | Continue under feature work
| `payment-events` | CRUD/webhook emits payment events and CRM campaign flow consumes | Publisher/subscriber paths active | Aligned | Continue under feature work
| `return-events` | CRUD emits returns lifecycle and at least one returns-aware agent consumes | `logistics-returns-support` and `crm-support-assistance` subscribed | Aligned | Continue under feature work
| `inventory-events` | CRUD emits reservation/release events and inventory/checkout agents consume | Reservation path active; broader inventory mutation paths still partial | Partially aligned | Follow-up implementation work from #299
| `user-events` | CRUD emits user registration/profile update events and CRM agents consume | Profile update publish active (`PATCH /api/users/me`); explicit registration publish remains pending | Partially aligned | Follow-up implementation work from #299
| `shipment-events` | CRUD emits shipment lifecycle and logistics/order-status agents consume | Subscribers wired in logistics + order-status services | Aligned | #446
| `product-events` | CRUD product lifecycle events are published and product/cat services consume | Canonical topic schema + CRUD publisher wiring active | Aligned | #445
| `completeness-jobs` | Truth ingestion publishes completeness jobs and validation service consumes | Publisher/subscriber paths active with dedicated consumer group | Aligned | #604

## Cross-issue dependency notes

- #340, #342, and #349 are not blocked by #299 because they target the intelligent-search bounded context (Cosmos + AI Search + MCP indexing), not the retail choreography topics above.
- #341 introduces `search-enrichment-jobs` Event Hub infrastructure and should adopt the same publisher/subscriber coverage-contract pattern documented here.
- #299 remains the architecture baseline for CRUD-to-agent topology truthfulness; implementation issues should reference this matrix when adding or wiring Event Hub topics.

## Notes

- Product-domain event publishing remains pending a dedicated product mutation route set in CRUD.
- Saga compensation framework is standardized in `holiday_peak_lib.utils.compensation`, with inventory reservation rollback as a reference integration path (#447).
- This matrix is intended as a living architecture artifact and should be updated alongside topology changes.
