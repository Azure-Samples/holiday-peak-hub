# Business Scenarios

This folder documents the key **business processes** of Holiday Peak Hub, explaining their importance for retail operations and how the platform's agentic architecture transforms each one.

Each scenario includes:
- A **Markdown document** describing the business context, traditional challenges, and how Holiday Peak Hub addresses them
- A **draw.io BPMN diagram** showing the process flow with proper BPMN 2.0 notation (pools, lanes, gateways, events)

## Scenario Index

| # | Scenario | Domain | Key Pattern | Agents Involved |
|---|----------|--------|-------------|-----------------|
| 1 | [Order-to-Fulfillment](01-order-to-fulfillment/) | E-commerce | SAGA Choreography | Reservation, Carrier Selection, Profile Aggregation |
| 2 | [Product Discovery & Enrichment](02-product-discovery-enrichment/) | E-commerce | Sync + Async | Catalog Search, Product Enrichment, Cart Intelligence |
| 3 | [Returns & Refund Processing](03-returns-refund-processing/) | Logistics/CRM | Event-Driven | Returns Support, Inventory Health Check, Support Assistance |
| 4 | [Inventory Optimization](04-inventory-optimization/) | Inventory | Event-Driven | Health Check, JIT Replenishment, Alerts/Triggers |
| 5 | [Shipment & Delivery Tracking](05-shipment-delivery-tracking/) | Logistics | Event-Driven | ETA Computation, Carrier Selection, Route Detection |
| 6 | [Customer 360 & Personalization](06-customer-360-personalization/) | CRM | Event-Driven | Profile Aggregation, Segmentation, Campaign Intelligence |
| 7 | [Product Lifecycle Management](07-product-lifecycle-management/) | Product Mgmt | Event-Driven | Normalization, ACP Transform, Consistency Validation |
| 8 | [Customer Support Resolution](08-customer-support-resolution/) | CRM | RAG + Events | Support Assistance, Returns Support |

## BPMN Notation Reference

All diagrams use **BPMN 2.0** notation:

| Symbol | Meaning |
|--------|---------|
| Thin circle | Start Event |
| Bold circle | End Event |
| Double-line circle | Intermediate Event (message, timer) |
| Rounded rectangle | Task / Activity |
| Diamond (X) | Exclusive Gateway (decision) |
| Diamond (+) | Parallel Gateway (fork/join) |
| Envelope icon | Message Event (async) |
| Solid arrow | Sequence Flow (within pool) |
| Dashed arrow | Message Flow (between pools) |
| Horizontal band | Pool / Swimlane |

## Architecture Mapping

These business scenarios map directly to the [C4 Component diagrams](../architecture/diagrams/):
- **Synchronous flows** use CRUD REST endpoints with circuit-breaker fallback
- **Asynchronous flows** use Azure Event Hubs (AMQP) with SAGA choreography
- **Agent decisions** are powered by Microsoft Foundry (SLM-first, LLM upgrade)
- **State** is managed through three-tier memory (Redis → Cosmos DB → Blob)
