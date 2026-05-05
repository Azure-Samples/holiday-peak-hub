# Apps Directory

> Last Updated: 2026-04-30

This directory contains the deployable Holiday Peak Hub services:
- 1 transactional microservice (`crud-service`)
- 26 Python agent/automation services
- 1 Next.js frontend (`ui`)

## App Inventory

| App | Type | Bounded Context | Purpose | Event Hub Subscriptions |
|-----|------|----------------|---------|------------------------|
| `crm-campaign-intelligence` | Agent | CRM | Generates campaign intelligence from CRM and funnel context | `user-events`, `order-events`, `payment-events` |
| `crm-profile-aggregation` | Agent | CRM | Builds unified customer profiles from distributed CRM data | `user-events`, `order-events` |
| `crm-segmentation-personalization` | Agent | CRM | Segments customers and suggests personalization actions | `order-events` |
| `crm-support-assistance` | Agent | CRM | Produces support-assist context and recommended actions | `order-events`, `return-events` |
| `crud-service` | Microservice | Platform | Owns transactional CRUD APIs and publishes domain events to 7 Event Hub topics | N/A (publisher) |
| `ecommerce-cart-intelligence` | Agent | eCommerce | Scores cart risk and recommends conversion improvements | `order-events` |
| `ecommerce-catalog-search` | Agent | eCommerce | Delivers catalog discovery via Azure AI Search with intent-grounding | `product-events` |
| `ecommerce-checkout-support` | Agent | eCommerce | Evaluates checkout blockers and completion guidance | `order-events`, `inventory-events` |
| `ecommerce-order-status` | Agent | eCommerce | Provides order and shipment status intelligence | `order-events`, `shipment-events` |
| `ecommerce-product-detail-enrichment` | Agent | eCommerce | Enriches product detail context for shopping experiences | `product-events` |
| `inventory-alerts-triggers` | Agent | Inventory | Detects inventory alerts and trigger conditions | `inventory-events` |
| `inventory-health-check` | Agent | Inventory | Assesses inventory health and anomaly signals | `order-events`, `inventory-events` |
| `inventory-jit-replenishment` | Agent | Inventory | Recommends just-in-time replenishment actions | `inventory-events` |
| `inventory-reservation-validation` | Agent | Inventory | Validates reservation requests against stock conditions | `order-events` |
| `logistics-carrier-selection` | Agent | Logistics | Recommends carrier options and trade-offs | `order-events`, `shipment-events` |
| `logistics-eta-computation` | Agent | Logistics | Computes ETA projections and delay risk signals | `order-events`, `shipment-events` |
| `logistics-returns-support` | Agent | Logistics | Guides returns-related operational decisions | `order-events`, `return-events` |
| `logistics-route-issue-detection` | Agent | Logistics | Detects route issues and recovery recommendations | `order-events` |
| `product-management-acp-transformation` | Agent | Product Management | Transforms product data into ACP-aligned payloads | `product-events` |
| `product-management-assortment-optimization` | Agent | Product Management | Ranks and optimizes assortment decisions | `order-events`, `product-events` |
| `product-management-consistency-validation` | Agent | Product Management | Evaluates product consistency and completeness signals | `completeness-jobs` (platform) |
| `product-management-normalization-classification` | Agent | Product Management | Normalizes and classifies product attributes | `product-events` |
| `search-enrichment-agent` | Agent | Search | Enriches search-oriented product content asynchronously | `search-enrichment-jobs` (platform) |
| `truth-enrichment` | Agent | Truth Layer | Generates proposed truth-layer attribute enrichments | `enrichment-jobs` (platform) |
| `truth-export` | Agent | Truth Layer | Exports truth-layer attributes to downstream protocols/systems | `export-jobs` (platform) |
| `truth-hitl` | Agent | Truth Layer | Supports human-in-the-loop review and approval queues | `hitl-jobs` (platform) |
| `truth-ingestion` | Agent | Truth Layer | Ingests source product data into truth workflows | `ingest-jobs` (platform) |
| `ui` | Frontend | Portal | Next.js 15 portal for admin, operations, and retail workflows | N/A |

## Common Agent Service Pattern

All 26 Python agent services follow the same structural pattern using `create_standard_app` from `holiday_peak_lib`:

```python
from holiday_peak_lib import create_standard_app
from holiday_peak_lib.utils import EventHubSubscription
from my_service.agents import MyAgent, register_mcp_tools
from my_service.event_handlers import build_event_handlers

SERVICE_NAME = "my-service-name"
app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name=SERVICE_NAME,
    agent_class=MyAgent,
    mcp_setup=register_mcp_tools,
    subscriptions=[EventHubSubscription("topic-events", "consumer-group")],
    handlers=build_event_handlers(),
)
```

### Standard Endpoints (all agents)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/invoke` | Synchronous agent invocation |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe (includes Foundry connectivity) |
| GET | `/self-healing/status` | Self-healing kernel state |
| GET | `/self-healing/incidents` | Active incident list |
| POST | `/self-healing/reconcile` | Trigger manual reconciliation |
| * | `/mcp/*` | MCP tool endpoints (agent-to-agent) |

### Technology Stack

- **Runtime**: Python 3.13, FastAPI, uvicorn
- **Package manager**: `uv`
- **AI Runtime**: Microsoft Agent Framework (MAF) >=1.0.1 GA
- **Model Routing**: GPT-5-nano (SLM/fast) → GPT-4o (LLM/rich)
- **Memory**: Redis (hot) / Cosmos DB (warm) / Blob Storage (cold)
- **Events**: Azure Event Hubs (8 topics)
- **Agent Protocol**: MCP via `FastAPIMCPServer`
- **Observability**: OpenTelemetry → Azure Monitor

## Event Hub Topics

| Topic | Publisher | Subscribers |
|-------|----------|-------------|
| `order-events` | CRUD Service | 11 agents |
| `payment-events` | CRUD Service | 1 agent |
| `return-events` | CRUD Service | 2 agents |
| `inventory-events` | CRUD Service | 4 agents |
| `shipment-events` | CRUD Service | 3 agents |
| `product-events` | CRUD Service | 4 agents |
| `user-events` | CRUD Service | 2 agents |
| `enrichment-jobs` | Platform/HITL | 1 agent (truth-enrichment) |
| `export-jobs` | Platform/HITL | 1 agent (truth-export) |
| `hitl-jobs` | Platform | 1 agent (truth-hitl) |
| `ingest-jobs` | Platform | 1 agent (truth-ingestion) |
| `completeness-jobs` | Platform | 1 agent (consistency-validation) |
| `search-enrichment-jobs` | Platform/HITL | 1 agent (search-enrichment-agent) |
