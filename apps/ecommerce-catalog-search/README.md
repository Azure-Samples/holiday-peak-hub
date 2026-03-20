# Ecommerce Catalog Search Service

Intelligent agent service for ACP (Agentic Commerce Protocol) compliant product catalog discovery with semantic search, inventory-aware results, and standardized product feed formatting.

## Overview

The Ecommerce Catalog Search service provides AI-powered product discovery by implementing the Agentic Commerce Protocol (ACP) product feed conventions. It combines product data, inventory availability, and semantic search capabilities to deliver accurate, actionable product results for shopping experiences.

## Architecture

### Components

```
ecommerce-catalog-search/
├── agents.py              # CatalogSearchAgent with SLM/LLM routing
├── adapters.py            # Product, inventory, and ACP mapping adapters
├── event_handlers.py      # Event Hub subscriber for product events
└── main.py                # FastAPI application with MCP tools
```

### Communication Patterns

1. **Agent REST Endpoints** (`/invoke`): Synchronous product search requests from frontend/CRUD
2. **MCP Tools**: Agent-to-agent communication for catalog queries
3. **Event Handlers**: Asynchronous processing of product events for catalog updates

## Features

### 🔍 ACP-Compliant Product Discovery
- **Semantic Search**: AI-powered product discovery (query → relevant products)
- **Inventory-Aware Results**: Real-time availability status (in_stock, out_of_stock, unknown)
- **ACP Product Feed Formatting**: Standardized fields per Agentic Commerce Protocol
- **Eligibility Filtering**: Only return products meeting search/checkout criteria

**ACP Product Feed Fields:**
- **item_id**: Unique product identifier (SKU)
- **title**: Product name
- **description**: Product description
- **url**: Product detail page URL
- **image_url**: Primary product image
- **brand**: Product brand/manufacturer
- **price**: Price with currency (e.g., "29.99 usd")
- **availability**: Stock status (in_stock, out_of_stock, unknown)
- **is_eligible_search**: Can appear in search results
- **is_eligible_checkout**: Can be purchased
- **store_name**: Seller/store name
- **seller_url**: Store homepage URL
- **seller_privacy_policy**: Privacy policy URL
- **seller_tos**: Terms of service URL
- **return_policy**: Returns policy URL
- **return_window**: Return window (days)
- **target_countries**: Supported countries (array)
- **store_country**: Store location country

### 🤖 AI-Powered Intelligence
- **SLM-First Routing**: Fast responses for simple product lookups
- **LLM Escalation**: Complex queries requiring semantic understanding
- **Dual-Path Search Modes**:
  - `keyword`: deterministic SKU-oriented path on `AI_SEARCH_INDEX`
  - `intelligent`: intent classification + multi-query hybrid retrieval on `AI_SEARCH_VECTOR_INDEX`
- **Query Understanding**: Natural language to product mapping
- **Missing Field Detection**: Flag incomplete products

### 🧠 Vector/Hybrid Search Enrichment
- **Vector Retrieval**: Uses `VectorizableTextQuery` against `product_search_index`
- **Hybrid Retrieval**: Combines keyword text scoring with semantic vector similarity
- **Intent Decomposition**: Breaks complex user intent into sub-queries and merges ranked results
- **Extended Search Fields**: `use_cases`, `complementary_products`, `substitute_products`, `enriched_description`

### 📊 Real-Time Event Processing
- **Product Events**: Process product create/update/delete events
- **Inventory Sync**: Update availability status from inventory events
- **ACP Transformation**: Convert internal product data to ACP format

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
REDIS_URL=redis://localhost:6379/0            # Hot memory (search cache)
COSMOS_ACCOUNT_URI=<cosmos-uri>               # Warm memory (recent searches)
COSMOS_DATABASE=holiday-peak
COSMOS_CONTAINER=agent-memory
BLOB_ACCOUNT_URL=<blob-uri>                   # Cold memory (historical data)
BLOB_CONTAINER=agent-memory

# Event Hub Configuration
EVENTHUB_NAMESPACE=<namespace>.servicebus.windows.net
EVENTHUB_CONNECTION_STRING=<connection-string>
# Subscriptions: product-events
# Consumer Group: catalog-search-group

# Azure AI Search Configuration
AI_SEARCH_ENDPOINT=https://<service>.search.windows.net
AI_SEARCH_INDEX=catalog-products
AI_SEARCH_VECTOR_INDEX=product_search_index
AI_SEARCH_VECTOR_FIELD=content_vector            # Optional; defaults to content_vector
AI_SEARCH_AUTH_MODE=managed_identity             # or api_key
AI_SEARCH_KEY=<search-admin-key>                 # Required when auth mode is api_key
EMBEDDING_DEPLOYMENT_NAME=<embedding-deployment> # Required for vectorizable query text

# CRUD Service Integration (for MCP tools)
CRUD_SERVICE_URL=http://localhost:8000
```

## API Reference

### Agent REST Endpoint

**POST** `/invoke` - Search product catalog with ACP-compliant results

**Request Body:**
```json
{
  "query": "wireless mouse",
  "limit": 5,
  "mode": "keyword"
}
```

**Response:**
```json
{
  "service": "ecommerce-catalog-search",
  "query": "wireless mouse",
  "mode": "keyword",
  "results": [
    {
      "item_id": "SKU-001",
      "title": "Logitech MX Master 3",
      "description": "Advanced wireless mouse with ergonomic design",
      "url": "https://example.com/products/SKU-001",
      "image_url": "https://example.com/images/SKU-001.jpg",
      "brand": "Logitech",
      "price": "99.99 usd",
      "availability": "in_stock",
      "is_eligible_search": true,
      "is_eligible_checkout": true,
      "store_name": "Example Store",
      "seller_url": "https://example.com/store",
      "seller_privacy_policy": "https://example.com/privacy",
      "seller_tos": "https://example.com/terms",
      "return_policy": "https://example.com/returns",
      "return_window": 30,
      "target_countries": ["US"],
      "store_country": "US"
    }
  ]
}
```

### MCP Tools (Agent-to-Agent Communication)

#### 1. Search Catalog
**POST** `/mcp/catalog/search`

```json
{
  "query": "wireless mouse",
  "limit": 5,
  "mode": "keyword"
}
```

Returns ACP-compliant product results.

**Response:**
```json
{
  "query": "wireless mouse",
  "mode": "keyword",
  "intent": null,
  "results": [
    {
      "item_id": "SKU-001",
      "title": "Logitech MX Master 3",
      "price": "99.99 usd",
      "availability": "in_stock",
      ...
    }
  ]
}
```

`mode` supports `keyword` (default) and `intelligent`.

#### 2. Classify Catalog Intent
**POST** `/mcp/catalog/intent`

```json
{
  "query": "best headphones for long flights"
}
```

**Response:**
```json
{
  "query": "best headphones for long flights",
  "complexity": 0.94,
  "intent": {
    "intent": "semantic_search",
    "confidence": 0.92,
    "entities": {
      "use_case": "travel",
      "features": ["noise cancellation", "wireless"]
    }
  }
}
```

#### 3. Get Product Details
**POST** `/mcp/catalog/product`

```json
{
  "sku": "SKU-001"
}
```

Returns single product with full ACP fields.

**Response:**
```json
{
  "product": {
    "item_id": "SKU-001",
    "title": "Logitech MX Master 3",
    "description": "Advanced wireless mouse with ergonomic design",
    "url": "https://example.com/products/SKU-001",
    "image_url": "https://example.com/images/SKU-001.jpg",
    "brand": "Logitech",
    "price": "99.99 usd",
    "availability": "in_stock",
    "is_eligible_search": true,
    "is_eligible_checkout": true,
    ...
  }
}
```

## ACP (Agentic Commerce Protocol)

### Protocol Compliance

This service implements the **Agentic Commerce Protocol (ACP) Product Feed** specification, ensuring:

1. **Required Fields Populated**: All mandatory fields (item_id, title, price, availability) present
2. **Accurate Availability**: Real-time inventory checks before returning results
3. **Eligibility Flags**: Products marked as searchable and purchasable
4. **Seller Metadata**: Store information and policies included
5. **Standardized Format**: Consistent field names and data types

### ACP Product Feed Mapping

```python
# Internal Product Schema → ACP Product Feed
{
  "sku": "SKU-001",                  # Internal identifier
  "name": "Logitech MX Master 3",    # Internal name
  "price": 99.99,                    # Internal price
  ...
}

# Mapped to ACP:
{
  "item_id": "SKU-001",              # ACP: Unique identifier
  "title": "Logitech MX Master 3",   # ACP: Display name
  "price": "99.99 usd",              # ACP: Price with currency
  "availability": "in_stock",        # ACP: Real-time stock status
  ...
}
```

### Availability Status

| Internal Inventory | ACP Status | Meaning |
|-------------------|------------|---------|
| `available > 0` | `in_stock` | Product can be purchased |
| `available = 0` | `out_of_stock` | Product unavailable |
| `null` or error | `unknown` | Inventory status cannot be determined |

### Quality Guarantees

**System Instructions:**
> "Follow the Agentic Commerce Protocol product feed conventions: only surface items with required fields populated and accurate availability. If any required field is missing, exclude the item and explain why."

This ensures:
- ✅ No incomplete products in search results
- ✅ Real-time availability (no stale data)
- ✅ Consistent data quality across all queries

## Event Processing

### Subscribed Events

| Event Hub | Consumer Group | Purpose |
|-----------|----------------|---------|
| `product-events` | `catalog-search-group` | Update catalog with product changes |

### Event Handling Logic

1. **Extract Product SKU**: Parse `sku`, `product_id`, or `id` from event payload
2. **Skip Invalid Events**: Log and skip events without identifiable product
3. **Fetch Product Data**: Retrieve product details from product adapter
4. **Check Inventory**: Query inventory adapter for availability status
5. **Transform to ACP**: Convert product + availability to ACP format
6. **Log Processing**: Structured logging with availability and ACP fields

**Event Types Processed:**
- `ProductCreated`: New product added to catalog
- `ProductUpdated`: Product details changed (price, description, etc.)
- `ProductDeleted`: Product removed from catalog
- `InventoryUpdated`: Stock levels changed (updates availability)

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
uvicorn ecommerce_catalog_search.main:app --reload --port 8021
```

### Testing

```bash
# Run unit tests
pytest apps/ecommerce-catalog-search/tests/

# Test agent endpoint
curl -X POST http://localhost:8021/invoke \
  -H "Content-Type: application/json" \
  -d '{
    "query": "wireless mouse",
    "limit": 5
  }'

# Test MCP tool - Search
curl -X POST http://localhost:8021/mcp/catalog/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "laptop",
    "limit": 3
  }'

# Test MCP tool - Product Details
curl -X POST http://localhost:8021/mcp/catalog/product \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU-001"}'

# Health check
curl http://localhost:8021/health
```

## Dependencies

- **holiday-peak-lib**: Shared framework (agents, adapters, memory, utilities)
- **FastAPI**: REST API and MCP server
- **Azure Event Hubs**: Async event processing
- **Azure AI Foundry**: SLM/LLM inference
- **Redis**: Hot memory (search result caching)
- **Azure Cosmos DB**: Warm memory (recent searches)
- **Azure Blob Storage**: Cold memory (historical data)

## Agent Behavior

### System Instructions

The agent is instructed to:
- **Follow ACP conventions**: Only return products with required fields populated
- **Ensure accurate availability**: Verify inventory status before returning
- **Exclude incomplete items**: Filter out products missing required fields
- **Explain exclusions**: Log why products were filtered out
- **Return ACP-aligned fields**: Use standardized field names and formats

### SLM vs LLM Routing

| Query Type | Model | Reasoning |
|------------|-------|-----------|
| "Show products for SKU-001" | SLM | Direct product lookup |
| "Search for wireless mouse" | SLM | Simple keyword matching |
| "Find eco-friendly office supplies" | LLM | Semantic understanding required |
| "Recommend products similar to laptop but cheaper" | LLM | Complex comparison + reasoning |
| "What products are trending in electronics?" | LLM | Trend analysis across catalog |

## Integration Examples

### From Frontend (Search Page)

```typescript
// React component - Product search
const { data: searchResults, isLoading } = useQuery({
  queryKey: ['catalog-search', searchQuery],
  queryFn: () => 
    fetch(`${AGENT_URL}/invoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: searchQuery,
        limit: 20
      })
    }).then(r => r.json()),
  enabled: searchQuery.length > 2  // Only search if query has 3+ chars
});

// Display results with ACP fields
{searchResults?.results?.map(product => (
  <ProductCard
    key={product.item_id}
    title={product.title}
    price={product.price}
    imageUrl={product.image_url}
    availability={product.availability}
    isEligibleCheckout={product.is_eligible_checkout}
  />
))}
```

### From CRUD Service (Via Agent Client)

```python
# CRUD service calling catalog search
from crud_service.integrations.agent_client import get_agent_client

agent_client = get_agent_client()
results = await agent_client.call_endpoint(
    agent_url=settings.catalog_search_agent_url,
    endpoint="/invoke",
    data={"query": "wireless mouse", "limit": 10},
    fallback_value={"results": []}  # Empty results on failure
)
```

### From Another Agent (MCP Tool)

```python
# Product enrichment agent calling catalog search via MCP
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://ecommerce-catalog-search:8021/mcp/catalog/product",
        json={"sku": "SKU-001"}
    )
    product_data = response.json()
    
    # Use ACP fields for enrichment
    acp_product = product_data["product"]
    enriched_description = f"{acp_product['description']} - {acp_product['brand']}"
```

## Use Cases

### 1. Product Search
Semantic search with natural language queries:
```python
results = await search_catalog(query="comfortable ergonomic office chair", limit=10)
# Returns chairs matching semantic meaning, not just keyword match
```

### 2. Product Recommendations
Find related products for cross-sell/upsell:
```python
primary = await get_product_details(sku="SKU-001")
query = f"products similar to {primary['title']}"
related = await search_catalog(query=query, limit=5)
```

### 3. Inventory-Aware Display
Show only in-stock products:
```python
results = await search_catalog(query="laptop", limit=20)
in_stock_only = [p for p in results if p["availability"] == "in_stock"]
```

### 4. Multi-Channel Commerce
Expose catalog via ACP for external platforms:
```python
# Shopping assistant agents from other platforms can consume ACP feed
acp_feed = await search_catalog(query="all products", limit=1000)
# Returns standardized format compatible with external shopping assistants
```

### 5. Product Data Quality
Validate catalog completeness:
```python
all_products = await search_catalog(query="*", limit=10000)
incomplete = [p for p in all_products if not p.get("description")]
# Identify products missing required fields
```

## Monitoring & Observability

### Key Metrics

- `catalog_event_processed`: Event processing count with availability distribution
- `catalog_event_skipped`: Events without valid product identifier
- `catalog_event_missing_product`: Events where product lookup failed
- `catalog_search_queries_total`: Total search requests
- `catalog_search_response_time`: Search latency (SLM vs LLM)
- `catalog_acp_compliance_rate`: Percentage of products meeting ACP requirements

### Logs

All operations emit structured logs with correlation IDs:

```json
{
  "event": "catalog_event_processed",
  "event_type": "product.updated",
  "sku": "SKU-001",
  "availability": "in_stock",
  "title": "Logitech MX Master 3",
  "acp_item_id": "SKU-001",
  "timestamp": "2026-02-03T10:30:00Z"
}
```

## Production Considerations

### Resilience
- **Circuit Breaker**: Product and inventory adapter calls have circuit breakers
- **Fallback**: Returns empty results if adapters unavailable
- **Timeout**: Fast timeouts prevent cascading failures
- **Availability Fallback**: Returns "unknown" if inventory check fails

### Scalability
- **Stateless Agent**: Horizontal scaling via Kubernetes/Container Apps
- **Event Processing**: Consumer group allows parallel processing across partitions
- **Memory Tiering**: Hot (Redis) → Warm (Cosmos) → Cold (Blob) for search cache
- **Search Result Caching**: Redis cache for frequent queries

### Performance
- **Parallel Inventory Checks**: All availability lookups concurrent (asyncio.gather)
- **Result Limit**: Default 5 products (configurable)
- **Query Coercion**: Simple hash-based SKU mapping for demo (replace with semantic search)

### Security
- **Authentication**: Azure Managed Identity for Event Hubs, Cosmos DB, Blob Storage
- **API Keys**: Azure AI Foundry uses key-based auth (rotate regularly)
- **Data Privacy**: Product data public (no PII in catalog)
- **Network Isolation**: Deploy in private subnet with service endpoints

### Data Quality
- **Required Field Validation**: Filter out products missing mandatory fields
- **Availability Accuracy**: Real-time inventory checks (no stale data)
- **ACP Compliance**: Automated validation of ACP format
- **Seller Metadata**: Store policies included (privacy, TOS, returns)

## Advanced Features (Future)

### Semantic Search Enhancements
- **Vector Embeddings**: Store product embeddings for true semantic search
- **Query Expansion**: Expand user queries with synonyms and related terms
- **Personalization**: Rank results based on user preferences and history
- **Multi-Language Support**: Search in multiple languages with translation

### Inventory Intelligence
- **Predictive Availability**: Forecast stock-out dates
- **Alternative Suggestions**: Recommend substitutes when out of stock
- **Low-Stock Alerts**: Flag items nearing stock-out
- **Regional Availability**: Show stock per warehouse/region

### ACP Extensions
- **Dynamic Pricing**: Include promotional prices and discounts
- **Shipping Info**: Add estimated delivery dates
- **Product Variants**: Handle size/color variations
- **Ratings & Reviews**: Include aggregate ratings in feed

### Search Optimization
- **A/B Testing**: Test different ranking algorithms
- **Click-Through Tracking**: Measure search effectiveness
- **Faceted Search**: Add filters (brand, price, category)
- **Auto-Complete**: Suggest queries as user types

## Related Services

- **ecommerce-product-detail-enrichment**: Provides detailed product context for search results
- **ecommerce-cart-intelligence**: Uses catalog data for cart analysis
- **inventory-health-check**: Maintains availability accuracy
- **crud-service**: Transactional API for product CRUD (called via MCP tools)

## License

See repository root for license information.
