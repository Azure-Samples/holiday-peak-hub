# Order Fulfillment Demo

**Scenario**: Order Placed → Inventory Allocation → Carrier Selection → Shipment → Delivery → Returns  
**Duration**: 20-25 minutes  
**Agents Involved**: 8  
**Status**: Phase 3 - Planned

---

## Overview

This scenario demonstrates the complete order fulfillment workflow with real-time inventory allocation, intelligent carrier selection, proactive delay detection, and returns processing using SAGA choreography patterns.

---

## Scenario Flow

### Step 1: Order Placement
**Agent**: `ecommerce-checkout-support` (Port 8004)  
**Trigger**: Customer completes payment

**Request**:
```json
POST http://localhost:8004/invoke
{
  "cart_id": "cart-12345",
  "user_id": "user-12345",
  "shipping_address": {"zip": "90210", "country": "US"},
  "payment_method": "card_ending_4242"
}
```

**Expected Output**:
```json
{
  "order_id": "ORD-67890",
  "status": "confirmed",
  "total": 249.99,
  "estimated_delivery": "2026-05-04"
}
```

**Event Published**:
- Topic: `order-events`
- Event: `order_placed`
- Payload:
```json
{
  "event": "order_placed",
  "order_id": "ORD-67890",
  "user_id": "user-12345",
  "items": [{"sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462", "quantity": 1, "price": 249.99}],
  "total": 249.99,
  "shipping_address": {"zip": "90210", "country": "US"},
  "timestamp": "2026-04-30T14:30:00Z"
}
```

---

### Step 2: Inventory Reservation
**Agent**: `inventory-reservation-validation` (Port 8016)  
**Trigger**: Subscribes to `order-events` → `order_placed`

**Request** (triggered by event):
```json
POST http://localhost:8016/invoke
{
  "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
  "quantity": 1,
  "order_id": "ORD-67890",
  "warehouse_preference": "closest"
}
```

**Expected Output**:
```json
{
  "reservation_id": "RES-44455",
  "status": "reserved",
  "warehouse": "WH-LAX-01",
  "allocated_quantity": 1,
  "remaining_stock": 42,
  "reservation_expiry": "2026-04-30T15:00:00Z"
}
```

**Event Published**:
- Topic: `inventory-events`
- Event: `reservation_created`
- Payload:
```json
{
  "event": "reservation_created",
  "reservation_id": "RES-44455",
  "order_id": "ORD-67890",
  "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
  "warehouse": "WH-LAX-01",
  "remaining_stock": 42,
  "timestamp": "2026-04-30T14:30:05Z"
}
```

**Memory Usage**:
- Hot (Redis): Reservation lock (30 min TTL)
- Warm (Cosmos): Allocation metadata

---

### Step 3: JIT Replenishment Check
**Agent**: `inventory-jit-replenishment` (Port 8015)  
**Trigger**: Subscribes to `inventory-events` → `reservation_created` when `remaining_stock < reorder_point`

**Request** (triggered when stock is low):
```json
POST http://localhost:8015/invoke
{
  "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
  "current_stock": 42,
  "daily_velocity": 15,
  "lead_time_days": 3,
  "warehouse": "WH-LAX-01"
}
```

**Expected Output** (stock above threshold — no action):
```json
{
  "action": "monitor",
  "reason": "Stock (42 units) above reorder point (45 units) by velocity calculation but within safe margin",
  "days_of_stock": 2.8,
  "recommendation": "Schedule review in 24 hours",
  "reorder_triggered": false
}
```

**Expected Output** (stock below threshold — PO created):
```json
{
  "action": "reorder",
  "purchase_order": {
    "po_id": "PO-88776",
    "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
    "quantity": 100,
    "supplier": "AudioTech Direct",
    "expected_arrival": "2026-05-03"
  },
  "reorder_triggered": true,
  "reason": "Stock (8 units) below reorder point (45 units). Lead time: 3 days."
}
```

**Event Published** (when reorder triggered):
- Topic: `inventory-events`
- Event: `reorder_triggered`
- Payload:
```json
{
  "event": "reorder_triggered",
  "po_id": "PO-88776",
  "sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462",
  "quantity": 100,
  "warehouse": "WH-LAX-01",
  "timestamp": "2026-04-30T14:30:10Z"
}
```

---

### Step 4: Carrier Selection
**Agent**: `logistics-carrier-selection` (Port 8018)  
**Trigger**: Subscribes to `inventory-events` → `reservation_created`

**Request**:
```json
POST http://localhost:8018/invoke
{
  "order_id": "ORD-67890",
  "origin_zip": "90001",
  "destination_zip": "90210",
  "weight_lbs": 1.2,
  "dimensions": {"length": 10, "width": 8, "height": 4},
  "speed_preference": "2-day"
}
```

**Expected Output**:
```json
{
  "selected_carrier": {
    "carrier": "UPS",
    "service": "2nd Day Air",
    "cost": 12.50,
    "tracking_prefix": "1Z999AA"
  },
  "alternatives": [
    {"carrier": "FedEx", "service": "Express Saver", "cost": 14.20},
    {"carrier": "USPS", "service": "Priority Mail", "cost": 9.80}
  ],
  "carbon_footprint_kg": 2.3,
  "label_generated": true,
  "pickup_scheduled": "2026-04-30T17:00:00Z"
}
```

**Event Published**:
- Topic: `logistics-events`
- Event: `carrier_selected`
- Payload:
```json
{
  "event": "carrier_selected",
  "order_id": "ORD-67890",
  "carrier": "UPS",
  "service": "2nd Day Air",
  "tracking_number": "1Z999AA1012345678",
  "timestamp": "2026-04-30T14:31:00Z"
}
```

---

### Step 5: ETA Computation
**Agent**: `logistics-eta-computation` (Port 8019)  
**Trigger**: Subscribes to `logistics-events` → `carrier_selected`

**Request**:
```json
POST http://localhost:8019/invoke
{
  "order_id": "ORD-67890",
  "shipment_id": "SHIP-11111",
  "carrier": "UPS",
  "service_level": "2nd_day_air",
  "origin_zip": "90001",
  "destination_zip": "90210"
}
```

**Expected Output**:
```json
{
  "estimated_delivery": "2026-05-02T20:00:00Z",
  "confidence": 0.95,
  "delivery_window": {
    "earliest": "2026-05-02T08:00:00Z",
    "latest": "2026-05-02T20:00:00Z"
  },
  "milestones": [
    {"event": "picked_up", "expected": "2026-04-30T17:00:00Z"},
    {"event": "in_transit", "expected": "2026-05-01T06:00:00Z"},
    {"event": "out_for_delivery", "expected": "2026-05-02T07:00:00Z"},
    {"event": "delivered", "expected": "2026-05-02T14:00:00Z"}
  ],
  "factors": ["No weather delays", "No holiday disruptions", "Direct route available"]
}
```

**Event Published**:
- Topic: `order-events`
- Event: `eta_computed`
- Payload:
```json
{
  "event": "eta_computed",
  "order_id": "ORD-67890",
  "eta": "2026-05-02T20:00:00Z",
  "confidence": 0.95,
  "timestamp": "2026-04-30T14:31:30Z"
}
```

---

### Step 6: Route Monitoring During Transit
**Agent**: `logistics-route-issue-detection` (Port 8020)  
**Trigger**: Continuous monitoring after `carrier_selected` event

**Request** (periodic polling):
```json
POST http://localhost:8020/invoke
{
  "shipment_id": "SHIP-11111",
  "carrier": "UPS",
  "tracking_number": "1Z999AA1012345678",
  "expected_delivery": "2026-05-02"
}
```

**Expected Output** (no issues):
```json
{
  "status": "on_track",
  "current_location": "Los Angeles Sort Facility",
  "last_scan": "2026-05-01T06:15:00Z",
  "issues_detected": [],
  "eta_change": null,
  "confidence": 0.96
}
```

**Expected Output** (delay detected):
```json
{
  "status": "delayed",
  "current_location": "Los Angeles Sort Facility",
  "last_scan": "2026-05-01T14:00:00Z",
  "issues_detected": [
    {
      "type": "weather_delay",
      "severity": "moderate",
      "description": "Severe thunderstorms in transit corridor",
      "estimated_impact_hours": 6
    }
  ],
  "eta_change": {
    "original": "2026-05-02T20:00:00Z",
    "revised": "2026-05-03T08:00:00Z",
    "reason": "Weather delay in transit"
  },
  "confidence": 0.72
}
```

**Event Published** (when delay detected):
- Topic: `order-events`
- Event: `delivery_delayed`
- Payload:
```json
{
  "event": "delivery_delayed",
  "order_id": "ORD-67890",
  "original_eta": "2026-05-02T20:00:00Z",
  "revised_eta": "2026-05-03T08:00:00Z",
  "reason": "weather_delay",
  "timestamp": "2026-05-01T14:05:00Z"
}
```

---

### Step 7: Delivery Confirmation
**Agent**: `ecommerce-order-status` (Port 8005)  
**Trigger**: Carrier webhook → `order-events` → `order_delivered`

**Request** (customer checks status):
```json
POST http://localhost:8005/invoke
{
  "order_id": "ORD-67890",
  "user_id": "user-12345"
}
```

**Expected Output**:
```json
{
  "order_id": "ORD-67890",
  "status": "delivered",
  "delivery_details": {
    "delivered_at": "2026-05-02T14:22:00Z",
    "signed_by": "Front Door",
    "proof_of_delivery": "https://tracking.ups.com/pod/1Z999AA1012345678"
  },
  "timeline": [
    {"event": "Order Placed", "timestamp": "2026-04-30T14:30:00Z"},
    {"event": "Payment Confirmed", "timestamp": "2026-04-30T14:30:02Z"},
    {"event": "Inventory Reserved", "timestamp": "2026-04-30T14:30:05Z"},
    {"event": "Shipped", "timestamp": "2026-04-30T17:00:00Z"},
    {"event": "In Transit", "timestamp": "2026-05-01T06:15:00Z"},
    {"event": "Out for Delivery", "timestamp": "2026-05-02T07:30:00Z"},
    {"event": "Delivered", "timestamp": "2026-05-02T14:22:00Z"}
  ],
  "tracking_number": "1Z999AA1012345678"
}
```

**Event Published**:
- Topic: `order-events`
- Event: `order_delivered`

---

### Step 8: Return Request
**Agent**: `logistics-returns-support` (Port 8021)  
**Trigger**: Customer initiates return via UI

**Request**:
```json
POST http://localhost:8021/invoke
{
  "order_id": "ORD-67890",
  "user_id": "user-12345",
  "reason": "Product does not match description",
  "items": [{"sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462", "quantity": 1}]
}
```

**Expected Output**:
```json
{
  "return_id": "RET-99001",
  "status": "approved",
  "return_label": {
    "carrier": "UPS",
    "tracking_number": "1Z999AA1098765432",
    "label_url": "https://returns.retailer.com/label/RET-99001.pdf"
  },
  "refund": {
    "amount": 249.99,
    "method": "original_payment",
    "estimated_processing": "3-5 business days after receipt"
  },
  "instructions": [
    "Pack item in original packaging if available",
    "Attach the provided return label",
    "Drop off at any UPS location or schedule pickup",
    "Refund will be processed within 3-5 business days of receipt"
  ],
  "pickup_available": true,
  "pickup_window": "2026-05-03 to 2026-05-05"
}
```

**Event Published**:
- Topic: `order-events`
- Event: `return_initiated`
- Payload:
```json
{
  "event": "return_initiated",
  "return_id": "RET-99001",
  "order_id": "ORD-67890",
  "reason": "Product does not match description",
  "items": [{"sku": "d9c3b1de-7158-5ea1-9f33-7bdaec2f0462", "quantity": 1}],
  "timestamp": "2026-05-04T10:00:00Z"
}
```

---

## SAGA Choreography Pattern

### Event Flow Diagram
```
[Customer] → Place Order
     │
     ▼
[Checkout Support] → Publishes: order-events.order_placed
     │
     ├──────────────────────────────────┐
     ▼                                  ▼
[Inventory Reservation]            [Profile Aggregation]
  Publishes:                        Updates purchase history
  inventory-events.reservation_created
     │
     ├─────────────────┐
     ▼                 ▼
[JIT Replenishment]  [Carrier Selection]
  (if stock low)      Publishes:
  Publishes:          logistics-events.carrier_selected
  inventory-events.     │
  reorder_triggered     ▼
                     [ETA Computation]
                      Publishes:
                      order-events.eta_computed
                        │
                        ▼
                     [Route Issue Detection]
                      (continuous monitoring)
                      Publishes:
                      order-events.delivery_delayed (if issues)
                        │
                        ▼
                     [Order Status]
                      Publishes:
                      order-events.order_delivered
                        │
                        ▼
                     [Returns Support]
                      (if customer initiates)
                      Publishes:
                      order-events.return_initiated
```

### Compensation (Rollback) Scenarios

| Failure Point | Compensation Action | Agent |
|---------------|-------------------|-------|
| Inventory unavailable | Cancel order, notify customer, suggest alternatives | Checkout Support |
| Payment declined | Release reservation, free stock | Inventory Reservation |
| Carrier API down | Use cached rates, select backup carrier | Carrier Selection |
| Delivery failed | Schedule re-delivery or return to warehouse | Route Issue Detection |
| Return rejected | Notify customer with reason, escalate to support | Returns Support |

---

## Performance Metrics

### Processing Time (Event-Driven)
- **Order → Reservation**: < 500ms (event processing + Cosmos write)
- **Reservation → Carrier**: < 300ms (parallel with JIT check)
- **Carrier → ETA**: < 200ms (SLM computation)
- **Total (order to shipping label)**: < 2 seconds

### Event Throughput
- **Peak capacity**: 10,000 orders/minute
- **Event Hub partitions**: 8 (order-events), 4 (inventory-events), 4 (logistics-events)
- **Consumer groups**: 1 per subscribing agent

---

## Running the Demo

### Prerequisites
```bash
# Start CRUD service
cd apps/crud-service/src && uvicorn crud_service.main:app --reload --port 8000

# Start fulfillment agents
cd apps/ecommerce-checkout-support/src && uvicorn main:app --reload --port 8004 &
cd apps/ecommerce-order-status/src && uvicorn main:app --reload --port 8005 &
cd apps/inventory-reservation-validation/src && uvicorn main:app --reload --port 8016 &
cd apps/inventory-jit-replenishment/src && uvicorn main:app --reload --port 8015 &
cd apps/logistics-carrier-selection/src && uvicorn main:app --reload --port 8018 &
cd apps/logistics-eta-computation/src && uvicorn main:app --reload --port 8019 &
cd apps/logistics-route-issue-detection/src && uvicorn main:app --reload --port 8020 &
cd apps/logistics-returns-support/src && uvicorn main:app --reload --port 8021 &
```

### Run Step-by-Step
```bash
# Step 1: Place order
curl -X POST http://localhost:8004/invoke \
  -H "Content-Type: application/json" \
  -d '{"cart_id":"cart-12345","user_id":"user-12345","shipping_address":{"zip":"90210","country":"US"},"payment_method":"card_ending_4242"}'

# Step 2: Reserve inventory
curl -X POST http://localhost:8016/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku":"d9c3b1de-7158-5ea1-9f33-7bdaec2f0462","quantity":1,"order_id":"ORD-67890","warehouse_preference":"closest"}'

# Step 3: Check replenishment
curl -X POST http://localhost:8015/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku":"d9c3b1de-7158-5ea1-9f33-7bdaec2f0462","current_stock":42,"daily_velocity":15,"lead_time_days":3,"warehouse":"WH-LAX-01"}'

# Step 4: Select carrier
curl -X POST http://localhost:8018/invoke \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-67890","origin_zip":"90001","destination_zip":"90210","weight_lbs":1.2,"dimensions":{"length":10,"width":8,"height":4},"speed_preference":"2-day"}'

# Step 5: Compute ETA
curl -X POST http://localhost:8019/invoke \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-67890","shipment_id":"SHIP-11111","carrier":"UPS","service_level":"2nd_day_air","origin_zip":"90001","destination_zip":"90210"}'

# Step 6: Monitor route
curl -X POST http://localhost:8020/invoke \
  -H "Content-Type: application/json" \
  -d '{"shipment_id":"SHIP-11111","carrier":"UPS","tracking_number":"1Z999AA1012345678","expected_delivery":"2026-05-02"}'

# Step 7: Check order status
curl -X POST http://localhost:8005/invoke \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-67890","user_id":"user-12345"}'

# Step 8: Initiate return
curl -X POST http://localhost:8021/invoke \
  -H "Content-Type: application/json" \
  -d '{"order_id":"ORD-67890","user_id":"user-12345","reason":"Product does not match description","items":[{"sku":"d9c3b1de-7158-5ea1-9f33-7bdaec2f0462","quantity":1}]}'
```

---

## Related Demos
- [Customer Journey](customer-journey.md) - Includes order placement
- [Product Lifecycle](product-lifecycle.md) - Product data preparation
- [CRM Campaigns](crm-campaigns.md) - Post-purchase engagement
