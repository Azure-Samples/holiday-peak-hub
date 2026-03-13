# Business Scenario 01: Order-to-Fulfillment

## Executive Statement

High-throughput commerce pipeline that protects revenue, enforces stock integrity, and delivers near-real-time confirmation under peak demand.

## Capability Mapping

| Capability | Business Leverage |
| --- | --- |
| CRUD transactional core | Trusted order capture and state transitions |
| Inventory reservation validation | Oversell prevention and inventory confidence |
| Carrier selection intelligence | Cost-speed optimization per shipment |
| Profile aggregation | Immediate post-purchase customer intelligence |

## Outcome Targets

| North-Star KPI | Target |
| --- | --- |
| Order-to-confirmation latency | < 5s p95 |
| Reservation integrity | > 99.9% |
| Payment-to-shipment continuity | > 97% |
| Compensation cycle (failure path) | < 2s |

## Executive Flow

```mermaid
flowchart LR
   A[Customer Checkout Intent] --> B[CRUD Order Commit]
   B --> C[Inventory Reservation]
   C --> D[Payment Capture]
   D --> E[Carrier Optimization]
   E --> F[Fulfillment Confirmation]
   B --> G[Profile Intelligence Update]

   D --> H{Payment Failure?}
   H -->|Yes| I[Auto Compensation\nRelease Inventory]
   I --> J[Customer Retry Path]

   classDef a fill:#0B84F3,color:#fff,stroke:#085ea8
   classDef b fill:#00A88F,color:#fff,stroke:#0b6e5f
   classDef c fill:#F39C12,color:#fff,stroke:#af6f0c
   classDef d fill:#8E44AD,color:#fff,stroke:#5b2a70
   classDef e fill:#D35400,color:#fff,stroke:#8e3a00
   class A,B a
   class C,D,E,F,G b
   class H c
   class I,J e
```

## Real Checkout Contract (Issue #210)

Checkout in this scenario runs on the live CRUD payment path (no stubbed success responses).

1. `POST /api/checkout/validate` validates cart and inventory warnings/errors.
2. `POST /api/orders` creates the order record.
3. `POST /api/payments/intent` creates a Stripe PaymentIntent for client-side confirmation.
4. Frontend confirms payment with Stripe.js.
5. `POST /api/payments/confirm-intent` reconciles the confirmed PaymentIntent back to the order, persists payment, sets order status to `paid`, and publishes payment-processed event when transitioning to paid.
6. `GET /api/payments/{payment_id}` supports post-checkout payment retrieval (customer ownership, staff/admin override).

Business impact: confirmation is tied to provider-backed payment state and auditable order/payment linkage, preserving payment-to-shipment continuity targets.
