# Business Scenarios

Executive scenario playbook for Holiday Peak Hub: each scenario is a value stream, each capability is mapped to a primary business outcome, and each flow is represented with a visual executive narrative.

## Scenario Portfolio

| # | Scenario | Outcome Theme | Flow Model |
|---|---|---|---|
| 1 | [Order-to-Fulfillment](01-order-to-fulfillment/) | Revenue Protection + Fulfillment Velocity | SAGA Orchestration |
| 2 | [Product Discovery & Enrichment](02-product-discovery-enrichment/) | Conversion Acceleration + Catalog Intelligence | Hybrid Sync/Async |
| 3 | [Returns & Refund Processing](03-returns-refund-processing/) | Margin Recovery + Trust Retention | Event-Driven Reverse Logistics |
| 4 | [Inventory Optimization](04-inventory-optimization/) | Availability Precision + Working-Capital Efficiency | Predictive Control Loop |
| 5 | [Shipment & Delivery Tracking](05-shipment-delivery-tracking/) | On-Time Confidence + WISMO Deflection | Proactive Logistics Intelligence |
| 6 | [Customer 360 & Personalization](06-customer-360-personalization/) | LTV Expansion + Segment Intelligence | Real-Time CRM Mesh |
| 7 | [Product Lifecycle Management](07-product-lifecycle-management/) | Data Quality at Scale + Time-to-Shelf Speed | Quality-Gated Product Pipeline |
| 8 | [Customer Support Resolution](08-customer-support-resolution/) | Cost-to-Serve Reduction + CSAT Lift | AI-First Resolution Loop |

## Capability-to-Scenario Mapping

| Capability Cluster | Primary Scenario | Supporting Platforms |
|---|---|---|
| CRUD transactional core | 1 | APIM, PostgreSQL, Event Hubs |
| Catalog search + enrichment | 2 | Azure AI Search, Foundry, Redis |
| Returns + refund automation | 3 | Logistics agents, payment flow, support context |
| Inventory health + JIT + alerts | 4 | Event Hubs, Redis, Cosmos DB |
| ETA + route detection + carrier strategy | 5 | Carrier APIs, logistics telemetry |
| Profile + segmentation + campaign intelligence | 6 | Cosmos DB, Foundry, CRM adapters |
| Normalization + ACP + validation + assortment | 7 | Product-management agents, truth services |
| Support assistance + escalation intelligence | 8 | CRM support agent, order status, KB loop |

## Executive Flow Map

```mermaid
flowchart LR
	A[Digital Demand Signals] --> B[Scenario Value Streams]
	B --> C[Agentic Decision Layer]
	C --> D[Operational Systems of Record]
	D --> E[Executive Outcomes Dashboard]

	classDef c1 fill:#0B84F3,color:#fff,stroke:#085ea8
	classDef c2 fill:#00A88F,color:#fff,stroke:#0b6e5f
	classDef c3 fill:#F39C12,color:#fff,stroke:#af6f0c
	classDef c4 fill:#8E44AD,color:#fff,stroke:#5b2a70
	class A,B c1
	class C c2
	class D c3
	class E c4
```
