# Business Scenario 04: Inventory Optimization

## Executive Statement

Predictive inventory control loop that balances availability, working capital, and replenishment speed under volatile demand.

## Capability Mapping

| Capability | Business Leverage |
| --- | --- |
| Inventory health monitoring | Early detection of stock integrity risks |
| JIT replenishment intelligence | Smarter reorder quantities and timing |
| Alerts and triggers | Prioritized operational intervention |
| Checkout scarcity integration | Conversion uplift with real-time urgency context |

## Outcome Targets

| North-Star KPI | Target |
| --- | --- |
| Stockout rate on priority SKUs | < 1.5% |
| Replenishment lead-time adherence | > 95% |
| Inventory anomaly detection precision | > 90% |
| Working-capital efficiency uplift | +10% YoY |

## Executive Flow

```mermaid
flowchart LR
   A[Demand + Order Signals] --> B[Inventory Health Check]
   B --> C{Threshold Breach?}
   C -->|Yes| D[JIT Replenishment Decision]
   D --> E[PO / Transfer Recommendation]
   E --> F[Alerts + Operations Action]
   F --> G[Inventory Position Update]
   C -->|No| H[Continuous Monitoring]
   G --> H

   classDef a fill:#0B84F3,color:#fff,stroke:#085ea8
   classDef b fill:#00A88F,color:#fff,stroke:#0b6e5f
   classDef c fill:#F39C12,color:#fff,stroke:#af6f0c
   classDef d fill:#8E44AD,color:#fff,stroke:#5b2a70
   class A,B a
   class D,E,F,G,H b
   class C c
```

## Implemented Reservation Lifecycle (Issue #216)

Checkout now uses an explicit reservation lifecycle in the CRUD API to protect stock integrity during payment.

1. `POST /api/inventory/reservations` creates per-item holds (`status=created`, reason `checkout_hold`).
2. If checkout setup fails after partial holds, the UI rolls back with `POST /api/inventory/reservations/{id}/release`.
3. After Stripe confirmation and `POST /api/payments/confirm-intent`, the UI finalizes holds with `POST /api/inventory/reservations/{id}/confirm`.
4. On checkout abandonment (before payment confirmation), outstanding holds are released on page teardown.

State model implemented in CRUD:

- `created -> confirmed` (successful payment finalization)
- `created -> released` (rollback/abandonment)
- `confirmed` and `released` are terminal states
- Invalid transitions (`released -> confirmed`, `confirmed -> released`) return `409`
