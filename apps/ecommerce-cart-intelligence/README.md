# Ecommerce Cart Intelligence Service

Intelligent agent service for shopping cart analysis, abandonment prevention, and conversion optimization through real-time product, pricing, and inventory insights.

## Overview

The Ecommerce Cart Intelligence service provides AI-powered cart analysis by evaluating product availability, pricing competitiveness, and abandonment risk factors. It delivers actionable recommendations to improve conversion rates and prevent cart abandonment.

## Architecture

### Components

```
ecommerce-cart-intelligence/
├── agents.py              # CartIntelligenceAgent with SLM/LLM routing
├── adapters.py            # Product, pricing, inventory, and analytics adapters
├── event_handlers.py      # Event Hub subscriber for order events
└── main.py                # FastAPI application with MCP tools
```

### Communication Patterns

1. **Agent REST Endpoints** (`/invoke`): Synchronous cart analysis requests from frontend/CRUD
2. **MCP Tools**: Agent-to-agent communication for cart context sharing
3. **Event Handlers**: Asynchronous processing of order events for cart optimization

## Features

### 🛒 Cart Analysis
- **Multi-Dimensional Context**: Product details, pricing history, inventory levels
- **Abandonment Risk Scoring**: Calculate likelihood of cart abandonment (0-1 scale)
- **Risk Driver Identification**: Pinpoint specific issues (out of stock, no promotion, missing data)
- **Hot Memory Caching**: Store cart context in Redis for fast retrieval (10-minute TTL)

**Risk Factors:**
- **Out of Stock**: +35% risk (critical blocker)
- **Low Stock**: +20% risk (creates urgency but may trigger doubt)
- **Missing Inventory Data**: +15% risk (uncertainty about availability)
- **No Active Promotion**: +5% risk (missed incentive opportunity)
- **No Active Price**: +10% risk (pricing uncertainty)

### 🤖 AI-Powered Intelligence
- **SLM-First Routing**: Fast responses for simple cart summaries
- **LLM Escalation**: Complex analysis requiring cross-product optimization
- **Contextual Recommendations**: AI-generated actions to reduce abandonment
- **Proactive Monitoring**: Flag anomalies and suggest tracking priorities

### 📊 Real-Time Event Processing
- **Order Events**: Analyze completed orders to understand conversion patterns
- **Parallel Context Fetching**: Async gathering of product, pricing, and inventory data

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
REDIS_URL=redis://localhost:6379/0            # Hot memory (cart caching)
COSMOS_ACCOUNT_URI=<cosmos-uri>               # Warm memory (recent carts)
COSMOS_DATABASE=holiday-peak
COSMOS_CONTAINER=agent-memory
BLOB_ACCOUNT_URL=<blob-uri>                   # Cold memory (historical data)
BLOB_CONTAINER=agent-memory

# Event Hub Configuration
EVENTHUB_NAMESPACE=<namespace>.servicebus.windows.net
EVENTHUB_CONNECTION_STRING=<connection-string>
# Subscriptions: order-events
# Consumer Group: cart-intel-group

# CRUD Service Integration (for MCP tools)
CRUD_SERVICE_URL=http://localhost:8000
```

## API Reference

### Agent REST Endpoint

**POST** `/invoke` - Analyze cart and generate intelligence insights

**Request Body:**
```json
{
  "user_id": "user-789",
  "items": [
    {"sku": "SKU-001", "quantity": 2},
    {"sku": "SKU-002", "quantity": 1}
  ],
  "related_limit": 3,
  "price_limit": 5,
  "cart_ttl": 600
}
```

**Response:**
```json
{
  "service": "ecommerce-cart-intelligence",
  "items": [
    {"sku": "SKU-001", "quantity": 2},
    {"sku": "SKU-002", "quantity": 1}
  ],
  "product_contexts": [
    {
      "product": {
        "sku": "SKU-001",
        "name": "Wireless Mouse",
        "category": "Electronics",
        "base_price": 29.99
      },
      "related_products": [
        {"sku": "SKU-003", "name": "Mouse Pad"},
        {"sku": "SKU-004", "name": "USB Hub"}
      ]
    }
  ],
  "pricing_contexts": [
    {
      "sku": "SKU-001",
      "active": {
        "amount": 24.99,
        "promotional": true,
        "discount_percentage": 17
      },
      "history": [...]
    }
  ],
  "inventory_contexts": [
    {
      "item": {
        "sku": "SKU-001",
        "available": 45,
        "warehouse_id": "warehouse-001"
      }
    }
  ],
  "abandonment_risk": {
    "risk_score": 0.15,
    "drivers": ["no promotion for SKU-002"]
  },
  "insight": "Cart health: Good (risk: 15%). SKU-001 has active promotion (17% off). Recommend: Apply discount to SKU-002 to balance cart value. Monitor: Stock levels for SKU-001 (45 units)."
}
```

### MCP Tools (Agent-to-Agent Communication)

#### 1. Get Cart Context
**POST** `/mcp/cart/context`

```json
{
  "items": [
    {"sku": "SKU-001", "quantity": 2}
  ],
  "related_limit": 3,
  "price_limit": 5
}
```

Returns complete cart context with product, pricing, and inventory details.

**Response:**
```json
{
  "items": [{"sku": "SKU-001", "quantity": 2}],
  "product_contexts": [...],
  "pricing_contexts": [...],
  "inventory_contexts": [...]
}
```

#### 2. Estimate Abandonment Risk
**POST** `/mcp/cart/abandonment-risk`

```json
{
  "items": [
    {"sku": "SKU-001", "quantity": 2},
    {"sku": "SKU-002", "quantity": 1}
  ]
}
```

Returns risk score and specific drivers.

**Response:**
```json
{
  "items": [...],
  "abandonment_risk": {
    "risk_score": 0.45,
    "drivers": [
      "out of stock for SKU-002",
      "no promotion for SKU-001"
    ]
  }
}
```

#### 3. Recommend Actions
**POST** `/mcp/cart/recommendations`

```json
{
  "items": [
    {"sku": "SKU-001", "quantity": 2}
  ]
}
```

Returns abandonment risk plus recommended actions.

**Response:**
```json
{
  "items": [...],
  "abandonment_risk": {...},
  "recommended_actions": [
    "send reminder",
    "offer limited-time discount",
    "highlight low stock"
  ]
}
```

## Risk Scoring Logic

### Risk Calculation Formula

```python
risk_score = 0.1  # Base risk

for item in cart_items:
    if inventory_missing:
        risk_score += 0.15
    elif out_of_stock:
        risk_score += 0.35  # Highest impact
    elif low_stock:
        risk_score += 0.20

for price in pricing_contexts:
    if no_active_price:
        risk_score += 0.10
    elif not_promotional:
        risk_score += 0.05

risk_score = min(risk_score, 1.0)  # Cap at 100%
```

### Risk Score Interpretation

| Score | Level | Interpretation | Recommended Actions |
|-------|-------|----------------|---------------------|
| 0.0 - 0.2 | **Low** | Healthy cart, likely to convert | Standard follow-up, upsell opportunities |
| 0.2 - 0.4 | **Medium** | Some friction, needs attention | Apply promotions, send reminder |
| 0.4 - 0.6 | **High** | Significant abandonment risk | Urgent discount, live chat offer, stock alerts |
| 0.6 - 1.0 | **Critical** | Very likely to abandon | Immediate intervention, alternative product suggestions |

### Driver Examples

```json
{
  "risk_score": 0.65,
  "drivers": [
    "out of stock for SKU-002",        // +0.35
    "low stock for SKU-001",           // +0.20
    "no promotion for SKU-003"         // +0.05
    // Base: +0.10
    // Total: 0.70 → capped at 1.0
  ]
}
```

## Event Processing

### Subscribed Events

| Event Hub | Consumer Group | Purpose |
|-----------|----------------|---------|
| `order-events` | `cart-intel-group` | Analyze completed orders to optimize cart intelligence |

### Event Handling Logic

1. **Extract Cart Items**: Parse items from order payload
2. **Skip Invalid Events**: Log and skip orders without items
3. **Parallel Context Fetching**: Gather product, pricing, and inventory data concurrently
   - Product contexts (with related products)
   - Pricing contexts (active price + history)
   - Inventory contexts (availability + warehouse)
4. **Risk Analysis**: Calculate abandonment risk based on fetched context
5. **Log Insights**: Structured logging with risk score and driver count

**Performance Optimization:**
```python
# Parallel fetching of all contexts (3 types × N items)
product_contexts, pricing_contexts, inventory_contexts = await asyncio.gather(
    asyncio.gather(*[get_product(item["sku"]) for item in items]),
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
uvicorn ecommerce_cart_intelligence.main:app --reload --port 8020
```

### Testing

```bash
# Run unit tests
pytest apps/ecommerce-cart-intelligence/tests/

# Test agent endpoint
curl -X POST http://localhost:8020/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-789",
    "items": [{"sku": "SKU-001", "quantity": 2}]
  }'

# Test MCP tool - Abandonment Risk
curl -X POST http://localhost:8020/mcp/cart/abandonment-risk \
  -H "Content-Type: application/json" \
  -d '{
    "items": [{"sku": "SKU-001", "quantity": 2}]
  }'

# Test MCP tool - Recommendations
curl -X POST http://localhost:8020/mcp/cart/recommendations \
  -H "Content-Type: application/json" \
  -d '{"items": [{"sku": "SKU-001", "quantity": 2}]}'
```

## Dependencies

- **holiday-peak-lib**: Shared framework (agents, adapters, memory, utilities)
- **FastAPI**: REST API and MCP server
- **Azure Event Hubs**: Async event processing
- **Azure AI Foundry**: SLM/LLM inference
- **Redis**: Hot memory (cart caching)
- **Azure Cosmos DB**: Warm memory (recent carts)
- **Azure Blob Storage**: Cold memory (historical data)

## Agent Behavior

### System Instructions

The agent is instructed to:
- **Be proactive**: Don't just report risk—suggest actions
- **Summarize cart health**: Use product, pricing, inventory context
- **Flag risks**: Call out specific issues (stock, pricing, missing data)
- **Recommend next actions**: Propose interventions to improve conversion
- **Monitor continuously**: Specify what to track next (stock levels, promotion uptake)
- **Handle missing data**: Propose safe assumptions when data unavailable

### SLM vs LLM Routing

| Query Type | Model | Reasoning |
|------------|-------|-----------|
| "Analyze this cart" | SLM | Simple risk calculation + context aggregation |
| "Summarize cart health" | SLM | Direct risk score interpretation |
| "Compare this cart to similar abandoned carts" | LLM | Historical pattern analysis |
| "Predict conversion likelihood" | LLM | Predictive modeling |
| "Why are customers abandoning carts with these items?" | LLM | Causal analysis across multiple carts |

## Integration Examples

### From Frontend (Cart Page)

```typescript
// React component - Shopping cart
const { data: cartAnalysis, isLoading } = useQuery({
  queryKey: ['cart-analysis', cartItems],
  queryFn: () => 
    fetch(`${AGENT_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: userId,
        items: cartItems.map(i => ({ sku: i.sku, quantity: i.quantity }))
      })
    }).then(r => r.json()),
  refetchInterval: 60000  // Refresh every minute
});

// Display risk-based messaging
if (cartAnalysis?.abandonment_risk?.risk_score > 0.4) {
  return (
    <Alert severity="warning">
      ⚠️ Limited stock available! Complete your purchase before items sell out.
      <Button>Apply 10% Discount</Button>
    </Alert>
  );
}
```

### From CRUD Service (Via Agent Client)

```python
# CRUD service calling cart intelligence
from crud_service.integrations.agent_client import get_agent_client

agent_client = get_agent_client()
recommendations = await agent_client.get_user_recommendations(
    user_id=user_id,
    items=[{"sku": item.sku, "quantity": item.quantity} for item in cart.items],
    fallback_value={"recommended_products": []}
)
```

### From Another Agent (MCP Tool)

```python
# Checkout support agent calling cart intelligence via MCP
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://ecommerce-cart-intelligence:8020/mcp/cart/abandonment-risk",
        json={"items": [{"sku": "SKU-001", "quantity": 2}]}
    )
    risk_data = response.json()
    
    if risk_data["abandonment_risk"]["risk_score"] > 0.5:
        # Apply intervention (discount, notification, etc.)
        await apply_discount(cart_id, discount_percentage=10)
```

## Use Cases

### 1. Real-Time Cart Health Dashboard
Display cart risk score and drivers to customer:
```python
analysis = await get_cart_context(items)
if analysis.abandonment_risk.risk_score > 0.4:
    show_urgency_banner("Limited stock! 45 items left")
    apply_dynamic_discount(10)  # 10% off
```

### 2. Abandoned Cart Recovery
Trigger email campaigns based on risk score:
```python
if risk_score >= 0.6:
    send_email(user, "Critical", "We saved your cart + 15% off!")
elif risk_score >= 0.3:
    send_email(user, "Medium", "Items in your cart are selling fast")
```

### 3. Dynamic Pricing Optimization
Adjust prices based on abandonment risk:
```python
for item in cart.items:
    risk = await estimate_abandonment_risk([item])
    if risk.risk_score > 0.5 and not item.promotional:
        apply_promotion(item.sku, discount=10)
```

### 4. Inventory Alerts
Notify customers when low-stock items are in cart:
```python
for item, inventory in zip(items, inventory_contexts):
    if inventory.item.available < 10:
        notify_user(f"Only {inventory.item.available} left!")
        add_to_cart_urgency_badge(item.sku)
```

### 5. A/B Testing Interventions
Test different strategies based on risk level:
```python
if risk_score > 0.5:
    if user_segment == "A":
        apply_discount(15)  # Aggressive discount
    else:
        send_live_chat_offer()  # Human assistance
```

## Monitoring & Observability

### Key Metrics

- `cart_event_processed`: Event processing count with risk distribution
- `cart_event_skipped`: Events without valid cart items
- `cart_risk_distribution`: Histogram of risk scores (low/medium/high/critical)
- `cart_conversion_rate`: Percentage of analyzed carts that convert
- `agent_invocation_duration`: Agent response time (SLM vs LLM)

### Logs

All operations emit structured logs with correlation IDs:

```json
{
  "event": "cart_event_processed",
  "event_type": "order.created",
  "order_id": "order-123",
  "risk_score": 0.45,
  "driver_count": 3,
  "product_contexts": 2,
  "timestamp": "2026-02-03T10:30:00Z"
}
```

## Production Considerations

### Resilience
- **Circuit Breaker**: Adapter calls (product, pricing, inventory) have circuit breakers
- **Fallback**: Returns safe defaults (low risk) if adapters unavailable
- **Timeout**: Fast timeouts prevent cascading failures
- **Parallel Fetching**: Async gather prevents sequential blocking

### Scalability
- **Stateless Agent**: Horizontal scaling via Kubernetes/Container Apps
- **Event Processing**: Consumer group allows parallel processing across partitions
- **Memory Tiering**: Hot (Redis) → Warm (Cosmos) → Cold (Blob) for cart context
- **Hot Memory TTL**: 10-minute cart cache (configurable via `cart_ttl`)

### Performance
- **Parallel Context Fetching**: All product/pricing/inventory calls concurrent
- **Related Product Limit**: Default 3 related products per item (configurable)
- **Price History Limit**: Default 5 historical prices per item (configurable)
- **Cache Optimization**: Cart context stored in Redis (10-minute TTL)

### Security
- **Authentication**: Azure Managed Identity for Event Hubs, Cosmos DB, Blob Storage
- **API Keys**: Azure AI Foundry uses key-based auth (rotate regularly)
- **PII Protection**: User IDs hashed in logs
- **Network Isolation**: Deploy in private subnet with service endpoints

## Advanced Features (Future)

### Machine Learning Enhancements
- **Predictive Abandonment**: ML model trained on historical cart + conversion data
- **Personalized Risk Scores**: Adjust risk based on user segment and behavior
- **Dynamic Thresholds**: Learn optimal risk thresholds per product category
- **Time-Series Analysis**: Factor in time-in-cart and session behavior

### Real-Time Interventions
- **Live Chat Triggers**: Automatic chat offer when risk > 0.7
- **Dynamic Discounts**: Real-time pricing adjustments based on risk
- **Stock Alerts**: Push notifications for low-stock items in cart
- **Alternative Suggestions**: Recommend in-stock alternatives when items unavailable

### Multi-Channel Optimization
- **Email Campaigns**: Abandoned cart emails with risk-based messaging
- **SMS Notifications**: Urgent alerts for high-risk carts
- **Push Notifications**: Mobile app alerts for cart status changes

## Related Services

- **ecommerce-catalog-search**: Provides product context for cart items
- **ecommerce-checkout-support**: Uses cart intelligence for checkout optimization
- **inventory-reservation-validation**: Validates stock availability for cart items
- **crud-service**: Transactional API for cart operations (called via MCP tools)

## License

See repository root for license information.
