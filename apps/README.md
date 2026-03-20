# Apps Directory

This directory contains the deployable Holiday Peak Hub services:
- 1 transactional microservice (`crud-service`)
- 26 Python agent/automation services
- 1 Next.js frontend (`ui`)

## App Inventory

| App | Type | Purpose |
|---|---|---|
| `crm-campaign-intelligence` | Agent service | Generates campaign intelligence from CRM and funnel context. |
| `crm-profile-aggregation` | Agent service | Builds unified customer profiles from distributed CRM data. |
| `crm-segmentation-personalization` | Agent service | Segments customers and suggests personalization actions. |
| `crm-support-assistance` | Agent service | Produces support-assist context and recommended actions. |
| `crud-service` | Microservice | Owns transactional CRUD APIs and event publishing. |
| `ecommerce-cart-intelligence` | Agent service | Scores cart risk and recommends conversion improvements. |
| `ecommerce-catalog-search` | Agent service | Delivers catalog discovery and ACP-aligned search responses. |
| `ecommerce-checkout-support` | Agent service | Evaluates checkout blockers and completion guidance. |
| `ecommerce-order-status` | Agent service | Provides order and shipment status intelligence. |
| `ecommerce-product-detail-enrichment` | Agent service | Enriches product detail context for shopping experiences. |
| `inventory-alerts-triggers` | Agent service | Detects inventory alerts and trigger conditions. |
| `inventory-health-check` | Agent service | Assesses inventory health and anomaly signals. |
| `inventory-jit-replenishment` | Agent service | Recommends just-in-time replenishment actions. |
| `inventory-reservation-validation` | Agent service | Validates reservation requests against stock conditions. |
| `logistics-carrier-selection` | Agent service | Recommends carrier options and trade-offs. |
| `logistics-eta-computation` | Agent service | Computes ETA projections and delay risk signals. |
| `logistics-returns-support` | Agent service | Guides returns-related operational decisions. |
| `logistics-route-issue-detection` | Agent service | Detects route issues and recovery recommendations. |
| `product-management-acp-transformation` | Agent service | Transforms product data into ACP-aligned payloads. |
| `product-management-assortment-optimization` | Agent service | Ranks and optimizes assortment decisions. |
| `product-management-consistency-validation` | Agent service | Evaluates product consistency and completeness signals. |
| `product-management-normalization-classification` | Agent service | Normalizes and classifies product attributes. |
| `search-enrichment-agent` | Agent service | Enriches search-oriented product content asynchronously. |
| `truth-enrichment` | Agent service | Generates proposed truth-layer attribute enrichments. |
| `truth-export` | Agent service | Exports truth-layer attributes to downstream protocols/systems. |
| `truth-hitl` | Agent service | Supports human-in-the-loop review and approval queues. |
| `truth-ingestion` | Agent service | Ingests source product data into truth workflows. |
| `ui` | Frontend | Next.js portal for admin, operations, and retail workflows. |

## Common Service Pattern

Most Python app services are FastAPI services built with `build_service_app`, exposing synchronous interfaces and background Event Hub processing. Configuration is environment-driven, including Foundry model settings and optional Redis/Cosmos/Blob memory tiers.
