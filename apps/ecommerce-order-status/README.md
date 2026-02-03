# Ecommerce Order Status Service

Intelligent agent service for order tracking, shipment monitoring, and delivery insights with real-time logistics event processing.

## Overview

The Ecommerce Order Status service provides AI-powered order tracking by aggregating shipment events, monitoring delivery progress, and identifying potential delays or exceptions. It delivers proactive insights to keep customers informed about their order status.

## Architecture

### Components

```
ecommerce-order-status/
├── agents.py              # OrderStatusAgent with SLM/LLM routing
├── adapters.py            # Logistics and tracking resolution adapters
├── event_handlers.py      # Event Hub subscriber for order events
└── main.py                # FastAPI application with MCP tools
```

### Communication Patterns

1. **Agent REST Endpoints** (`/invoke`): Synchronous order status requests from frontend/CRUD
2. **MCP Tools**: Agent-to-agent communication for tracking queries
3. **Event Handlers**: Asynchronous processing of order events for shipment updates

## Features

### 📦 Order Tracking
- **Shipment Status**: Real-time tracking of order fulfillment
- **Event Timeline**: Chronological shipment events (picked, shipped, in_transit, delivered)
- **Tracking Resolution**: Map order IDs to tracking numbers
- **Delivery Monitoring**: Track progress toward delivery date

**Shipment Statuses:**
- **pending**: Order received, not yet shipped
- **picked**: Items picked from warehouse
- **shipped**: Package handed to carrier
- **in_transit**: En route to destination
- **out_for_delivery**: Final delivery in progress
- **delivered**: Successfully delivered
- **exception**: Delivery issue (address problem, failed delivery)
- **cancelled**: Order cancelled before shipment

### 🤖 AI-Powered Intelligence
- **SLM-First Routing**: Fast responses for simple status lookups
- **LLM Escalation**: Complex scenarios requiring exception handling or recommendations
- **Delivery Risk Assessment**: Identify potential delays or issues
- **Proactive Recommendations**: Suggest actions for exceptions (reroute, contact carrier)

### 📊 Real-Time Event Processing
- **Order Events**: Track new orders and status changes
- **Shipment Events**: Monitor carrier updates and delivery milestones
- **Exception Detection**: Flag delivery issues automatically

## Configuration

### Required Environment Variables

```bash
# Azure AI Foundry Configuration
PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com/
FOUNDRY_AGENT_ID_FAST=<slm-agent-id>          # Small language model (GPT-4o-mini)
FOUNDRY_AGENT_ID_RICH=<llm-agent-id>          # Large language model (GPT-4o)
MODEL_DEPLOYMENT_NAME_FAST=<slm-deployment>
MODEL_DEPLOYMENT_NAME_RICH=<llm-deployment>
FOUNDRY_PROJECT_NAME=<project-name>           # Optional
FOUNDRY_STREAM=false                          # Enable streaming responses

# Memory Configuration (Three-Tier Architecture)
REDIS_URL=redis://localhost:6379/0            # Hot memory (status cache)
COSMOS_ACCOUNT_URI=<cosmos-uri>               # Warm memory (recent orders)
COSMOS_DATABASE=holiday-peak
COSMOS_CONTAINER=agent-memory
BLOB_ACCOUNT_URL=<blob-uri>                   # Cold memory (historical data)
BLOB_CONTAINER=agent-memory

# Event Hub Configuration
EVENTHUB_NAMESPACE=<namespace>.servicebus.windows.net
EVENTHUB_CONNECTION_STRING=<connection-string>
# Subscriptions: order-events
# Consumer Group: order-status-group

# CRUD Service Integration (for MCP tools)
CRUD_SERVICE_URL=http://localhost:8000
```

## API Reference

### Agent REST Endpoint

**POST** `/invoke` - Get order status with AI insights

**Request Body (by Order ID):**
```json
{
  "order_id": "order-123"
}
```

**Request Body (by Tracking ID):**
```json
{
  "tracking_id": "T-order-123"
}
```

**Response:**
```json
{
  "service": "ecommerce-order-status",
  "order_id": "order-123",
  "tracking_id": "T-order-123",
  "status": "in_transit",
  "events": [
    {
      "event_id": "evt-001",
      "timestamp": "2026-02-01T10:00:00Z",
      "status": "picked",
      "location": "Warehouse A",
      "description": "Package picked and ready for shipment"
    },
    {
      "event_id": "evt-002",
      "timestamp": "2026-02-01T14:30:00Z",
      "status": "shipped",
      "location": "Warehouse A",
      "carrier": "FedEx",
      "description": "Package shipped via FedEx"
    },
    {
      "event_id": "evt-003",
      "timestamp": "2026-02-02T08:15:00Z",
      "status": "in_transit",
      "location": "Memphis, TN",
      "description": "In transit to destination"
    }
  ]
}
```

**Response with AI Insights:**
```json
{
  "service": "ecommerce-order-status",
  "order_id": "order-123",
  "tracking_id": "T-order-123",
  "status": "in_transit",
  "events": [...],
  "insight": "Your order is in transit from Memphis, TN. Current status: in_transit as of Feb 2 at 8:15am. Expected delivery: Feb 5. Next milestone: Arrival at local facility. No exceptions detected."
}
```

### MCP Tools (Agent-to-Agent Communication)

#### 1. Get Order Status
**POST** `/mcp/order/status`

```json
{
  "order_id": "order-123"
}
```

Or with tracking ID:

```json
{
  "tracking_id": "T-order-123"
}
```

Returns shipment status and event timeline.

**Response:**
```json
{
  "order_id": "order-123",
  "tracking_id": "T-order-123",
  "status": "in_transit",
  "events": [
    {
      "event_id": "evt-001",
      "timestamp": "2026-02-01T10:00:00Z",
      "status": "picked",
      "location": "Warehouse A",
      "description": "Package picked and ready for shipment"
    }
  ]
}
```

#### 2. Get Order Events
**POST** `/mcp/order/events`

```json
{
  "tracking_id": "T-order-123"
}
```

Returns detailed event timeline for a tracking ID.

**Response:**
```json
{
  "tracking_id": "T-order-123",
  "events": [
    {
      "event_id": "evt-001",
      "timestamp": "2026-02-01T10:00:00Z",
      "status": "picked",
      "location": "Warehouse A",
      "description": "Package picked and ready for shipment"
    },
    {
      "event_id": "evt-002",
      "timestamp": "2026-02-01T14:30:00Z",
      "status": "shipped",
      "location": "Warehouse A",
      "carrier": "FedEx",
      "description": "Package shipped via FedEx"
    }
  ]
}
```

## Order Status Logic

### Status Progression

```
pending → picked → shipped → in_transit → out_for_delivery → delivered
                                    ↓
                                exception
```

### Tracking ID Resolution

When order ID provided without tracking ID:

```python
# Order ID → Tracking ID resolution
tracking_id = await resolver.resolve_tracking_id(order_id)
# Returns: "T-{order_id}" (stub implementation)
# Production: Query shipment database or carrier API
```

### Event Timeline

Events are ordered chronologically to show delivery progress:

```python
events = [
  {"timestamp": "2026-02-01T10:00:00Z", "status": "picked"},
  {"timestamp": "2026-02-01T14:30:00Z", "status": "shipped"},
  {"timestamp": "2026-02-02T08:15:00Z", "status": "in_transit"},
  # ...
]
# Latest event = events[-1] (most recent status)
```

## Event Processing

### Subscribed Events

| Event Hub | Consumer Group | Purpose |
|-----------|----------------|---------|
| `order-events` | `order-status-group` | Track order lifecycle and shipment updates |

### Event Handling Logic

1. **Extract Identifiers**: Parse `order_id` and `tracking_id` from event payload
2. **Resolve Tracking**: If no tracking ID, resolve from order ID
3. **Skip Invalid Events**: Log and skip events without identifiable tracking
4. **Fetch Logistics Context**: Retrieve shipment status and event timeline
5. **Log Status**: Structured logging with status and event count

**Event Types Processed:**
- `OrderCreated`: New order received
- `OrderShipped`: Package handed to carrier
- `OrderDelivered`: Package successfully delivered
- `OrderException`: Delivery issue detected
- `ShipmentUpdated`: Carrier status update (from logistics integration)

## Development

### Running Locally

```bash
# Install dependencies (from repository root)
uv sync

# Set environment variables
export PROJECT_ENDPOINT=https://your-project.cognitiveservices.azure.com/
export FOUNDRY_AGENT_ID_FAST=<slm-agent-id>
export REDIS_URL=redis://localhost:6379/0

# Run service
uvicorn ecommerce_order_status.main:app --reload --port 8023
```

### Testing

```bash
# Run unit tests
pytest apps/ecommerce-order-status/tests/

# Test agent endpoint - By order ID
curl -X POST http://localhost:8023/invoke \
  -H "Content-Type: application/json" \
  -d '{"order_id": "order-123"}'

# Test agent endpoint - By tracking ID
curl -X POST http://localhost:8023/invoke \
  -H "Content-Type: application/json" \
  -d '{"tracking_id": "T-order-123"}'

# Test MCP tool - Order Status
curl -X POST http://localhost:8023/mcp/order/status \
  -H "Content-Type: application/json" \
  -d '{"order_id": "order-123"}'

# Test MCP tool - Order Events
curl -X POST http://localhost:8023/mcp/order/events \
  -H "Content-Type: application/json" \
  -d '{"tracking_id": "T-order-123"}'
```

## Dependencies

- **holiday-peak-lib**: Shared framework (agents, adapters, memory, utilities)
- **FastAPI**: REST API and MCP server
- **Azure Event Hubs**: Async event processing
- **Azure AI Foundry**: SLM/LLM inference
- **Redis**: Hot memory (status caching)
- **Azure Cosmos DB**: Warm memory (recent orders)
- **Azure Blob Storage**: Cold memory (historical data)

## Agent Behavior

### System Instructions

The agent is instructed to:
- **Be proactive about delivery risks**: Flag potential delays or exceptions
- **Summarize latest status**: Provide clear current status and key events
- **Recommend actions**: Suggest next steps for exceptions (contact carrier, update address)
- **Monitor continuously**: Specify what to track next (carrier updates, exception codes, ETA drift)
- **Handle anomalies**: Call out unusual patterns (delayed transit, repeated exceptions)

### SLM vs LLM Routing

| Query Type | Model | Reasoning |
|------------|-------|-----------|
| "What's the status of order-123?" | SLM | Direct status lookup |
| "Show order events" | SLM | Simple event timeline retrieval |
| "Why is my order delayed?" | LLM | Requires analyzing event patterns |
| "What should I do about delivery exception?" | LLM | Recommendation + policy decision |
| "Compare delivery times across my orders" | LLM | Cross-order analysis |

## Integration Examples

### From Frontend (Order Tracking Page)

```typescript
// React component - Order tracking
const { data: orderStatus, isLoading } = useQuery({
  queryKey: ['order-status', orderId],
  queryFn: () => 
    fetch(`${AGENT_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_id: orderId })
    }).then(r => r.json()),
  refetchInterval: 300000  // Refresh every 5 minutes
});

// Display status timeline
<Timeline>
  {orderStatus?.events?.map(event => (
    <TimelineEvent
      key={event.event_id}
      timestamp={event.timestamp}
      status={event.status}
      location={event.location}
      description={event.description}
    />
  ))}
</Timeline>

// Status badge
<StatusBadge status={orderStatus?.status} />
```

### From CRUD Service (Via Agent Client)

```python
# CRUD service calling order status
from crud_service.integrations.agent_client import get_agent_client

agent_client = get_agent_client()
status = await agent_client.call_endpoint(
    agent_url=settings.order_status_agent_url,
    endpoint="/invoke",
    data={"order_id": order_id},
    fallback_value={"status": "unknown", "events": []}
)

# Return status to customer
return OrderStatusResponse(
    order_id=order_id,
    status=status["status"],
    events=status["events"]
)
```

### From Another Agent (MCP Tool)

```python
# Support assistance agent calling order status via MCP
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://ecommerce-order-status:8023/mcp/order/status",
        json={"order_id": "order-123"}
    )
    order_data = response.json()
    
    if order_data["status"] == "exception":
        # Escalate to support
        await create_support_ticket(
            order_id=order_data["order_id"],
            issue="Delivery exception",
            context=order_data["events"]
        )
```

## Use Cases

### 1. Customer Self-Service Tracking
Provide real-time order status without support calls:
```python
status = await get_order_status(order_id="order-123")
display_tracking_page(status)
# Shows timeline, current location, expected delivery
```

### 2. Proactive Delay Notifications
Alert customers before they inquire:
```python
status = await get_order_status(order_id="order-123")
if status.status == "exception" or is_delayed(status.events):
    send_notification(
        user_id=order.user_id,
        message="Your order is delayed. New ETA: Feb 10"
    )
```

### 3. Support Ticket Context
Provide order history to support agents:
```python
ticket = await create_ticket(order_id="order-123")
status = await get_order_status(order_id="order-123")
ticket.context = {
    "status": status.status,
    "events": status.events,
    "last_location": status.events[-1].location
}
```

### 4. Delivery Exception Handling
Automatically route exceptions to appropriate teams:
```python
status = await get_order_status(order_id="order-123")
if status.status == "exception":
    exception_code = status.events[-1].get("exception_code")
    if exception_code == "address_invalid":
        route_to_address_verification()
    elif exception_code == "customer_unavailable":
        schedule_redelivery()
```

### 5. Analytics & Reporting
Track delivery performance metrics:
```python
orders = await get_all_orders(date_range="last_30_days")
statuses = await asyncio.gather(*[
    get_order_status(order_id=o.id) for o in orders
])

# Calculate metrics
on_time_rate = sum(1 for s in statuses if s.status == "delivered") / len(statuses)
exception_rate = sum(1 for s in statuses if s.status == "exception") / len(statuses)
avg_transit_time = calculate_avg_transit_time(statuses)
```

## Monitoring & Observability

### Key Metrics

- `order_status_event_processed`: Event processing count with status distribution
- `order_status_event_skipped`: Events without tracking information
- `order_status_by_state`: Histogram of orders per status (pending, shipped, delivered, etc.)
- `order_delivery_time`: Time from order creation to delivery
- `order_exception_rate`: Percentage of orders with exceptions
- `agent_invocation_duration`: Agent response time (SLM vs LLM)

### Logs

All operations emit structured logs with correlation IDs:

```json
{
  "event": "order_status_event_processed",
  "event_type": "order.shipped",
  "order_id": "order-123",
  "tracking_id": "T-order-123",
  "status": "shipped",
  "event_count": 2,
  "timestamp": "2026-02-03T10:30:00Z"
}
```

## Production Considerations

### Resilience
- **Circuit Breaker**: Logistics adapter calls have circuit breakers
- **Fallback**: Returns "unknown" status if logistics adapter unavailable
- **Timeout**: Fast timeouts prevent cascading failures
- **Retry Logic**: Exponential backoff for transient carrier API failures

### Scalability
- **Stateless Agent**: Horizontal scaling via Kubernetes/Container Apps
- **Event Processing**: Consumer group allows parallel processing across partitions
- **Memory Tiering**: Hot (Redis) → Warm (Cosmos) → Cold (Blob) for status cache
- **Status Caching**: Redis cache for frequently checked orders (5-minute TTL)

### Performance
- **Tracking Resolution**: Cache order_id → tracking_id mappings
- **Event Aggregation**: Store full event timeline (avoid repeated carrier API calls)
- **Lazy Loading**: Only fetch events when needed (not on every status check)

### Security
- **Authentication**: Azure Managed Identity for Event Hubs, Cosmos DB, Blob Storage
- **API Keys**: Azure AI Foundry and carrier APIs use key-based auth (rotate regularly)
- **PII Protection**: Order data contains customer addresses (encrypt at rest)
- **Network Isolation**: Deploy in private subnet with service endpoints

### Carrier Integration
- **API Rate Limits**: Respect carrier API quotas (cache aggressively)
- **Webhook Authentication**: Verify carrier webhooks (HMAC signatures)
- **Error Handling**: Handle carrier API downtime gracefully
- **Multi-Carrier**: Support FedEx, UPS, USPS, DHL with adapter pattern

## Advanced Features (Future)

### Predictive Delivery
- **ETA Prediction**: ML model for accurate delivery time estimates
- **Delay Detection**: Identify at-risk deliveries before carrier reports exception
- **Weather Impact**: Factor weather conditions into ETA calculations
- **Traffic Analysis**: Adjust ETAs based on real-time traffic data

### Enhanced Tracking
- **Live Map**: Real-time driver location on map
- **SMS Notifications**: Text updates for delivery milestones
- **Photo Proof of Delivery**: Upload delivery photos from carrier
- **Signature Capture**: Digital signature on delivery

### Exception Management
- **Automatic Rescheduling**: Rebook failed deliveries automatically
- **Address Correction**: Suggest corrected addresses when invalid
- **Alternative Delivery**: Offer pickup at nearby location
- **Delivery Instructions**: Allow customers to leave special instructions

### Multi-Package Orders
- **Split Shipments**: Track multiple packages per order
- **Consolidated Status**: Aggregate status across all packages
- **Partial Delivery**: Handle deliveries where some items arrive separately

## Related Services

- **ecommerce-checkout-support**: Validates orders before shipment
- **logistics-eta-computation**: Provides ETA estimates for orders
- **logistics-route-issue-detection**: Identifies delivery route problems
- **crud-service**: Transactional API for order management (called via MCP tools)

## License

See repository root for license information.
