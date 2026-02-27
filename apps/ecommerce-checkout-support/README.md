# Ecommerce Checkout Support Service

Intelligent agent service for checkout validation, order readiness verification, and payment optimization through real-time pricing and inventory checks.

## Overview

The Ecommerce Checkout Support service provides AI-powered checkout assistance by validating cart items against pricing and inventory constraints. It identifies blockers (out of stock, missing prices, insufficient inventory) and recommends fixes to ensure smooth order completion.

## Architecture

### Components

```
ecommerce-checkout-support/
├── agents.py              # CheckoutSupportAgent with SLM/LLM routing
├── adapters.py            # Pricing, inventory, and validation adapters
├── event_handlers.py      # Event Hub subscribers for order and inventory events
└── main.py                # FastAPI application with MCP tools
```

### Communication Patterns

1. **Agent REST Endpoints** (`/invoke`): Synchronous checkout validation from frontend/CRUD
2. **MCP Tools**: Agent-to-agent communication for checkout context sharing
3. **Event Handlers**: Asynchronous processing of order and inventory events

## Features

### ✅ Checkout Validation
- **Pricing Verification**: Validate active prices exist for all items
- **Inventory Checks**: Verify sufficient stock availability
- **Blocker Detection**: Identify issues preventing order completion
- **Status Assessment**: Overall checkout readiness (ready, blocked)

**Validation Issues:**
- **out_of_stock**: Item has zero inventory
- **insufficient_stock**: Item available < quantity requested
- **inventory_missing**: Cannot determine inventory status
- **missing_price**: No active price configured

### 🤖 AI-Powered Intelligence
- **SLM-First Routing**: Fast responses for simple validation checks
- **LLM Escalation**: Complex scenarios requiring policy decisions or alternatives
- **Contextual Recommendations**: AI-generated fixes for blockers
- **Proactive Monitoring**: Flag price changes and stock volatility

### 📊 Real-Time Event Processing
- **Order Events**: Validate checkout readiness when orders created
- **Inventory Events**: Update stock availability for in-flight checkouts
- **Parallel Context Fetching**: Async gathering of pricing and inventory data

### 💳 Payment Integration
- **External Payment API Tools**: Optional integration with payment gateways
- **Payment Authorization**: Authorize payment before order completion
- **Payment Capture**: Capture authorized payment after fulfillment
- **Payment Refund**: Process refunds for cancelled orders

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
REDIS_URL=redis://localhost:6379/0            # Hot memory (checkout cache)
COSMOS_ACCOUNT_URI=<cosmos-uri>               # Warm memory (recent checkouts)
COSMOS_DATABASE=holiday-peak
COSMOS_CONTAINER=agent-memory
BLOB_ACCOUNT_URL=<blob-uri>                   # Cold memory (historical data)
BLOB_CONTAINER=agent-memory

# Event Hub Configuration
EVENTHUB_NAMESPACE=<namespace>.servicebus.windows.net
EVENTHUB_CONNECTION_STRING=<connection-string>
# Subscriptions: order-events, inventory-events
# Consumer Group: checkout-group

# CRUD Service Integration (for MCP tools)
CRUD_SERVICE_URL=http://localhost:8000

# Payment API Integration (Optional)
PAYMENT_API_URL=https://api.stripe.com/v1      # Example: Stripe API
PAYMENT_API_KEY=<stripe-secret-key>            # Payment gateway API key
```

## API Reference

### Agent REST Endpoint

**POST** `/invoke` - Validate checkout and identify blockers

**Request Body:**
```json
{
  "items": [
    {"sku": "SKU-001", "quantity": 2},
    {"sku": "SKU-002", "quantity": 1}
  ]
}
```

**Response (Successful Validation):**
```json
{
  "service": "ecommerce-checkout-support",
  "items": [
    {"sku": "SKU-001", "quantity": 2},
    {"sku": "SKU-002", "quantity": 1}
  ],
  "pricing": [
    {
      "sku": "SKU-001",
      "active": {
        "amount": 29.99,
        "currency": "USD",
        "promotional": true
      }
    },
    {
      "sku": "SKU-002",
      "active": {
        "amount": 49.99,
        "currency": "USD",
        "promotional": false
      }
    }
  ],
  "inventory": [
    {
      "item": {
        "sku": "SKU-001",
        "available": 50,
        "warehouse_id": "warehouse-001"
      }
    },
    {
      "item": {
        "sku": "SKU-002",
        "available": 10,
        "warehouse_id": "warehouse-001"
      }
    }
  ],
  "validation": {
    "status": "ready",
    "issues": []
  }
}
```

**Response (Blocked Checkout):**
```json
{
  "service": "ecommerce-checkout-support",
  "items": [
    {"sku": "SKU-001", "quantity": 2},
    {"sku": "SKU-003", "quantity": 5}
  ],
  "validation": {
    "status": "blocked",
    "issues": [
      {
        "sku": "SKU-003",
        "type": "insufficient_stock",
        "available": 3
      },
      {
        "sku": "SKU-001",
        "type": "missing_price"
      }
    ]
  }
}
```

### MCP Tools (Agent-to-Agent Communication)

#### 1. Validate Checkout
**POST** `/mcp/checkout/validate`

```json
{
  "items": [
    {"sku": "SKU-001", "quantity": 2}
  ]
}
```

Returns validation status and issues list.

**Response:**
```json
{
  "items": [{"sku": "SKU-001", "quantity": 2}],
  "validation": {
    "status": "ready",
    "issues": []
  }
}
```

#### 2. Get Pricing
**POST** `/mcp/checkout/pricing`

```json
{
  "sku": "SKU-001"
}
```

Returns pricing context for a single SKU.

**Response:**
```json
{
  "pricing": {
    "sku": "SKU-001",
    "active": {
      "amount": 29.99,
      "currency": "USD",
      "promotional": true,
      "discount_percentage": 25
    },
    "history": [...]
  }
}
```

#### 3. Get Inventory
**POST** `/mcp/checkout/inventory`

```json
{
  "sku": "SKU-001"
}
```

Returns inventory context for a single SKU.

**Response:**
```json
{
  "inventory": {
    "item": {
      "sku": "SKU-001",
      "available": 50,
      "warehouse_id": "warehouse-001",
      "reserved": 5
    }
  }
}
```

#### 4. Payment API Tools (Optional)

If `PAYMENT_API_URL` and `PAYMENT_API_KEY` are configured, the following MCP tools are exposed:

**POST** `/mcp/payment/authorize` - Authorize payment

**POST** `/mcp/payment/capture` - Capture authorized payment

**POST** `/mcp/payment/refund` - Process refund

These tools proxy directly to the payment gateway API with authentication.

## Validation Logic

### Checkout Status Determination

```python
issues = []

for item in cart_items:
    # Inventory validation
    if inventory_missing:
        issues.append({"type": "inventory_missing"})
    elif available == 0:
        issues.append({"type": "out_of_stock"})
    elif available < requested_quantity:
        issues.append({"type": "insufficient_stock", "available": available})
    
    # Pricing validation
    if no_active_price:
        issues.append({"type": "missing_price"})

status = "ready" if len(issues) == 0 else "blocked"
```

### Issue Types

| Issue Type | Severity | Description | Recommended Action |
|------------|----------|-------------|-------------------|
| **out_of_stock** | Critical | Item has zero inventory | Remove from cart or suggest alternative |
| **insufficient_stock** | Critical | Not enough stock for quantity | Reduce quantity or split order |
| **inventory_missing** | High | Cannot determine availability | Retry inventory check or mark unavailable |
| **missing_price** | Critical | No active price configured | Configure pricing or remove item |

### Validation Flow

```
1. Extract cart items (SKU + quantity)
2. Fetch pricing contexts (parallel)
3. Fetch inventory contexts (parallel)
4. Check each item:
   - Inventory available >= quantity?
   - Active price exists?
5. Aggregate issues
6. Determine status (ready vs blocked)
7. Return validation result + AI recommendations
```

## Event Processing

### Subscribed Events

| Event Hub | Consumer Group | Purpose |
|-----------|----------------|---------|
| `order-events` | `checkout-group` | Validate checkout readiness for new orders |
| `inventory-events` | `checkout-group` | Update availability for in-flight checkouts |

### Event Handling Logic

**Order Events:**
1. **Extract Cart Items**: Parse items from order payload
2. **Skip Invalid Events**: Log and skip orders without items
3. **Parallel Context Fetching**: Gather pricing and inventory data concurrently
4. **Validation**: Check for blockers (out of stock, missing price)
5. **Log Results**: Structured logging with status and issue count

**Inventory Events:**
1. **Extract SKU**: Parse product identifier from event
2. **Skip Invalid Events**: Log and skip events without SKU
3. **Fetch Inventory Context**: Get current availability
4. **Log Update**: Record new stock level

**Performance Optimization:**
```python
# Parallel fetching of pricing and inventory contexts
pricing_contexts, inventory_contexts = await asyncio.gather(
    asyncio.gather(*[get_pricing(item["sku"]) for item in items]),
    asyncio.gather(*[get_inventory(item["sku"]) for item in items])
)
```

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
uvicorn ecommerce_checkout_support.main:app --reload --port 8022
```

### Testing

```bash
# Run unit tests
pytest apps/ecommerce-checkout-support/tests/

# Test agent endpoint - Ready checkout
curl -X POST http://localhost:8022/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "items": [{"sku": "SKU-001", "quantity": 2}]
  }'

# Test agent endpoint - Blocked checkout
curl -X POST http://localhost:8022/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "items": [{"sku": "SKU-999", "quantity": 100}]
  }'

# Test MCP tool - Validate
curl -X POST http://localhost:8022/mcp/checkout/validate \
  -H "Content-Type: application/json" \
  -d '{"items": [{"sku": "SKU-001", "quantity": 2}]}'

# Test MCP tool - Pricing
curl -X POST http://localhost:8022/mcp/checkout/pricing \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU-001"}'

# Test MCP tool - Inventory
curl -X POST http://localhost:8022/mcp/checkout/inventory \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU-001"}'
```

## Dependencies

- **holiday-peak-lib**: Shared framework (agents, adapters, memory, utilities)
- **FastAPI**: REST API and MCP server
- **Azure Event Hubs**: Async event processing
- **Azure AI Foundry**: SLM/LLM inference
- **Redis**: Hot memory (checkout caching)
- **Azure Cosmos DB**: Warm memory (recent checkouts)
- **Azure Blob Storage**: Cold memory (historical data)

## Agent Behavior

### System Instructions

The agent is instructed to:
- **Be proactive about checkout readiness**: Validate before user attempts to complete order
- **Validate pricing and availability**: Check all constraints
- **Summarize blockers**: List all issues preventing checkout
- **Propose fixes**: Suggest actions to resolve issues (reduce quantity, remove item, etc.)
- **Monitor continuously**: Flag price changes, stock volatility, failed validations

### SLM vs LLM Routing

| Query Type | Model | Reasoning |
|------------|-------|-----------|
| "Validate this checkout" | SLM | Simple validation rules |
| "Check if items are in stock" | SLM | Direct inventory lookup |
| "Why can't I complete checkout?" | LLM | Requires explaining multiple issues |
| "Suggest alternatives for out-of-stock items" | LLM | Product recommendation logic |
| "What's the best way to handle this pricing error?" | LLM | Policy decision making |

## Integration Examples

### From Frontend (Checkout Page)

```typescript
// React component - Checkout validation
const { data: validation, isLoading, error } = useQuery({
  queryKey: ['checkout-validation', cartItems],
  queryFn: () => 
    fetch(`${AGENT_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        items: cartItems.map(i => ({ sku: i.sku, quantity: i.quantity }))
      })
    }).then(r => r.json()),
  refetchInterval: 30000  // Revalidate every 30 seconds
});

// Display validation status
if (validation?.validation?.status === "blocked") {
  return (
    <Alert severity="error">
      <AlertTitle>Cannot Complete Checkout</AlertTitle>
      <ul>
        {validation.validation.issues.map(issue => (
          <li key={issue.sku}>
            {issue.type === "out_of_stock" && `${issue.sku} is out of stock`}
            {issue.type === "insufficient_stock" && 
              `Only ${issue.available} units of ${issue.sku} available`}
            {issue.type === "missing_price" && `${issue.sku} has no price`}
          </li>
        ))}
      </ul>
    </Alert>
  );
}
```

### From CRUD Service (Via Agent Client)

```python
# CRUD service calling checkout support
from crud_service.integrations.agent_client import get_agent_client

agent_client = get_agent_client()
validation = await agent_client.call_endpoint(
    agent_url=settings.checkout_support_agent_url,
    endpoint="/invoke",
    data={"items": [{"sku": item.sku, "quantity": item.quantity} for item in cart.items]},
    fallback_value={"validation": {"status": "unknown", "issues": []}}
)

if validation["validation"]["status"] == "blocked":
    raise CheckoutBlockedException(issues=validation["validation"]["issues"])
```

### From Another Agent (MCP Tool)

```python
# Order status agent calling checkout support via MCP
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://ecommerce-checkout-support:8022/mcp/checkout/validate",
        json={"items": [{"sku": "SKU-001", "quantity": 2}]}
    )
    validation_result = response.json()
    
    if validation_result["validation"]["status"] == "blocked":
        # Notify customer of issues
        await send_notification(order_id, validation_result["validation"]["issues"])
```

## Use Cases

### 1. Pre-Checkout Validation
Validate cart before user reaches checkout page:
```python
validation = await validate_checkout(cart_items)
if validation.status == "blocked":
    show_checkout_disabled()
    display_issues(validation.issues)
```

### 2. Real-Time Stock Updates
Monitor inventory during checkout flow:
```python
# Revalidate every 30 seconds
while checkout_in_progress:
    validation = await validate_checkout(cart_items)
    if validation.status == "blocked":
        show_stock_warning()
    await asyncio.sleep(30)
```

### 3. Dynamic Pricing Validation
Verify prices haven't changed since cart creation:
```python
pricing = await get_pricing(sku)
if pricing.active.amount != cart_item.price:
    notify_user_price_change(old_price, pricing.active.amount)
```

### 4. Inventory Reservation
Reserve stock during checkout to prevent overselling:
```python
validation = await validate_checkout(items)
if validation.status == "ready":
    # Reserve inventory for 10 minutes
    await reserve_inventory(items, ttl_minutes=10)
    proceed_to_payment()
```

### 5. Alternative Product Suggestions
Suggest alternatives when items out of stock:
```python
validation = await validate_checkout(items)
for issue in validation.issues:
    if issue.type == "out_of_stock":
        alternatives = await search_similar_products(issue.sku)
        suggest_alternatives(alternatives)
```

## Monitoring & Observability

### Key Metrics

- `checkout_event_processed`: Event processing count with status distribution
- `checkout_event_skipped`: Events without valid items
- `checkout_validation_blocked_rate`: Percentage of blocked checkouts
- `checkout_issue_types`: Histogram of issue types (out_of_stock, missing_price, etc.)
- `checkout_validation_duration`: Validation latency
- `agent_invocation_duration`: Agent response time (SLM vs LLM)

### Logs

All operations emit structured logs with correlation IDs:

```json
{
  "event": "checkout_event_processed",
  "event_type": "order.created",
  "order_id": "order-123",
  "status": "blocked",
  "issue_count": 2,
  "timestamp": "2026-02-03T10:30:00Z"
}
```

## Production Considerations

### Resilience
- **Circuit Breaker**: Pricing and inventory adapter calls have circuit breakers
- **Fallback**: Returns "unknown" status if adapters unavailable
- **Timeout**: Fast timeouts prevent cascading failures
- **Parallel Fetching**: Async gather prevents sequential blocking

### Scalability
- **Stateless Agent**: Horizontal scaling via Kubernetes/Container Apps
- **Event Processing**: Consumer group allows parallel processing across partitions
- **Memory Tiering**: Hot (Redis) → Warm (Cosmos) → Cold (Blob) for checkout cache

### Performance
- **Parallel Context Fetching**: All pricing/inventory calls concurrent
- **Validation Caching**: Hot memory caches validation results (short TTL)
- **Early Exit**: Stop validation on first critical blocker (optional optimization)

### Security
- **Authentication**: Azure Managed Identity for Event Hubs, Cosmos DB, Blob Storage
- **API Keys**: Azure AI Foundry and Payment API use key-based auth (rotate regularly)
- **PII Protection**: Order data encrypted at rest
- **Network Isolation**: Deploy in private subnet with service endpoints
- **Payment Security**: Never log payment credentials or card details

### Payment Integration
- **PCI Compliance**: Use tokenized payment methods (never store card numbers)
- **Idempotency**: Payment operations are idempotent (safe to retry)
- **Webhook Validation**: Verify payment gateway webhooks (HMAC signatures)
- **Refund Limits**: Enforce business rules on refund amounts and timing

## Advanced Features (Future)

### Intelligent Checkout Optimization
- **Predictive Inventory**: Reserve stock proactively for high-intent users
- **Dynamic Pricing**: Adjust prices based on cart abandonment risk
- **Split Orders**: Automatically split orders when partial stock available
- **Pre-Authorization**: Authorize payment before final checkout

### Multi-Payment Methods
- **Saved Payment Methods**: Store tokenized cards for repeat customers
- **Alternative Payments**: Support PayPal, Apple Pay, Google Pay
- **Buy Now Pay Later**: Integrate Affirm, Afterpay, Klarna
- **Gift Cards**: Apply gift card balances to checkout

### Fraud Prevention
- **Risk Scoring**: Calculate fraud risk based on order patterns
- **Address Verification**: Validate shipping addresses
- **Velocity Checks**: Detect suspicious order frequency
- **Device Fingerprinting**: Track device IDs for fraud detection

### Checkout Analytics
- **Abandonment Tracking**: Measure checkout drop-off by step
- **Issue Frequency**: Track most common blockers
- **Conversion Optimization**: A/B test checkout flows
- **Time-to-Checkout**: Measure checkout duration

## Related Services

- **ecommerce-cart-intelligence**: Provides cart abandonment risk analysis
- **ecommerce-order-status**: Tracks order fulfillment after checkout
- **inventory-reservation-validation**: Validates stock reservations
- **crud-service**: Transactional API for order creation (called via MCP tools)

## License

See repository root for license information.
