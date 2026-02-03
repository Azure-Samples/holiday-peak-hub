# Ecommerce Product Detail Enrichment Service

Intelligent agent service for product detail page (PDP) enhancement with real-time enrichment from catalog data, ACP content, reviews, and inventory status.

## Overview

The Product Detail Enrichment service aggregates multiple data sources to create comprehensive product detail pages. It combines catalog data with ACP (Agentic Commerce Protocol) content, customer reviews, inventory status, and related products to maximize conversion and customer confidence.

## Architecture

### Components

```
ecommerce-product-detail-enrichment/
├── agents.py              # ProductDetailEnrichmentAgent with SLM/LLM routing
├── adapters.py            # Product, inventory, ACP, and review adapters
├── event_handlers.py      # Event Hub subscriber for product updates
└── main.py                # FastAPI application with MCP tools
```

### Communication Patterns

1. **Agent REST Endpoints** (`/invoke`): Synchronous product enrichment from frontend/CRUD
2. **MCP Tools**: Agent-to-agent communication for product details and similar products
3. **Event Handlers**: Asynchronous enrichment when products are created/updated

## Features

### 🎨 Multi-Source Product Enrichment
- **Catalog Data**: Base product information (name, SKU, description, price)
- **ACP Content**: Rich descriptions, feature lists, high-quality media assets
- **Review Aggregation**: Rating, review count, customer highlights
- **Inventory Context**: Stock availability, warehouse locations, lead times
- **Related Products**: Recommendations for cross-sell and upsell

### 🔍 Intelligent PDP Optimization
- **Conversion Signal Detection**: Flag low stock, missing media, low ratings
- **Content Completeness Scoring**: Identify incomplete product data
- **SLM-First Routing**: Fast enrichment for simple requests
- **LLM Escalation**: Deep analysis for complex recommendations

### ⚡ Real-Time Updates
- **Event-Driven**: Auto-enrich on product creation/update events
- **Hot Memory Caching**: 5-minute cache for high-traffic PDPs
- **Parallel Data Fetching**: Concurrent calls to all adapters (sub-100ms)
- **Fallback Strategies**: Gracefully handle missing data sources

### 📊 Enrichment Components

| Component | Source | Example Data |
|-----------|--------|--------------|
| **Catalog** | Product Service | Name, SKU, price, category |
| **ACP Content** | ACP Adapter | Long description, feature list, media URLs |
| **Reviews** | Review Adapter | Rating (4.6), review count (128), highlights |
| **Inventory** | Inventory Service | Stock level, availability, warehouses |
| **Related** | Product Service | Similar products (limit: 4) |

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
REDIS_URL=redis://localhost:6379/0            # Hot memory (PDP cache)
COSMOS_ACCOUNT_URI=<cosmos-uri>               # Warm memory (recent enrichments)
COSMOS_DATABASE=holiday-peak
COSMOS_CONTAINER=agent-memory
BLOB_ACCOUNT_URL=<blob-uri>                   # Cold memory (historical data)
BLOB_CONTAINER=agent-memory

# Event Hub Configuration
EVENTHUB_NAMESPACE=<namespace>.servicebus.windows.net
EVENTHUB_CONNECTION_STRING=<connection-string>
# Subscriptions: product-events
# Consumer Group: enrichment-group

# CRUD Service Integration (for MCP tools)
CRUD_SERVICE_URL=http://localhost:8000
```

## API Reference

### Agent REST Endpoint

**POST** `/invoke` - Get enriched product details with AI insights

**Request Body:**
```json
{
  "sku": "PROD-12345",
  "related_limit": 4,
  "cache_ttl": 300
}
```

**Parameters:**
- `sku` (required): Product SKU or ID
- `related_limit` (optional): Number of related products (default: 4)
- `cache_ttl` (optional): Hot memory cache TTL in seconds (default: 300)

**Response:**
```json
{
  "sku": "PROD-12345",
  "name": "Premium Wireless Headphones",
  "description": "Rich, ACP-supplied product description with full feature details.",
  "features": [
    "Active Noise Cancellation",
    "40-hour battery life",
    "Premium audio drivers"
  ],
  "rating": 4.6,
  "review_count": 128,
  "media": [
    {
      "type": "image",
      "url": "https://example.com/images/PROD-12345.png"
    }
  ],
  "inventory": {
    "stock_level": "in_stock",
    "quantity": 45,
    "warehouses": ["US-EAST", "US-WEST"]
  },
  "related": [
    {
      "sku": "PROD-12346",
      "name": "Wireless Charging Case",
      "price": 49.99
    }
  ],
  "product": {
    "sku": "PROD-12345",
    "name": "Premium Wireless Headphones",
    "price": 299.99,
    "category": "Electronics"
  }
}
```

**Response with AI Insights:**
```json
{
  "sku": "PROD-12345",
  "name": "Premium Wireless Headphones",
  "description": "...",
  "rating": 4.6,
  "review_count": 128,
  "inventory": {
    "stock_level": "in_stock",
    "quantity": 45
  },
  "insight": "Strong PDP with high rating (4.6/5, 128 reviews) and good stock (45 units). Content is complete with rich description and media. Conversion signals: Positive rating, adequate inventory. Monitor: Stock level (should maintain >20 units), review sentiment trends."
}
```

### MCP Tools (Agent-to-Agent Communication)

#### 1. Get Product Details
**POST** `/mcp/product/detail`

```json
{
  "sku": "PROD-12345",
  "related_limit": 4
}
```

Returns enriched product with all data sources merged.

**Response:**
```json
{
  "enriched_product": {
    "sku": "PROD-12345",
    "name": "Premium Wireless Headphones",
    "description": "Rich, ACP-supplied product description.",
    "features": ["Feature A", "Feature B"],
    "rating": 4.6,
    "review_count": 128,
    "inventory": {
      "stock_level": "in_stock",
      "quantity": 45
    },
    "related": [
      {"sku": "PROD-12346", "name": "Charging Case"}
    ],
    "product": {
      "sku": "PROD-12345",
      "price": 299.99
    }
  }
}
```

#### 2. Get Similar Products
**POST** `/mcp/product/similar`

```json
{
  "sku": "PROD-12345",
  "limit": 4
}
```

Returns related/similar products for cross-sell recommendations.

**Response:**
```json
{
  "sku": "PROD-12345",
  "related": [
    {
      "sku": "PROD-12346",
      "name": "Wireless Charging Case",
      "price": 49.99,
      "category": "Electronics"
    },
    {
      "sku": "PROD-12347",
      "name": "Premium Audio Cable",
      "price": 29.99,
      "category": "Accessories"
    }
  ]
}
```

## Enrichment Logic

### Data Merging Strategy

```python
# Priority: ACP Content > Catalog Data
enriched = {
    "sku": product.sku,
    "name": product.name,
    "description": acp_content.get("long_description") or product.description,
    "features": acp_content.get("features", []),
    "rating": review_summary.get("rating"),
    "review_count": review_summary.get("review_count"),
    "media": acp_content.get("media", []),
    "inventory": inventory.model_dump(),
    "related": [item.model_dump() for item in related],
    "product": product.model_dump()
}
```

### Parallel Data Fetching

All data sources are fetched concurrently:

```python
product, related, inventory, acp_content, review_summary = await asyncio.gather(
    adapters.products.get_product(sku),
    adapters.products.get_related(sku, limit=4),
    adapters.inventory.build_inventory_context(sku),
    adapters.acp.get_content(sku),
    adapters.reviews.get_summary(sku)
)
# Total latency = max(all adapters) instead of sum(all adapters)
```

### Conversion Impact Signals

| Signal | Impact | Action |
|--------|--------|--------|
| **Low Stock** (< 10 units) | High | Display urgency messaging |
| **Out of Stock** | Critical | Show alternatives, backorder option |
| **Low Rating** (< 3.5) | High | Highlight positive reviews, improve description |
| **Missing Media** | Medium | Request ACP content, use placeholders |
| **High Review Count** (> 100) | Positive | Feature social proof prominently |
| **Missing Features** | Medium | Flag for content team |

### Caching Strategy

```python
# Hot memory (Redis): 5-minute TTL for high-traffic PDPs
await hot_memory.set(
    key=f"pdp:{sku}",
    value=enriched,
    ttl_seconds=300
)

# Cache invalidation on product update events
```

## Event Processing

### Subscribed Events

| Event Hub | Consumer Group | Purpose |
|-----------|----------------|---------|
| `product-events` | `enrichment-group` | Auto-enrich when products are created/updated |

### Event Handling Logic

1. **Extract SKU**: Parse `sku`, `product_id`, or `id` from event payload
2. **Skip Invalid Events**: Log events without identifiable SKU
3. **Parallel Fetch**: Retrieve product, inventory, ACP content, reviews concurrently
4. **Merge Enrichment**: Combine all data sources into unified structure
5. **Log Results**: Structured logging with enrichment keys and data availability

**Event Types Processed:**
- `ProductCreated`: New product added to catalog
- `ProductUpdated`: Product data modified (price, description, media)
- `InventoryChanged`: Stock level update (triggers re-enrichment)
- `ReviewAdded`: New customer review (update rating/count)

### Event Processing Output

```json
{
  "event": "enrichment_event_processed",
  "event_type": "product.updated",
  "sku": "PROD-12345",
  "has_inventory": true,
  "review_count": 128,
  "has_product": true,
  "enrichment_keys": ["sku", "name", "description", "features", "rating", "inventory", "related"]
}
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
uvicorn ecommerce_product_detail_enrichment.main:app --reload --port 8024
```

### Testing

```bash
# Run unit tests
pytest apps/ecommerce-product-detail-enrichment/tests/

# Test agent endpoint - Basic enrichment
curl -X POST http://localhost:8024/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345"}'

# Test agent endpoint - With related products
curl -X POST http://localhost:8024/invoke \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345", "related_limit": 8}'

# Test MCP tool - Product Details
curl -X POST http://localhost:8024/mcp/product/detail \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345", "related_limit": 4}'

# Test MCP tool - Similar Products
curl -X POST http://localhost:8024/mcp/product/similar \
  -H "Content-Type: application/json" \
  -d '{"sku": "PROD-12345", "limit": 6}'
```

## Dependencies

- **holiday-peak-lib**: Shared framework (agents, adapters, memory, utilities)
- **FastAPI**: REST API and MCP server
- **Azure Event Hubs**: Async event processing
- **Azure AI Foundry**: SLM/LLM inference
- **Redis**: Hot memory (PDP caching)
- **Azure Cosmos DB**: Warm memory (recent enrichments)
- **Azure Blob Storage**: Cold memory (historical data)

## Agent Behavior

### System Instructions

The agent is instructed to:
- **Be proactive when enriching product details**: Combine all data sources comprehensively
- **Highlight conversion impact signals**: Flag low stock, missing media, low ratings
- **Monitor data completeness**: Track which signals need attention (stock, ratings, content)
- **Identify anomalies**: Call out missing data, outdated content, inconsistencies
- **Provide actionable insights**: Recommend next steps for PDP optimization

### SLM vs LLM Routing

| Query Type | Model | Reasoning |
|------------|-------|-----------|
| "Get product details for PROD-12345" | SLM | Straightforward data aggregation |
| "Show related products" | SLM | Simple recommendation retrieval |
| "Why is this PDP underperforming?" | LLM | Requires conversion analysis |
| "Optimize this product page for conversions" | LLM | Complex optimization recommendations |
| "Compare content quality across products" | LLM | Multi-product analysis |

## Integration Examples

### From Frontend (Product Detail Page)

```typescript
// React component - Product detail page
const { data: productData, isLoading } = useQuery({
  queryKey: ['product-detail', sku],
  queryFn: () => 
    fetch(`${AGENT_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ sku, related_limit: 4 })
    }).then(r => r.json()),
  staleTime: 300000  // Cache for 5 minutes
});

// Display enriched PDP
<ProductDetailView>
  <ProductImages media={productData?.media} />
  <ProductInfo 
    name={productData?.name}
    description={productData?.description}
    price={productData?.product?.price}
  />
  <ProductFeatures features={productData?.features} />
  <ProductReviews 
    rating={productData?.rating}
    count={productData?.review_count}
  />
  <StockIndicator inventory={productData?.inventory} />
  <RelatedProducts items={productData?.related} />
</ProductDetailView>

// Conversion impact warning
{productData?.inventory?.quantity < 10 && (
  <Alert severity="warning">
    Only {productData.inventory.quantity} left in stock!
  </Alert>
)}
```

### From CRUD Service (Via Agent Client)

```python
# CRUD service enriching product response
from crud_service.integrations.agent_client import get_agent_client

agent_client = get_agent_client()
enriched = await agent_client.call_endpoint(
    agent_url=settings.product_enrichment_agent_url,
    endpoint="/invoke",
    data={"sku": sku, "related_limit": 4},
    fallback_value={"sku": sku, "error": "enrichment unavailable"}
)

# Return enriched PDP to frontend
return EnrichedProductResponse(
    sku=sku,
    name=enriched["name"],
    description=enriched["description"],
    features=enriched["features"],
    rating=enriched["rating"],
    inventory=enriched["inventory"],
    related=enriched["related"]
)
```

### From Another Agent (MCP Tool)

```python
# Checkout support agent checking product availability via MCP
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://ecommerce-product-detail-enrichment:8024/mcp/product/detail",
        json={"sku": "PROD-12345"}
    )
    product_data = response.json()["enriched_product"]
    
    inventory = product_data.get("inventory", {})
    if inventory.get("stock_level") == "out_of_stock":
        # Suggest alternatives
        similar_response = await client.post(
            "http://ecommerce-product-detail-enrichment:8024/mcp/product/similar",
            json={"sku": "PROD-12345", "limit": 3}
        )
        alternatives = similar_response.json()["related"]
        await suggest_alternatives(cart_item, alternatives)
```

## Use Cases

### 1. High-Performance PDPs
Serve enriched product pages with all data pre-aggregated:
```python
enriched = await get_enriched_product(sku="PROD-12345")
render_pdp(enriched)
# Single API call returns: catalog + ACP + reviews + inventory + related
```

### 2. Conversion Rate Optimization
Identify and fix PDP issues automatically:
```python
enriched = await get_enriched_product(sku="PROD-12345")
if enriched["review_count"] < 5:
    flag_for_review_collection(sku)
if not enriched["media"]:
    request_acp_media(sku)
if enriched["inventory"]["quantity"] < 10:
    enable_urgency_messaging(sku)
```

### 3. Personalized Recommendations
Use related products for cross-sell:
```python
similar = await get_similar_products(sku="PROD-12345", limit=4)
display_recommendation_carousel(similar["related"])
# "Customers who viewed this also liked..."
```

### 4. Content Quality Monitoring
Track PDP completeness across catalog:
```python
products = await get_all_products()
for product in products:
    enriched = await get_enriched_product(sku=product.sku)
    completeness_score = calculate_completeness(enriched)
    if completeness_score < 0.7:
        flag_for_content_team(product.sku)
```

### 5. Real-Time Inventory Updates
Auto-refresh PDPs when stock changes:
```python
# Event handler: InventoryChanged → Re-enrich PDP
async def handle_inventory_event(event):
    sku = event["sku"]
    enriched = await get_enriched_product(sku=sku)
    await update_pdp_cache(sku, enriched)
    # Frontend fetches fresh data from cache
```

## Monitoring & Observability

### Key Metrics

- `enrichment_event_processed`: Event processing count with data source availability
- `enrichment_event_skipped`: Events without identifiable SKU
- `enrichment_cache_hit_rate`: Hot memory cache efficiency
- `enrichment_latency_by_source`: Per-adapter response time (product, inventory, ACP, reviews)
- `enrichment_missing_data`: Count by data source (inventory, ACP, reviews)
- `pdp_conversion_signal`: Distribution of conversion impact signals (low_stock, missing_media, low_rating)

### Logs

All operations emit structured logs with correlation IDs:

```json
{
  "event": "enrichment_event_processed",
  "event_type": "product.updated",
  "sku": "PROD-12345",
  "has_inventory": true,
  "review_count": 128,
  "has_product": true,
  "enrichment_keys": ["sku", "name", "description", "features", "rating", "inventory", "related"],
  "timestamp": "2026-02-03T10:30:00Z"
}
```

## Production Considerations

### Resilience
- **Circuit Breaker**: All adapter calls have circuit breakers
- **Fallback**: Returns partial enrichment if data sources unavailable
- **Timeout**: Fast timeouts prevent cascading failures (500ms per adapter)
- **Retry Logic**: Exponential backoff for transient failures

### Scalability
- **Stateless Agent**: Horizontal scaling via Kubernetes/Container Apps
- **Event Processing**: Consumer group allows parallel processing across partitions
- **Memory Tiering**: Hot (Redis) → Warm (Cosmos) → Cold (Blob) for PDP cache
- **Cache Prewarming**: Pre-enrich high-traffic products during off-peak hours

### Performance
- **Parallel Fetching**: All adapters called concurrently (total latency = max, not sum)
- **Hot Memory**: 5-minute cache for PDPs (sub-10ms retrieval)
- **Lazy Loading**: Only fetch related products when requested
- **CDN Integration**: Serve media assets via CDN, not inline

### Security
- **Authentication**: Azure Managed Identity for Event Hubs, Cosmos DB, Blob Storage
- **API Keys**: Azure AI Foundry uses key-based auth (rotate regularly)
- **Data Validation**: Sanitize user input (SKU) to prevent injection attacks
- **Network Isolation**: Deploy in private subnet with service endpoints

### Content Quality
- **ACP Validation**: Verify ACP content completeness before merging
- **Review Moderation**: Filter inappropriate reviews before display
- **Media Validation**: Ensure media URLs are accessible and secure (HTTPS)
- **Data Freshness**: Monitor staleness of ACP content, reviews, inventory

## Advanced Features (Future)

### AI-Powered Descriptions
- **Dynamic Rewriting**: Generate descriptions tailored to user intent
- **SEO Optimization**: Optimize description for search keywords
- **A/B Testing**: Test multiple description variants for conversion

### Visual Enrichment
- **Image Recognition**: Extract features from product images
- **Video Generation**: Auto-generate product videos from images
- **AR Integration**: Enable augmented reality product previews
- **360° Views**: Stitch images into interactive 360° view

### Personalized PDPs
- **User-Specific Content**: Customize description based on user segment
- **Dynamic Pricing**: Show personalized discounts/offers
- **Localized Content**: Translate descriptions to user's language
- **Purchase History**: Highlight features relevant to past purchases

### Content Generation
- **Feature Extraction**: Auto-generate feature list from description
- **Comparison Tables**: Create comparison charts vs. similar products
- **Benefit Mapping**: Transform features into customer benefits
- **Social Proof**: Highlight trending products, bestsellers

## Related Services

- **ecommerce-catalog-search**: Provides ACP-compliant product feed
- **ecommerce-cart-intelligence**: Uses enriched data for cart recommendations
- **crud-service**: Transactional API for product management (called via MCP tools)
- **inventory-health-check**: Monitors stock levels for enrichment

## License

See repository root for license information.
