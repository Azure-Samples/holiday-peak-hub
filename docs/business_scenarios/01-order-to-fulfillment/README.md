# Business Scenario 01: Order-to-Fulfillment

## Overview

The **Order-to-Fulfillment** process is the backbone of any e-commerce operation. It encompasses the complete journey from the moment a customer submits an order to the point where a shipment is scheduled and a confirmation is sent. In Holiday Peak Hub, this process is orchestrated through **SAGA Choreography** — a pattern where each service reacts to events and publishes its own events, maintaining data consistency across distributed services without a central coordinator.

## Business Importance for Retail

Order fulfillment directly impacts:

| Metric | Impact |
|--------|--------|
| **Revenue** | Failed orders = lost sales. During peak (Black Friday, Cyber Monday), even 1% failure rate on 100K orders = 1,000 lost transactions |
| **Customer Trust** | Overselling (accepting orders without stock) destroys brand credibility |
| **Operational Cost** | Manual intervention for failed orders costs $5–15 per incident |
| **Cash Flow** | Payment capture timing affects working capital — delayed capture = delayed revenue |
| **Inventory Accuracy** | Stock reservation prevents double-selling across channels |

During **holiday peak seasons**, order volumes can spike 5–10× normal levels. The order-to-fulfillment pipeline must:
- Scale elastically without human intervention
- Maintain consistency across inventory, payment, and logistics
- Recover gracefully from partial failures (e.g., payment declined after stock reserved)

## Traditional Challenges

1. **Tight Coupling**: Monolithic checkout flows fail entirely if any subsystem is down
2. **Overselling**: Without real-time reservation, concurrent orders can exceed available stock
3. **Payment–Inventory Mismatch**: Stock reserved but payment fails → inventory locked, other customers blocked
4. **No Compensation Logic**: When failures occur mid-flow, manual cleanup is required
5. **Scaling Bottleneck**: Synchronous order pipelines become the bottleneck during traffic spikes

## How Holiday Peak Hub Addresses It

### SAGA Choreography Pattern

Instead of a centralized orchestrator, each agent **reacts to events** and **publishes outcomes**. This creates a resilient, loosely coupled pipeline:

```
Customer → OrderCreated → InventoryReserved → PaymentProcessed → ShipmentScheduled → Confirmation
                                                    ↓ (failure)
                                              PaymentFailed → InventoryReleased → Order Cancelled
```

### Key Architectural Decisions

- **Event-Driven**: All inter-service communication via Azure Event Hubs (5 topics)
- **Compensation**: Automatic stock release on payment failure — no manual intervention
- **Idempotent Handlers**: Each agent can safely process the same event multiple times
- **SLM-First Routing**: Simple reservations handled by SLM; complex scenarios (partial stock, substitutions) escalated to LLM

## Process Flow

### Happy Path

1. **Customer submits order** via `/checkout` page → CRUD Service receives `POST /api/orders`
2. **CRUD Service** validates the order, creates an order record (status: `pending`), publishes `OrderCreated` to `order-events` topic
3. **Inventory Reservation Agent** (`inventory-reservation-validation`) receives `OrderCreated`:
   - Checks stock availability across warehouses
   - Reserves requested quantities
   - Publishes `InventoryReserved` to `inventory-events` topic
4. **Payment Service** receives `InventoryReserved`:
   - Captures payment via payment provider (Stripe/PayPal)
   - On success: publishes `PaymentProcessed` to `payment-events` topic
5. **Logistics Carrier Selection Agent** (`logistics-carrier-selection`) receives `PaymentProcessed`:
   - Evaluates available carriers (cost, speed, reliability)
   - Selects optimal carrier using AI model
   - Schedules shipment
   - Publishes `ShipmentScheduled` to `order-events` topic
6. **CRUD Service** receives `ShipmentScheduled`:
   - Updates order status to `processing`
   - Sends confirmation email to customer
7. **CRM Profile Aggregation Agent** (`crm-profile-aggregation`) receives `OrderCreated`:
   - Updates customer lifetime value (LTV)
   - Triggers segmentation recalculation

### Compensation Path (Payment Failure)

1. **Payment Service** fails to capture payment → publishes `PaymentFailed` to `payment-events` topic
2. **Inventory Reservation Agent** receives `PaymentFailed`:
   - Releases all reserved stock for the order
   - Publishes `InventoryReleased` to `inventory-events` topic
3. **CRUD Service** receives `PaymentFailed`:
   - Updates order status to `payment_failed`
   - Notifies customer with retry options

## Agents Involved

| Agent | Role in Process | Event Subscription | Event Published |
|-------|----------------|-------------------|-----------------|
| `inventory-reservation-validation` | Reserve/release stock | `order-events` (OrderCreated), `payment-events` (PaymentFailed) | `InventoryReserved`, `InventoryReleased` |
| `logistics-carrier-selection` | Select carrier, schedule shipment | `payment-events` (PaymentProcessed) | `ShipmentScheduled` |
| `crm-profile-aggregation` | Update customer LTV/profile | `order-events` (OrderCreated) | — |
| `crm-segmentation-personalization` | Recalculate customer segment | CRM internal trigger | — |

## Event Hub Topology

```
order-events          ──→  inventory-reservation-validation, crm-profile-aggregation
inventory-events      ──→  (downstream consumers)
payment-events        ──→  logistics-carrier-selection, inventory-reservation-validation
order-events          ←──  logistics-carrier-selection (ShipmentScheduled)
```

## Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| Order-to-confirmation latency | < 5 seconds | Time from POST /orders to confirmation email |
| Inventory reservation accuracy | 99.9% | Reserved vs. actually available |
| Payment capture success rate | > 97% | Successful captures / total attempts |
| Compensation execution time | < 2 seconds | Time from PaymentFailed to InventoryReleased |
| Peak throughput | 1,000+ orders/min | Sustained during Black Friday |

## BPMN Diagram

See [order-to-fulfillment.drawio](order-to-fulfillment.drawio) for the complete BPMN 2.0 process diagram showing:
- **6 pools**: Customer, CRUD Service, Event Hub, Inventory Agent, Payment Service, Logistics Agent
- **Happy path**: left-to-right flow through all pools
- **Compensation path**: Payment failure triggers stock release
- **Message flows**: Dashed arrows showing async event communication
