# Business Scenario 05: Shipment & Delivery Tracking

## Overview

**Shipment & Delivery Tracking** covers the full logistics lifecycle from carrier selection through delivery — including ETA computation, real-time route monitoring, delay detection, and proactive customer notification. Holiday Peak Hub uses a chain of specialized logistics agents that react to shipping events and provide continuous visibility into shipment status.

## Business Importance for Retail

| Metric | Impact |
|--------|--------|
| **WISMO Reduction** | "Where Is My Order?" accounts for 30–50% of customer service contacts; proactive tracking reduces this by 70% |
| **Carrier Cost** | AI carrier selection can reduce shipping costs by 8–15% through multi-carrier optimization |
| **Delivery Success** | Proactive delay notification reduces failed deliveries by 25% (customer can adjust) |
| **NPS Score** | Accurate delivery estimates improve Net Promoter Score by 10–15 points |
| **Peak Reliability** | Holiday shipping volumes spike 4–8× — carrier selection must balance cost, speed, and capacity |
| **Return Prevention** | "Late delivery" is the #2 return reason — ETA accuracy prevents these returns |

During peak seasons, logistics becomes the weakest link. Carrier capacity is constrained, routes are congested, and weather disruptions increase. Proactive monitoring and intelligent carrier selection are essential to maintaining delivery promises.

## Traditional Challenges

1. **Single Carrier**: Reliance on one carrier creates risk — capacity limits, regional weakness, outages
2. **Static ETAs**: Estimated delivery dates set at checkout never update, even when delays occur
3. **Reactive Support**: Customers discover delays only when packages are late, then flood support
4. **Manual Monitoring**: Operations staff manually check carrier dashboards for exceptions
5. **No Route Intelligence**: Inability to predict delays from weather, traffic, or carrier performance patterns
6. **Cost Blindness**: No real-time comparison of carrier rates factoring delivery speed requirements

## How Holiday Peak Hub Addresses It

### Multi-Agent Logistics Pipeline

```
order.ready_to_ship → carrier-selection optimizes → carrier_selected
order.shipped → eta-computation calculates → eta_computed
ShipmentStatusUpdated → eta recalculated → ETAUpdated
order.in_transit → route-issue-detection → delay_detected → customer notified
```

### Intelligent Carrier Selection

The `logistics-carrier-selection` agent uses AI to:
- Compare carrier rates in real-time across multiple providers
- Factor delivery speed requirements (standard, express, overnight)
- Consider carrier historical reliability per region/route
- Account for current carrier capacity constraints during peak
- SLM handles standard selections; LLM evaluates complex multi-leg shipments

## Process Flow

### Carrier Selection

1. **Payment processed** → `PaymentProcessed` event published
2. **Carrier Selection Agent** (`logistics-carrier-selection`) receives event:
   - Retrieves order details (weight, dimensions, destination, delivery promise)
   - Queries available carriers with rates and ETAs
   - AI evaluates: cost vs. speed vs. reliability vs. capacity
   - Selects optimal carrier (or split shipment for multi-warehouse orders)
   - Publishes `CarrierSelected` and `ShipmentScheduled` events
3. **CRUD Service** updates order with carrier info and tracking number

### ETA Computation

4. **ETA Computation Agent** (`logistics-eta-computation`) receives `order.shipped`:
   - Calculates initial ETA based on:
     - Carrier's standard transit time for route
     - Historical delivery data for the lane (origin → destination)
     - Current known disruptions (weather, carrier alerts)
   - Stores ETA in warm memory (Cosmos DB)
   - Publishes `ETAComputed` event
5. **CRUD Service** provides ETA to customer via order tracking page

### Real-Time Route Monitoring

6. **Order Status Agent** (`ecommerce-order-status`) receives `ShipmentStatusUpdated`:
   - Updates order tracking timeline (picked up, in transit, out for delivery)
   - Triggers ETA recalculation if status change is unexpected
   - Provides real-time tracking data to `/order/[id]/tracking` endpoint

### Delay Detection & Response

7. **Route Issue Detection Agent** (`logistics-route-issue-detection`) monitors `order.in_transit`:
   - Analyzes real-time tracking data against expected route progress
   - Detects anomalies: shipment stalled, route deviation, weather impact
   - Evaluates delay severity using AI:
     - Minor (< 1 day): update ETA, no notification
     - Significant (1–3 days): notify customer with new ETA
     - Severe (> 3 days or lost): escalate to operations + notify customer
   - Publishes `DelayDetected` event with severity and new ETA

### Proactive Customer Notification

8. **ETA Computation Agent** receives `DelayDetected`:
   - Recalculates ETA with delay factors
   - Publishes `ETAUpdated` event
9. **Order Status Agent** receives `ETAUpdated`:
   - Sends proactive notification to customer (email/push)
   - Updates tracking page with new estimated delivery date
   - Provides options if severe: contact support, cancel order

## Agents Involved

| Agent | Role | Trigger | Output |
|-------|------|---------|--------|
| `logistics-carrier-selection` | Multi-carrier optimization | `PaymentProcessed` | `CarrierSelected`, `ShipmentScheduled` |
| `logistics-eta-computation` | ETA calculation and updates | `order.shipped`, `DelayDetected` | `ETAComputed`, `ETAUpdated` |
| `logistics-route-issue-detection` | Route monitoring and anomaly detection | `order.in_transit` | `DelayDetected` |
| `ecommerce-order-status` | Order tracking and notifications | `ShipmentStatusUpdated`, `ETAUpdated` | Customer notifications |

## Event Hub Topology

```
payment-events (PaymentProcessed)    ──→  logistics-carrier-selection
order-events (order.shipped)         ──→  logistics-eta-computation
order-events (order.in_transit)      ──→  logistics-route-issue-detection
order-events (ShipmentStatusUpdated) ──→  ecommerce-order-status
order-events (order.status_changed)  ──→  ecommerce-order-status
```

## Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| Carrier cost optimization | 10% savings | Actual cost vs. default carrier cost |
| ETA accuracy | > 90% | Deliveries within ±1 day of estimated |
| Delay detection lead time | > 12 hours | Time between detection and actual impact |
| Proactive notification rate | > 95% | Customers notified before they inquire |
| WISMO ticket reduction | 50% decrease | WISMO tickets vs. baseline |
| On-time delivery rate | > 95% | Delivered by promised date |

## BPMN Diagram

See [shipment-delivery-tracking.drawio](shipment-delivery-tracking.drawio) for the complete BPMN 2.0 process diagram showing:
- **5 pools**: CRUD Service, Carrier Selection Agent, ETA Agent, Route Detection Agent, Order Status Agent
- **Sequential flow**: Carrier selection → ETA → monitoring → notification
- **Feedback loop**: Delay detected → ETA recalculation → customer notification
- **Severity gateway**: Minor / significant / severe delay handling
