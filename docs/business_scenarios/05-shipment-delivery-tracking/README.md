# Business Scenario 05: Shipment & Delivery Tracking

## Executive Statement

Proactive logistics intelligence pipeline that improves ETA confidence, reduces WISMO pressure, and optimizes carrier economics.

## Capability Mapping

| Capability | Business Leverage |
| --- | --- |
| Carrier selection intelligence | Lower cost-to-ship with SLA compliance |
| ETA computation | Accurate expectation setting and trust retention |
| Route issue detection | Early disruption detection and mitigation |
| CRM notification context | Proactive communication and support deflection |

## Outcome Targets

| North-Star KPI | Target |
| --- | --- |
| ETA prediction accuracy | > 92% |
| WISMO ticket reduction | > 60% |
| Late-delivery incident rate | < 5% |
| Carrier cost optimization gain | 8–15% |

## Executive Flow

```mermaid
flowchart LR
   A[Order Ready to Ship] --> B[Carrier Selection]
   B --> C[Shipment Dispatch]
   C --> D[ETA Computation]
   D --> E[In-Transit Signal Monitoring]
   E --> F{Route Risk Detected?}
   F -->|Yes| G[Delay Prediction + Replan]
   G --> H[Proactive Customer Notification]
   F -->|No| I[On-Time Tracking Updates]
   H --> J[Delivery Confirmation]
   I --> J

   classDef a fill:#0B84F3,color:#fff,stroke:#085ea8
   classDef b fill:#00A88F,color:#fff,stroke:#0b6e5f
   classDef c fill:#F39C12,color:#fff,stroke:#af6f0c
   classDef d fill:#8E44AD,color:#fff,stroke:#5b2a70
   class A,B,C,D,E a
   class G,H,I,J b
   class F c
```
