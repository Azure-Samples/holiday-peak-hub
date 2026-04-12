# C4 Component Diagram - Production Architecture

**Date**: January 30, 2026  
**Version**: 1.0  
**Diagram Level**: C3 (Component)

---

## Overview

This document contains the C4 Component-level diagram (Level 3) for the Holiday Peak Hub production architecture, showing the detailed component interactions between frontend, CRUD service, 21 agent services, and data layers.

---

## Component Diagram

```mermaid
C4Component
    title Component Diagram - Holiday Peak Hub Production Architecture

    Container_Boundary(frontend, "Frontend Layer") {
        Component(nextjs, "Next.js App", "React 19, TypeScript", "User interface with SSR/CSR")
        Component(auth_context, "Auth Context", "MSAL React", "Microsoft Entra ID integration")
    }

    Container_Boundary(gateway, "API Gateway Layer") {
        Component(apim, "Azure API Management", "API Gateway", "Rate limiting, auth, routing")
        ComponentDb(apim_cache, "Response Cache", "Redis", "API response caching")
    }

    Container_Boundary(crud_boundary, "CRUD Service") {
        Component(crud_api, "FastAPI App", "Python 3.13", "31 REST endpoints")
        Component(auth_deps, "Auth Dependencies", "JWT validation", "RBAC with 4 roles")
        Component(crud_repos, "Repositories", "Base + 4 repos", "User, Product, Order, Cart")
        Component(event_pub, "Event Publisher", "Azure SDK", "Publishes to Event Hubs")
        Component(agent_client, "Agent Client", "httpx + circuitbreaker", "Calls agent REST endpoints (NOT MCP)")
    }

    Container_Boundary(agents_ecommerce, "E-commerce Agents") {
        Component(catalog_search, "Catalog Search", "Agent + AI Search", "Semantic product search")
        Component(enrichment, "Product Enrichment", "Agent", "ACP metadata generation")
        Component(cart_intel, "Cart Intelligence", "Agent + ML", "Personalized recommendations")
        Component(checkout_support, "Checkout Support", "Agent", "Validation & dynamic pricing")
        Component(order_status, "Order Status", "Agent", "Proactive tracking")
    }

    Container_Boundary(agents_crm, "CRM Agents") {
        Component(profile_agg, "Profile Aggregation", "Agent", "Unified customer view")
        Component(segmentation, "Segmentation", "Agent + ML", "Dynamic cohorts")
        Component(campaign_intel, "Campaign Intelligence", "Agent + ML", "ROI-optimized campaigns")
        Component(support_assist, "Support Assistance", "Agent + RAG", "Augmented support")
    }

    Container_Boundary(agents_inventory, "Inventory Agents") {
        Component(health_check, "Health Check", "Agent", "Predictive stock-out alerts")
        Component(jit_replenish, "JIT Replenishment", "Agent", "Demand-sensing reorder")
        Component(reservation, "Reservation Validation", "Agent", "Real-time locking")
        Component(alerts_triggers, "Alerts/Triggers", "Agent", "Exception notifications")
    }

    Container_Boundary(agents_logistics, "Logistics Agents") {
        Component(eta_compute, "ETA Computation", "Agent", "Real-time delivery predictions")
        Component(carrier_select, "Carrier Selection", "Agent", "Cost/speed optimization")
        Component(returns_support, "Returns Support", "Agent", "Reverse logistics")
        Component(route_detect, "Route Issue Detection", "Agent", "Proactive delay mitigation")
    }

    Container_Boundary(agents_product, "Product Management Agents") {
        Component(normalize, "Normalization", "Agent", "Auto-classify & clean")
        Component(acp_transform, "ACP Transform", "Agent", "Standards-compliant export")
        Component(consistency_val, "Consistency Validation", "Agent", "Data quality checks")
        Component(assortment_opt, "Assortment Optimization", "Agent + ML", "SKU mix recommendations")
    }

    Container_Boundary(data_layer, "Data Layer") {
        ComponentDb(cosmos, "Cosmos DB", "NoSQL Database", "10 operational containers")
        ComponentDb(cosmos_memory, "Cosmos DB Memory", "NoSQL Database", "Warm tier (conversation history)")
        ComponentDb(redis, "Redis Cache Premium", "In-memory", "Hot tier (session state)")
        ComponentDb(blob, "Blob Storage", "Object Store", "Cold tier (archival)")
        ComponentQueue(eventhub, "Event Hubs", "Messaging", "5 topics with consumer groups")
        ComponentDb(search_index, "AI Search", "Search Service", "Vector + hybrid search")
    }

    Container_Boundary(platform, "Azure Platform Services") {
        Component(monitor, "Azure Monitor", "Observability", "Logs, metrics, distributed tracing")
        Component(keyvault, "Key Vault", "Secrets Management", "Connection strings, API keys")
        Component(app_insights, "Application Insights", "APM", "Performance monitoring")
    }

    ' Frontend → Gateway
    Rel(nextjs, apim, "HTTPS/REST", "All API calls")
    Rel(auth_context, nextjs, "Provides JWT", "Token management")

    ' Gateway → CRUD (Primary path for transactions)
    Rel(apim, crud_api, "HTTPS/REST", "Transactional operations")
    Rel(apim, apim_cache, "TCP", "Cache lookups")

    ' Gateway → Agents (Direct for semantic capabilities)
    Rel(apim, catalog_search, "HTTPS/REST", "Semantic search (bypasses CRUD)")
    Rel(apim, campaign_intel, "HTTPS/REST", "Campaign analytics (staff only)")

    ' CRUD → Auth
    Rel(crud_api, auth_deps, "Uses", "JWT validation & RBAC")

    ' CRUD → Repositories
    Rel(crud_api, crud_repos, "Uses", "Data operations")
    Rel(crud_repos, cosmos, "TCP/HTTPS", "CRUD operations on 10 containers")

    ' Agents → CRUD REST endpoints (for transactional operations)
    Rel(reservation, crud_api, "HTTPS", "Update order status via REST")
    Rel(health_check, crud_api, "HTTPS", "Query inventory via REST")
    Rel(support_assist, crud_api, "HTTPS", "Create tickets via REST")

    ' CRUD → Event Publishing
    Rel(crud_api, event_pub, "Uses", "On mutations")
    Rel(event_pub, eventhub, "AMQP", "5 event types")

    ' CRUD → Agent Client (Sync with circuit breaker - REST endpoints only)
    Rel(crud_api, agent_client, "Uses", "Optional enrichment")
    Rel(agent_client, enrichment, "HTTP REST (500ms timeout)", "/enrich endpoint + fallback")
    Rel(agent_client, cart_intel, "HTTP REST (500ms timeout)", "/recommendations endpoint + fallback")

    ' Event Hubs → Agents (Async event processing)
    Rel(eventhub, catalog_search, "AMQP", "product-events → catalog-search-group")
    Rel(eventhub, enrichment, "AMQP", "product-events → enrichment-group")
    Rel(eventhub, cart_intel, "AMQP", "order-events → cart-intel-group")
    Rel(eventhub, checkout_support, "AMQP", "inventory-events → checkout-group")
    Rel(eventhub, order_status, "AMQP", "order-events → order-status-group")
    
    Rel(eventhub, profile_agg, "AMQP", "user-events + order-events → profile-agg-group")
    Rel(eventhub, segmentation, "AMQP", "order-events → segmentation-group")
    Rel(eventhub, campaign_intel, "AMQP", "order-events + payment-events → campaign-intel-group")
    Rel(eventhub, support_assist, "AMQP", "order-events → support-group")
    
    Rel(eventhub, health_check, "AMQP", "order-events + inventory-events → health-check-group")
    Rel(eventhub, jit_replenish, "AMQP", "inventory-events → replenishment-group")
    Rel(eventhub, reservation, "AMQP", "order-events → reservation-group")
    Rel(eventhub, alerts_triggers, "AMQP", "inventory-events → alerts-group")
    
    Rel(eventhub, eta_compute, "AMQP", "order-events → eta-group")
    Rel(eventhub, carrier_select, "AMQP", "order-events → carrier-group")
    Rel(eventhub, returns_support, "AMQP", "order-events → returns-group")
    Rel(eventhub, route_detect, "AMQP", "order-events → route-group")
    
    Rel(eventhub, normalize, "AMQP", "product-events → normalization-group")
    Rel(eventhub, acp_transform, "AMQP", "product-events → acp-transform-group")
    Rel(eventhub, consistency_val, "AMQP", "product-events → validation-group")
    Rel(eventhub, assortment_opt, "AMQP", "order-events + product-events → assortment-group")

    ' Agents → Data Layer (Three-tier memory + operational data)
    Rel(catalog_search, search_index, "HTTPS", "Vector search")
    Rel(catalog_search, redis, "TCP", "Hot memory (session state)")
    Rel(catalog_search, cosmos_memory, "TCP/HTTPS", "Warm memory (conversation history)")
    Rel(catalog_search, blob, "HTTPS", "Cold memory (archival)")
    
    Rel(enrichment, cosmos, "TCP/HTTPS", "Store enrichments")
    Rel(profile_agg, cosmos, "TCP/HTTPS", "Store profiles")
    Rel(campaign_intel, cosmos, "TCP/HTTPS", "Campaign data")
    
    Rel(health_check, redis, "TCP", "Cache stock levels")
    Rel(reservation, cosmos, "TCP/HTTPS", "Reservation locks")

    ' All Agents → Platform Services
    Rel(crud_api, monitor, "HTTPS", "Structured logs + traces")
    Rel(catalog_search, monitor, "HTTPS", "Agent telemetry")
    Rel(enrichment, monitor, "HTTPS", "Agent telemetry")
    Rel(profile_agg, monitor, "HTTPS", "Agent telemetry")
    
    Rel(crud_api, keyvault, "HTTPS", "Fetch secrets")
    Rel(catalog_search, keyvault, "HTTPS", "Fetch secrets")
    Rel(profile_agg, keyvault, "HTTPS", "Fetch secrets")
    
    Rel(monitor, app_insights, "Internal", "APM data")

    UpdateLayoutConfig($c4ShapeInRow="4", $c4BoundaryInRow="2")
```

---

## Component Descriptions

**Architecture Overview**:
- **CRUD REST endpoints** → Called by Frontend AND Agents (for transactional operations)
- **Agent REST endpoints** → Called by Frontend, CRUD, and other services (for intelligence/enrichment)
- **Agent MCP tools** → Called by agents only (agent-to-agent communication, indexed and discoverable)
- **Event Hubs** → CRUD publishes, agents subscribe (async processing)

### Frontend Layer

#### Next.js App
- **Technology**: React 19, Next.js 15, TypeScript, Tailwind CSS
- **Pattern**: App Router with server-side rendering
- **Authentication**: Microsoft Entra ID via MSAL
- **Responsibilities**:
  - User interface rendering
  - Client-side routing
  - API consumption (CRUD + direct agent calls)
  - Session management

#### Auth Context
- **Technology**: `@azure/msal-react`
- **Pattern**: Context provider with hooks
- **Responsibilities**:
  - JWT token acquisition
  - Token refresh
  - Silent authentication
  - RBAC role validation

---

### API Gateway Layer

#### Azure API Management
- **Tier**: Standard V2
- **Responsibilities**:
  - Rate limiting (100 req/min per IP)
  - JWT validation
  - Request routing (CRUD vs Agents)
  - Response caching
  - API versioning
  - CORS handling

**Routing Rules**:
- `/api/*` → CRUD Service (transactions)
- `/agents/catalog-search/*` → Catalog Search Agent (semantic search)
- `/agents/campaign-intelligence/*` → Campaign Intelligence Agent (analytics, staff only)

---

### CRUD Service

#### FastAPI App
- **Framework**: FastAPI 0.109+
- **Endpoints**: 31 total
  - Anonymous: 7 (health, product browsing)
  - Customer: 18 (cart, orders, checkout)
  - Staff: 4 (analytics, tickets)
  - Admin: 2 (returns processing)
- **Features**:
  - Async/await throughout
  - Pydantic validation
  - OpenAPI documentation
  - Lifespan management

#### Auth Dependencies
- **Library**: `python-jose`, `cryptography`
- **Validation**:
  - JWT signature verification
  - Audience validation (api://crud-service)
  - Issuer validation (Microsoft Entra ID)
  - Expiration check
- **RBAC**: 4 roles (anonymous, customer, staff, admin)

#### Repositories
- **Pattern**: Repository pattern with async
- **Implementations**:
  - `UserRepository`: User profiles, addresses
  - `ProductRepository`: Product catalog
  - `OrderRepository`: Order headers + items
  - `CartRepository`: Shopping carts
- **Base**: `BaseRepository` with common CRUD operations

#### Event Publisher
- **Library**: `azure-eventhub`
- **Topics**: 5 (user-events, product-events, order-events, inventory-events, payment-events)
- **Pattern**: Fire-and-forget with batching
- **Schema**: Standardized event envelope with metadata

#### Agent Client
- **Library**: `httpx`, `circuitbreaker`, `tenacity`
- **Important**: Calls agent **REST endpoints**, NOT MCP tools (MCP is agent-to-agent only)
- **Features**:
  - Circuit breaker (5 failures → 60s recovery)
  - Timeout (500ms for sync calls)
  - Retry (2 attempts, exponential backoff)
  - Fallback responses
- **Use Cases**:
  - Product enrichment (optional) via `/enrich` endpoint
  - Cart recommendations (optional) via `/recommendations` endpoint

---

### Agent Services (21 Total)

#### Common Pattern
All agents follow the same structure:
- **Base Class**: `BaseRetailAgent` from `holiday_peak_lib`
- **Memory**: Three-tier (Hot: Redis, Warm: Cosmos DB, Cold: Blob)
- **Event Handling**: Async event consumer with checkpoint
- **MCP Tools**: Exposed via `FastAPIMCPServer` for **agent-to-agent** communication
- **REST Endpoints**: Exposed for CRUD service to call (e.g., `/enrich`, `/recommendations`)
- **Observability**: Structured logging to Azure Monitor

**Dual Interface Pattern**:
```python
# REST endpoint for CRUD service
@app.post("/enrich")
async def enrich_product(request: EnrichRequest):
    return await agent.enrich(request.product_id)

# MCP tool for agent-to-agent communication
@mcp_server.tool()
async def get_enrichment(product_id: str) -> dict:
    return await agent.enrich(product_id)
```

#### E-commerce Domain (5 Agents)

##### Catalog Search
- **Capability**: Semantic product search
- **Technologies**: Azure AI Search (vector + hybrid), OpenAI embeddings
- **Event Topics**: `product-events` (updates search index)
- **Exposed**: Directly via API Gateway for semantic queries

##### Product Enrichment
- **Capability**: ACP metadata generation
- **Event Topics**: `product-events` (enrich on create/update)
- **Invoked By**: 
  - CRUD service (sync via `/enrich` REST endpoint with fallback)
  - Other agents (via MCP tool `get_enrichment`)

##### Cart Intelligence
- **Capability**: Personalized recommendations
- **Technologies**: Collaborative filtering, content-based recommendations
- **Event Topics**: `order-events` (update models)
- **Invoked By**: 
  - CRUD service (sync via `/recommendations` REST endpoint with fallback)
  - Other agents (via MCP tool `get_recommendations`)

##### Checkout Support
- **Capability**: Validation, dynamic pricing, scarcity messaging
- **Event Topics**: `inventory-events` (adjust rules)

##### Order Status
- **Capability**: Proactive order tracking
- **Event Topics**: `order-events` (update status cache)

#### CRM Domain (4 Agents)

##### Profile Aggregation
- **Capability**: Unified customer view
- **Event Topics**: `user-events`, `order-events` (enrich profiles)
- **Storage**: Cosmos DB profiles container

##### Segmentation/Personalization
- **Capability**: Dynamic customer cohorts
- **Technologies**: K-means clustering, RFM analysis
- **Event Topics**: `order-events` (recalculate segments)

##### Campaign Intelligence
- **Capability**: ROI-optimized marketing automation
- **Event Topics**: `order-events`, `payment-events` (track conversions)
- **Exposed**: Directly via API Gateway for staff analytics

##### Support Assistance
- **Capability**: Agent-augmented customer service
- **Technologies**: RAG with knowledge base
- **Event Topics**: `order-events` (flag support issues)

#### Inventory Domain (4 Agents)

##### Health Check
- **Capability**: Predictive stock-out alerts
- **Event Topics**: `order-events`, `inventory-events` (monitor levels)

##### JIT Replenishment
- **Capability**: Demand-sensing reorder triggers
- **Event Topics**: `inventory-events` (low stock → generate PO)

##### Reservation Validation
- **Capability**: Real-time inventory locking
- **Event Topics**: `order-events` (reserve on order creation)
- **Pattern**: SAGA participant (compensating transactions)

##### Alerts/Triggers
- **Capability**: Exception-based notifications
- **Event Topics**: `inventory-events` (send alerts)

#### Logistics Domain (4 Agents)

##### ETA Computation
- **Capability**: Real-time delivery predictions
- **Event Topics**: `order-events` (compute on shipment)
- **APIs**: Carrier APIs (FedEx, UPS, USPS)

##### Carrier Selection
- **Capability**: Cost/speed trade-off optimization
- **Event Topics**: `order-events` (select on ready-to-ship)

##### Returns Support
- **Capability**: Reverse logistics automation
- **Event Topics**: `order-events` (generate return labels)

##### Route Issue Detection
- **Capability**: Proactive delay mitigation
- **Event Topics**: `order-events` (monitor in-transit)

#### Product Management Domain (4 Agents)

##### Normalization/Classification
- **Capability**: Auto-classify & clean product data
- **Technologies**: NLP classification, data cleaning
- **Event Topics**: `product-events` (normalize on create)

##### ACP Transformation
- **Capability**: Standards-compliant catalog export
- **Event Topics**: `product-events` (transform to ACP schema)

##### Consistency Validation
- **Capability**: Real-time data quality checks
- **Event Topics**: `product-events` (validate on create/update)

##### Assortment Optimization
- **Capability**: ML-driven SKU mix recommendations
- **Event Topics**: `order-events`, `product-events` (optimize based on sales)

---

### Data Layer

#### Cosmos DB (Operational)
- **API**: NoSQL (SQL API)
- **Partition Strategy**: Domain-specific keys
- **Containers**: 10 operational
  1. Users (`/userId`)
  2. Products (`/category`)
  3. Orders (`/userId`)
  4. OrderItems (`/orderId`)
  5. Cart (`/userId`)
  6. Reviews (`/productId`)
  7. PaymentMethods (`/userId`)
  8. Tickets (`/userId`)
  9. Shipments (`/orderId`)
  10. AuditLogs (`/entityType`)

#### Cosmos DB (Memory - Warm Tier)
- **Purpose**: Conversation history (1-30 days retention)
- **Containers**: Per-agent memory containers
- **Access Pattern**: Agents read/write via `AgentMemory` abstraction

#### Redis Cache Premium
- **Size**: 6GB
- **Purpose**: Hot tier memory (< 50ms latency)
- **TTL**: 30 minutes (session state), 5 minutes (product cache)
- **Access Pattern**: All agents + CRUD service

#### Blob Storage
- **Tier**: Hot
- **Purpose**: Cold tier memory (archival, > 30 days)
- **Access Pattern**: Agents archive via `AgentMemory`

#### Event Hubs
- **Namespace**: Standard tier with auto-inflate
- **Topics**: 5
  1. `user-events` (2 consumer groups)
  2. `product-events` (7 consumer groups)
  3. `order-events` (14 consumer groups)
  4. `inventory-events` (4 consumer groups)
  5. `payment-events` (1 consumer group)
- **Retention**: 7 days
- **Partitions**: 32 per topic

#### AI Search
- **Tier**: Standard
- **Purpose**: Vector + hybrid search for product catalog
- **Index**: Products (embeddings + keyword)
- **Access**: Catalog Search Agent only

---

### Azure Platform Services

#### Azure Monitor
- **Components**: Log Analytics + Metrics
- **Sources**: CRUD service + 21 agents
- **Retention**: 90 days
- **Dashboards**: Performance, errors, business metrics

#### Key Vault
- **Purpose**: Secret management
- **Secrets**:
  - Event Hub connection strings
  - Cosmos DB keys
  - Redis connection string
  - API keys (Stripe, carrier APIs)
- **Access**: Managed Identity (CRUD + agents)

#### Application Insights
- **Purpose**: APM (Application Performance Monitoring)
- **Features**:
  - Distributed tracing
  - Dependency tracking
  - Exception logging
  - Performance profiling

---

## Event Flow Examples

### Example 1: User Places Order (Async)

```
1. Frontend → API Gateway → CRUD API: POST /orders
2. CRUD API → Cosmos DB: Insert order
3. CRUD API → Event Hubs: Publish "order.placed" event
4. CRUD API → Frontend: 202 Accepted (order ID)

5. Event Hubs → Profile Aggregation Agent: Process event
   - Update user profile (order count, LTV)
   
6. Event Hubs → Segmentation Agent: Process event
   - Recalculate customer segment
   
7. Event Hubs → Health Check Agent: Process event
   - Check inventory levels for ordered SKUs
   
8. Event Hubs → Reservation Validation Agent: Process event
   - Reserve inventory for order
   - Publish "inventory.reserved" event
   
9. Event Hubs → ETA Computation Agent: Process event
   - Compute delivery ETA
   - Store in Redis cache
```

**Total Time**: ~2-5 seconds for async processing  
**User Experience**: Immediate response (202), background enrichment

---

### Example 2: User Searches Products (Sync + Direct)

```
1. Frontend → API Gateway: POST /agents/catalog-search/semantic
   Body: { "query": "winter jackets for hiking" }

2. API Gateway: Validate JWT, check rate limit

3. API Gateway → Catalog Search Agent: Forward request

4. Catalog Search Agent:
   - Generate query embedding (OpenAI)
   - Vector search in AI Search
   - Rank results
   - Return products

5. Catalog Search Agent → API Gateway: 200 OK (products)

6. API Gateway → Frontend: Return cached or live results
```

**Total Time**: ~200-500ms (direct to agent)  
**Fallback**: If agent fails, API Gateway returns cached results

---

### Example 3: User Adds to Cart (Sync with Circuit Breaker)

```
1. Frontend → API Gateway → CRUD API: POST /cart/items

2. CRUD API → Cosmos DB: Insert cart item

3. CRUD API → Agent Client: invoke_tool(cart-intelligence, "get_recommendations")
   - Timeout: 500ms
   - Circuit breaker: Monitors failures
   
4a. Success Path:
    Agent Client → Cart Intelligence Agent: HTTP POST
    Agent → CRUD API: Recommendations
    CRUD API → Frontend: Cart + recommendations

4b. Failure Path (timeout or error):
    Agent Client: Return fallback (trending products)
    CRUD API → Frontend: Cart + trending products (degraded)
```

**Total Time**: ~100ms (base) + 200ms (agent if available)  
**Resilience**: Falls back to trending products if agent unavailable

---

## Deployment Topology

### Kubernetes Namespaces

```
holiday-peak-hub (AKS cluster)
│
├── namespace: holiday-peak-crud
│   ├── deployment: crud-service (3 replicas)
│   ├── service: crud-service-svc
│   └── hpa: crud-service-hpa (3-20 replicas)
│
└── namespace: holiday-peak-agents
    │
    ├── eCommerce Domain
    │   ├── deployment: catalog-search (3 replicas)
    │   ├── deployment: product-enrichment (2 replicas)
    │   ├── deployment: cart-intelligence (2 replicas)
    │   ├── deployment: checkout-support (2 replicas)
    │   └── deployment: order-status (2 replicas)
    │
    ├── CRM Domain
    │   ├── deployment: profile-aggregation (2 replicas)
    │   ├── deployment: segmentation (2 replicas)
    │   ├── deployment: campaign-intelligence (2 replicas)
    │   └── deployment: support-assistance (2 replicas)
    │
    ├── Inventory Domain
    │   ├── deployment: health-check (2 replicas)
    │   ├── deployment: jit-replenishment (2 replicas)
    │   ├── deployment: reservation-validation (3 replicas)
    │   └── deployment: alerts-triggers (2 replicas)
    │
    ├── Logistics Domain
    │   ├── deployment: eta-computation (2 replicas)
    │   ├── deployment: carrier-selection (2 replicas)
    │   ├── deployment: returns-support (2 replicas)
    │   └── deployment: route-detection (2 replicas)
    │
    ├── Product Management Domain
    │   ├── deployment: normalization (2 replicas)
    │   ├── deployment: acp-transformation (2 replicas)
    │   ├── deployment: consistency-validation (2 replicas)
    │   └── deployment: assortment-optimization (2 replicas)
    │
    ├── Search Domain
    │   └── deployment: search-enrichment-agent (2 replicas)
    │
    └── Truth Layer Domain
        ├── deployment: truth-ingestion (2 replicas)
        ├── deployment: truth-enrichment (2 replicas)
        ├── deployment: truth-hitl (2 replicas)
        └── deployment: truth-export (2 replicas)
```

**Total Pods**: ~55 (CRUD: 3-20, Agents: 2-3 each × 26)

---

## Network Diagram

```
Internet
   │
   ▼
Azure Front Door (CDN)
   │
   ├─→ Static Web App (Next.js)
   │
   └─→ API Management (API Gateway)
          │
          ├─→ CRUD Service (AKS)
          │     │
          │     ├─→ Cosmos DB
          │     ├─→ Redis Cache
          │     └─→ Event Hubs
          │
          └─→ Agent Services (AKS)
                │
                ├─→ Catalog Search
                ├─→ Campaign Intelligence
                └─→ (other 19 agents via Event Hubs)
```

**Private Endpoints**: All Azure services accessed via private endpoints (no public IPs)  
**Virtual Network**: Single VNet with subnets (AKS, data services, agents)

---

## Related Documents

- [Implementation Plan](./architecture-implementation-plan.md)
- [Compliance Analysis](./compliance-analysis.md)
- [Architecture Overview](../architecture/architecture.md)
- [CRUD Service Implementation](../architecture/crud-service-implementation.md)

---

**End of C4 Component Diagram Documentation**
