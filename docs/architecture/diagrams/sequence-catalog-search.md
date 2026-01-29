# Sequence Diagram: E-commerce Catalog Search Flow

This diagram illustrates the end-to-end flow for product search in the Holiday Peak Hub accelerator.

## Flow Overview

1. **User Query** → API Gateway
2. **SLM-First Routing** → Complexity assessment
3. **Search Execution** → Azure AI Search (vector + hybrid)
4. **Inventory Validation** → Check stock availability
5. **Personalization** → Rank based on user preferences
6. **Response Assembly** → Return ACP-aligned results

## Sequence Diagram

```mermaid
sequenceDiagram
    actor User
    participant API as FastAPI App
    participant Agent as Catalog Agent
    participant Router as Model Router
    participant SLM as GPT-4o-mini
    participant LLM as GPT-4o
    participant Search as Azure AI Search
    participant Inventory as Inventory Adapter
    participant Memory as Memory Stack
    participant Embedding as Embedding Model

    User->>API: POST /invoke {"query": "red sneakers"}
    API->>Agent: invoke(query)
    
    Note over Agent: Step 1: Assess Complexity
    Agent->>Router: assess_complexity("red sneakers")
    Router->>Router: Analyze query tokens
    Router-->>Agent: complexity = MODERATE
    
    Note over Agent: Step 2: Try SLM First
    Agent->>Memory: get(user_profile)
    Memory-->>Agent: {preferences: {brand: "Nike"}}
    
    Agent->>SLM: invoke(query, context)
    SLM-->>Agent: {intent: "search", confidence: 0.85}
    
    Note over Agent: Confidence OK (>0.8)
    
    Note over Agent: Step 3: Generate Embedding
    Agent->>Embedding: embed("red sneakers")
    Embedding-->>Agent: [0.23, 0.67, ..., 0.91]
    
    Note over Agent: Step 4: Search Execution
    Agent->>Search: hybrid_search(query, vector)
    activate Search
    Search->>Search: Vector similarity + keyword match
    Search-->>Agent: [product1, product2, product3]
    deactivate Search
    
    Note over Agent: Step 5: Inventory Check
    par Parallel Inventory Checks
        Agent->>Inventory: check_stock(product1.sku)
        Inventory-->>Agent: {available: 45}
        Agent->>Inventory: check_stock(product2.sku)
        Inventory-->>Agent: {available: 0}
        Agent->>Inventory: check_stock(product3.sku)
        Inventory-->>Agent: {available: 12}
    end
    
    Note over Agent: Step 6: Personalization
    Agent->>Agent: rank_for_user(results, preferences)
    Agent->>Agent: filter_out_of_stock()
    
    Note over Agent: Step 7: Cache Results
    Agent->>Memory: set(recent_search, results, ttl=300)
    Memory-->>Agent: OK
    
    Agent-->>API: SearchResponse(products=[...])
    API-->>User: 200 OK {products: [...]}
    
    Note over User,Memory: Escalation Path (if needed)
    
    User->>API: POST /invoke {"query": "compare performance..."}
    API->>Agent: invoke(query)
    Agent->>Router: assess_complexity(query)
    Router-->>Agent: complexity = COMPLEX
    
    Agent->>LLM: invoke(query, context)
    activate LLM
    LLM->>LLM: Multi-step reasoning
    LLM-->>Agent: DetailedComparison
    deactivate LLM
    
    Agent-->>API: ComparisonResponse
    API-->>User: 200 OK {comparison: {...}}
```

## Key Decision Points

### 1. Complexity Assessment
**Location**: Model Router  
**Decision**: Route to SLM or LLM based on query complexity
- **Simple/Moderate** → Try SLM first
- **Complex** → Skip directly to LLM

### 2. Confidence Check
**Location**: Agent  
**Decision**: Accept SLM response or escalate to LLM
- **Confidence > 0.8** → Return SLM response
- **Confidence ≤ 0.8** → Escalate to LLM

### 3. Inventory Filtering
**Location**: Agent  
**Decision**: Include/exclude out-of-stock items
- **Default**: Filter out items with `available = 0`
- **Optional**: Show out-of-stock with backorder info

### 4. Personalization Strategy
**Location**: Agent  
**Decision**: Apply user preferences to ranking
- **No profile** → Rank by relevance score only
- **Profile exists** → Boost preferred brands/categories

## Performance Characteristics

| Step | Target Latency | Optimization |
|------|----------------|--------------|
| Complexity assessment | < 10ms | Cached patterns |
| SLM invocation | < 500ms | Small model |
| Embedding generation | < 100ms | Batch embedding |
| Search execution | < 200ms | Indexed fields |
| Inventory check (parallel) | < 300ms | Async + connection pool |
| Personalization | < 50ms | In-memory ranking |
| **Total (P95)** | **< 1.2s** | |

## Error Handling

### Search Failures
```python
try:
    results = await search.hybrid_search(query, vector)
except SearchUnavailableError:
    # Fallback to cached popular products
    results = await memory.get("popular_products")
```

### Inventory Timeout
```python
try:
    stock = await asyncio.wait_for(
        inventory.check_stock(sku),
        timeout=0.5
    )
except asyncio.TimeoutError:
    # Assume in stock, but flag as uncertain
    stock = {"available": -1, "uncertain": True}
```

### Model Unavailable
```python
try:
    response = await llm.invoke(query)
except ModelThrottledError:
    # Fallback to SLM with best effort
    response = await slm.invoke(query, force=True)
```

## Observability

### Metrics Tracked
```python
# Request metrics
metrics.histogram("search.latency_ms", duration)
metrics.counter("search.requests", {"status": "success"})

# Model routing
metrics.counter("model.invocations", {"model": "slm|llm"})
metrics.counter("model.escalations")
metrics.histogram("model.confidence", confidence)

# Search quality
metrics.histogram("search.result_count", len(results))
metrics.counter("search.zero_results")
metrics.histogram("search.relevance_score", avg_score)

# Inventory checks
metrics.histogram("inventory.check_latency_ms", duration)
metrics.counter("inventory.out_of_stock", {"sku": sku})
```

### Distributed Tracing
```python
from opencensus.trace import tracer

with tracer.span(name="catalog_search") as span:
    span.add_attribute("query", query)
    span.add_attribute("user_id", user_id)
    
    with tracer.span(name="search_execution"):
        results = await search.hybrid_search(query, vector)
    
    with tracer.span(name="inventory_check"):
        await check_inventory_parallel(results)
```

## Related Documentation
- [ADR-013: SLM-First Model Routing](../adrs/adr-013-model-routing.md)
- [ADR-011: ACP Alignment for Catalog Search](../adrs/adr-011-acp-catalog-search.md)
- [E-commerce Catalog Search Component](../components/apps/ecommerce-catalog-search.md)
