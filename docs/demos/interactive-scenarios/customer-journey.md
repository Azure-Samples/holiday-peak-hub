# Customer Journey Demo

**Scenario**: Anonymous Visitor → Product Discovery → Cart → Checkout → Order Tracking  
**Duration**: 15-20 minutes  
**Agents Involved**: 8  
**Status**: Phase 3 - Planned

---

## Overview

This end-to-end scenario demonstrates how agents collaborate to provide a seamless shopping experience from initial product discovery through order fulfillment and tracking.

---

## Scenario Flow

### Step 1: Product Discovery (Catalog Search Agent)
**Agent**: `ecommerce-catalog-search` (Port 8001)  
**User Action**: Search for "wireless headphones"

**Request**:
```json
POST http://localhost:8001/invoke
{
  "query": "wireless headphones under $100",
  "filters": {
    "category": "electronics",
    "price_max": 100
  },
  "limit": 10
}
```

**Expected Output**:
- 10 relevant products with semantic search ranking
- Facets (brand, price range, rating)
- Query enhancement suggestions

**Memory Usage**:
- Hot (Redis): Query cache (5 min TTL)
- Warm (Cosmos): Recent searches for trend analysis

---

### Step 2: Product Detail View (Product Detail Enrichment Agent)
**Agent**: `ecommerce-product-detail-enrichment` (Port 8002)  
**User Action**: Click on product "Sony WH-1000XM5"

**Request**:
```json
POST http://localhost:8002/invoke
{
  "sku": "ELEC-HEADPHONE-001",
  "related_limit": 4
}
```

**Expected Output**:
- Enriched product with ACP content
- Customer reviews (aggregated rating, highlights)
- Inventory status (in stock, 3 warehouses)
- Related products (cross-sell recommendations)

**MCP Tool Calls** (internal):
- `/mcp/get_acp_content` → ACP adapter
- `/mcp/get_review_summary` → Review service
- `/mcp/get_inventory_status` → Inventory health check agent

**Memory Usage**:
- Hot (Redis): PDP cache (5 min TTL)
- Warm (Cosmos): Enrichment metadata

---

### Step 3: Add to Cart (Cart Intelligence Agent)
**Agent**: `ecommerce-cart-intelligence` (Port 8003)  
**User Action**: Add product to cart

**Request**:
```json
POST http://localhost:8003/invoke
{
  "user_id": "user-12345",
  "action": "add_item",
  "sku": "ELEC-HEADPHONE-001",
  "quantity": 1
}
```

**Expected Output**:
- Updated cart with item added
- Bundle recommendations ("Customers also bought: headphone case, charging cable")
- Total price with potential discounts

**MCP Tool Calls** (internal):
- `/mcp/get_bundle_suggestions` → Assortment optimization agent
- `/mcp/get_user_context` → Profile aggregation agent

**Memory Usage**:
- Hot (Redis): Cart state (session TTL)
- Warm (Cosmos): User purchase patterns

---

### Step 4: Checkout Initiation (Checkout Support Agent)
**Agent**: `ecommerce-checkout-support` (Port 8004)  
**User Action**: Proceed to checkout

**Request**:
```json
POST http://localhost:8004/invoke
{
  "cart_id": "cart-12345",
  "user_id": "user-12345",
  "shipping_address": {
    "zip": "90210",
    "country": "US"
  }
}
```

**Expected Output**:
- Inventory validation (stock available)
- Dynamic pricing (base + tax + shipping)
- Shipping options (2-day, next-day, standard)
- Payment methods (saved cards, new card)

**MCP Tool Calls** (internal):
- `/mcp/validate_inventory` → Inventory reservation validation agent
- `/mcp/calculate_shipping` → Carrier selection agent
- `/mcp/get_saved_payment_methods` → CRUD service

**Memory Usage**:
- Hot (Redis): Checkout session (15 min TTL)
- Warm (Cosmos): User payment preferences

---

### Step 5: Inventory Reservation (Inventory Reservation Validation Agent)
**Agent**: `inventory-reservation-validation` (Port 8016)  
**User Action**: Complete payment

**Request**:
```json
POST http://localhost:8016/invoke
{
  "sku": "ELEC-HEADPHONE-001",
  "quantity": 1,
  "order_id": "ORD-67890",
  "warehouse_preference": "closest"
}
```

**Expected Output**:
- Reservation confirmed (warehouse: Los Angeles)
- Allocation ID for fulfillment
- Reservation expiry (30 minutes)

**Event Published**:
- Topic: `inventory-events`
- Payload: `{"event": "reservation_created", "sku": "...", "order_id": "..."}`

**Memory Usage**:
- Hot (Redis): Reservation lock (30 min TTL)
- Warm (Cosmos): Allocation metadata

---

### Step 6: Carrier Selection (Carrier Selection Agent)
**Agent**: `logistics-carrier-selection` (Port 8019)  
**User Action**: Select shipping option

**Request**:
```json
POST http://localhost:8019/invoke
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
- Selected carrier: UPS 2nd Day Air
- Cost: $12.50
- Carbon footprint: 2.3 kg CO2

**MCP Tool Calls** (internal):
- `/mcp/get_carrier_rates` → 3rd party carrier APIs (UPS, FedEx, USPS)
- `/mcp/get_service_area` → Coverage validation

**Memory Usage**:
- Warm (Cosmos): Carrier rate cache (24 hours)

---

### Step 7: ETA Computation (ETA Computation Agent)
**Agent**: `logistics-eta-computation` (Port 8018)  
**User Action**: Order confirmed

**Request**:
```json
POST http://localhost:8018/invoke
{
  "order_id": "ORD-67890",
  "shipment_id": "SHIP-11111",
  "carrier": "UPS",
  "service_level": "2nd_day_air"
}
```

**Expected Output**:
- Estimated delivery: February 5, 2026 by 8 PM
- Confidence: 95%
- Cut-off for today's shipment: 3 PM PST

**Event Published**:
- Topic: `order-events`
- Payload: `{"event": "order_confirmed", "order_id": "...", "eta": "..."}`

**Memory Usage**:
- Warm (Cosmos): Carrier SLA data

---

### Step 8: Order Tracking (Order Status Agent)
**Agent**: `ecommerce-order-status` (Port 8005)  
**User Action**: Check order status

**Request**:
```json
POST http://localhost:8005/invoke
{
  "order_id": "ORD-67890",
  "user_id": "user-12345"
}
```

**Expected Output**:
- Current status: "In Transit"
- Last update: "Package picked up from Los Angeles warehouse"
- Next milestone: "Out for delivery"
- Tracking number: 1Z999AA1012345678
- ETA: February 5, 2026 by 8 PM

**MCP Tool Calls** (internal):
- `/mcp/get_shipment_tracking` → Carrier tracking APIs
- `/mcp/get_eta_update` → ETA computation agent (recalculation if needed)

**Event Subscription**:
- Topic: `order-events`
- Consumer: `order-status-group`
- Updates: Status changes, delays, delivery confirmation

**Memory Usage**:
- Hot (Redis): Recent order queries (10 min TTL)
- Warm (Cosmos): Order history and updates

---

## Event Choreography

### Event Flow Diagram

```
[User Action] → [Agent] → [Event Hub] → [Downstream Agents]

1. Add to Cart → Cart Intelligence → No event (session state only)
2. Place Order → Checkout Support → order-events.order_placed
   ↓
   → Inventory Reservation Validation (reserve stock)
   → JIT Replenishment Agent (trigger reorder if low)
   → Profile Aggregation Agent (update purchase history)
   
3. Confirm Payment → CRUD Service → payment-events.payment_success
   ↓
   → Order Status Agent (update status)
   → Campaign Intelligence Agent (post-purchase engagement)
   
4. Allocate Inventory → Inventory Reservation → inventory-events.reservation_created
   ↓
   → ETA Computation Agent (calculate delivery date)
   → Carrier Selection Agent (finalize shipping)
   
5. Ship Order → CRUD Service → order-events.order_shipped
   ↓
   → Order Status Agent (tracking updates)
   → Route Issue Detection Agent (monitor for delays)
```

---

## Performance Metrics

### Latency Breakdown
- **Step 1 (Search)**: 85ms (SLM, Redis cache miss)
- **Step 2 (PDP Enrichment)**: 120ms (parallel adapter calls)
- **Step 3 (Cart Update)**: 45ms (Redis state update)
- **Step 4 (Checkout)**: 180ms (LLM for dynamic pricing logic)
- **Step 5 (Inventory Reserve)**: 60ms (Cosmos write + Redis lock)
- **Step 6 (Carrier Selection)**: 200ms (3rd party API calls)
- **Step 7 (ETA)**: 95ms (SLM with carrier SLA data)
- **Step 8 (Order Status)**: 70ms (Redis cache hit)

**Total End-to-End**: ~855ms (excluding user think time)

### Memory Hit Rates
- Hot (Redis): 78% hit rate
- Warm (Cosmos): 92% hit rate
- Cold (Blob): < 1% access (historical data only)

### Token Usage
- Total tokens: ~18,500
- SLM tokens: 12,000 (65%)
- LLM tokens: 6,500 (35%)
- Estimated cost: $0.035 per journey

---

## Error Handling Demonstrations

### Scenario 1: Out of Stock
**Trigger**: Request product with `inventory_status = "out_of_stock"`

**Agent Response** (Checkout Support):
```json
{
  "status": "error",
  "error_code": "inventory_unavailable",
  "message": "This item is currently out of stock",
  "alternatives": [
    {"sku": "ELEC-HEADPHONE-002", "name": "Similar model available"},
    {"sku": "ELEC-HEADPHONE-003", "name": "Alternative brand"}
  ],
  "waitlist": {
    "available": true,
    "estimated_restock": "2026-02-15"
  }
}
```

**Fallback**: Assortment optimization agent suggests alternatives

---

### Scenario 2: Carrier API Failure
**Trigger**: Carrier service timeout

**Agent Response** (Carrier Selection):
```json
{
  "status": "partial_success",
  "warning": "One carrier service unavailable",
  "carriers_checked": ["UPS", "FedEx"],
  "carriers_failed": ["USPS"],
  "recommendation": {
    "carrier": "UPS",
    "service": "Ground",
    "cost": 8.99,
    "confidence": "medium"
  }
}
```

**Fallback**: Use cached carrier rates (24-hour stale data acceptable)

---

### Scenario 3: Payment Failure
**Trigger**: Payment gateway returns decline

**Event Published**:
- Topic: `payment-events`
- Event: `payment_failed`

**Downstream Actions**:
- Inventory Reservation: Release stock (30-min grace period)
- Profile Aggregation: Flag payment method for review
- Support Assistance: Create proactive support ticket

**User Notification**: Email with retry link and alternative payment options

---

## Frontend Integration

### UI Components Involved
1. **SearchBar** (atoms) → Catalog Search Agent
2. **ProductCard** (molecules) → Product Detail Enrichment Agent
3. **CartSummary** (organisms) → Cart Intelligence Agent
4. **CheckoutForm** (organisms) → Checkout Support Agent
5. **OrderTracker** (organisms) → Order Status Agent

### API Client Usage
```typescript
// Frontend code example (apps/ui/lib/api/product.ts)
import { productService } from '@/lib/api';
import { useQuery } from '@tanstack/react-query';

export function useProductDetails(sku: string) {
  return useQuery({
    queryKey: ['product', sku],
    queryFn: () => productService.getProduct(sku),
    staleTime: 5 * 60 * 1000, // 5 minutes (matches Redis TTL)
  });
}
```

### Network Trace
**Chrome DevTools → Network Tab**:
```
GET /api/products/ELEC-HEADPHONE-001       200  120ms  (Agent: enrichment)
GET /api/inventory/ELEC-HEADPHONE-001      200   45ms  (Cache: Redis hit)
GET /api/reviews/ELEC-HEADPHONE-001        200   30ms  (Cache: Redis hit)
POST /api/cart                             201   50ms  (Agent: cart intelligence)
```

---

## Running the Demo

### Prerequisites
```bash
# Start CRUD service
cd apps/crud-service/src && uvicorn crud_service.main:app --reload --port 8000

# Start required agents
cd apps/ecommerce-catalog-search/src && uvicorn main:app --reload --port 8001 &
cd apps/ecommerce-product-detail-enrichment/src && uvicorn main:app --reload --port 8002 &
cd apps/ecommerce-cart-intelligence/src && uvicorn main:app --reload --port 8003 &
cd apps/ecommerce-checkout-support/src && uvicorn main:app --reload --port 8004 &
cd apps/ecommerce-order-status/src && uvicorn main:app --reload --port 8005 &
cd apps/inventory-reservation-validation/src && uvicorn main:app --reload --port 8016 &
cd apps/logistics-carrier-selection/src && uvicorn main:app --reload --port 8019 &
cd apps/logistics-eta-computation/src && uvicorn main:app --reload --port 8018 &
```

### Run Automated Demo
```bash
# Using bash script
bash docs/demos/interactive-scenarios/run-customer-journey.sh

# Using PowerShell
.\docs\demos\interactive-scenarios\run-customer-journey.ps1
```

### Manual Step-Through
```bash
# Follow each step manually with curl commands
bash docs/demos/api-examples/curl-examples.sh customer-journey
```

---

## Next Steps

1. Explore [Product Lifecycle Demo](product-lifecycle.md)
2. Learn about [Order Fulfillment Demo](order-fulfillment.md)
3. Try [CRM Campaign Demo](crm-campaigns.md)
4. Review [Agent Architecture](../../architecture/components.md)
