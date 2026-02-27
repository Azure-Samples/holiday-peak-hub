# Business Scenario 04: Inventory Optimization

## Overview

**Inventory Optimization** encompasses real-time stock monitoring, low-stock detection, automated replenishment, critical stock alerting, and scarcity messaging for checkout. In Holiday Peak Hub, a chain of specialized agents continuously monitors inventory health and takes proactive action — from generating purchase orders to alerting operations teams and enabling urgency messaging on the storefront.

## Business Importance for Retail

| Metric | Impact |
|--------|--------|
| **Stockout Cost** | Each stockout event loses 4.1% of annual revenue (IHL Group) |
| **Overstock Waste** | Excess inventory ties up capital and leads to 15–30% markdowns |
| **Carrying Cost** | Average inventory carrying cost is 20–30% of item value per year |
| **Peak Season Risk** | Holiday stockouts are 3× more costly — no time for reorders |
| **Customer Experience** | "Out of stock" is the #1 reason for customer brand switching (73% of shoppers) |
| **Conversion Boost** | Scarcity messaging ("Only 3 left!") increases conversion by 10–25% |

During holiday peaks, accurate inventory management is existential — overstock means markdowns, stockout means lost sales and lost customers. The window for replenishment is narrow, and decisions must be automated and real-time.

## Traditional Challenges

1. **Batch Processing**: Daily inventory counts miss intra-day stock changes from concurrent orders
2. **Manual Reordering**: Buyers review reports weekly and place orders manually — too slow for peak
3. **Threshold Blindness**: Static reorder points don't adapt to demand velocity changes
4. **Alert Fatigue**: Operations teams receive too many alerts with no prioritization
5. **No Demand Context**: Reorder quantities don't account for upcoming promotions or trends
6. **Checkout Disconnect**: Storefront doesn't reflect real-time inventory urgency

## How Holiday Peak Hub Addresses It

### Event-Driven Inventory Pipeline

Each order placement triggers a real-time inventory evaluation chain:

```
OrderPlaced → health-check monitors → low_stock threshold breached
                                           ↓
                            jit-replenishment calculates reorder → generates PO
                                           ↓
                            alerts-triggers sends notifications (SMS/email)
                                           ↓
                            checkout-support enables scarcity messaging
```

### Three-Agent Collaboration

1. **Health Check Agent**: Continuous monitoring, threshold evaluation, trend analysis
2. **JIT Replenishment Agent**: AI-powered reorder calculations considering demand velocity, lead times, seasonal patterns
3. **Alerts & Triggers Agent**: Multi-channel notifications with severity-based routing

## Process Flow

### Stock Level Monitoring

1. **Order placed** → `OrderCreated` published to `order-events`
2. **Inventory Health Check Agent** (`inventory-health-check`) receives event:
   - Decrements available stock count in real-time
   - Evaluates stock level against dynamic thresholds:
     - **Healthy**: stock > reorder point → no action
     - **Low Stock**: stock ≤ reorder point → publish `inventory.low_stock`
     - **Critical**: stock ≤ safety stock → publish `inventory.critical_stock`
     - **Stockout**: stock = 0 → publish `inventory.stockout`
   - Uses SLM to analyze demand velocity and adjust thresholds dynamically

### Just-in-Time Replenishment

3. **JIT Replenishment Agent** (`inventory-jit-replenishment`) receives `inventory.low_stock`:
   - Calculates optimal reorder quantity using:
     - Current demand velocity (orders/day trending)
     - Supplier lead time (historical average + buffer)
     - Seasonal adjustment factors (peak multiplier)
     - Pending inbound inventory (existing POs)
   - Generates purchase order (PO) with recommended quantities
   - Stores PO in Cosmos DB for staff review
   - Publishes `inventory.reorder_generated` event

### Critical Stock Alerting

4. **Alerts & Triggers Agent** (`inventory-alerts-triggers`) receives `inventory.critical_stock`:
   - Evaluates severity based on:
     - Product importance (top seller? promotional item?)
     - Time to stockout (demand velocity / remaining stock)
     - Supplier responsiveness (can they expedite?)
   - Routes alerts by severity:
     - **High**: SMS to operations manager + Slack/Teams notification
     - **Medium**: Email to procurement team
     - **Low**: Dashboard update only
   - Publishes `inventory.alert_sent` event

### Checkout Scarcity Messaging

5. **Checkout Support Agent** (`ecommerce-checkout-support`) receives `inventory.low_stock`:
   - Enables scarcity messaging for affected products:
     - "Only 3 left in stock!"
     - "High demand — selling fast"
   - Provides scarcity data to CRUD Service for storefront display
   - Adjusts messaging intensity based on stock level and demand

### Inventory Recovery (from Returns)

6. **Inventory Health Check Agent** receives `ReturnApproved`:
   - Increases expected inbound count
   - Recalculates stock projections
   - May cancel pending JIT purchase orders if return restocking is sufficient

## Agents Involved

| Agent | Role | Trigger | Output |
|-------|------|---------|--------|
| `inventory-health-check` | Monitor stock, evaluate thresholds | `OrderCreated`, `ReturnApproved` | `inventory.low_stock`, `inventory.critical_stock` |
| `inventory-jit-replenishment` | Calculate reorder, generate PO | `inventory.low_stock` | Purchase orders, `inventory.reorder_generated` |
| `inventory-alerts-triggers` | Multi-channel alerting | `inventory.critical_stock` | SMS, email, Teams notifications |
| `ecommerce-checkout-support` | Scarcity messaging | `inventory.low_stock` | Urgency UI data |

## Event Hub Topology

```
order-events (OrderCreated)           ──→  inventory-health-check
inventory-events (low_stock)          ──→  inventory-jit-replenishment, ecommerce-checkout-support
inventory-events (critical_stock)     ──→  inventory-alerts-triggers
order-events (ReturnApproved)         ──→  inventory-health-check (recovery)
```

## Key Performance Indicators

| KPI | Target | Measurement |
|-----|--------|-------------|
| Stockout incidents (peak) | < 0.5% of SKUs | SKUs at zero stock / total active SKUs |
| Reorder accuracy | > 90% | PO quantities within 10% of actual demand |
| Alert response time | < 15 minutes | Time from critical alert to human acknowledgment |
| Scarcity conversion lift | > 10% | Conversion with vs. without scarcity messaging |
| Inventory turnover | > 8×/year | COGS / average inventory value |
| Demand forecast accuracy | > 85% | Forecasted vs. actual demand (MAPE) |

## BPMN Diagram

See [inventory-optimization.drawio](inventory-optimization.drawio) for the complete BPMN 2.0 process diagram showing:
- **5 pools**: Order Events, Health Check Agent, JIT Replenishment, Alerts Agent, Checkout Support
- **Threshold gateways**: Healthy / Low / Critical / Stockout decision tree
- **Parallel processing**: JIT reorder + alerting + scarcity messaging happen concurrently
- **Feedback loop**: Return-driven inventory recovery
