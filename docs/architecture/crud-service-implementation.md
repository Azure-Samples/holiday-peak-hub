# CRUD Service Implementation

**Status**: ✅ Implemented  
**Last Updated**: March 12, 2026  
**Version**: 1.1.0

## Overview

The **Holiday Peak Hub CRUD Service** is a FastAPI-based microservice that handles all transactional data operations and user-facing REST APIs. It serves as the primary backend for the Next.js frontend, providing authentication, product catalog management, cart operations, order processing, and staff/admin features.

## Key Characteristics

- **NOT an Agent Service**: Pure REST API microservice (no BaseRetailAgent, no memory tiers)
- **Event-Driven**: Publishes domain events to Azure Event Hubs for agent consumption
- **Stateless**: Horizontally scalable with managed identity authentication
- **RBAC-Enabled**: Microsoft Entra ID JWT validation with role-based access control
- **Production-Ready**: Comprehensive error handling, logging, observability, and test structure

---

## Architecture

### Service Boundaries

**What the CRUD Service Does**:
- ✅ User authentication and profile management
- ✅ Product catalog CRUD (fallback when agents unavailable)
- ✅ Shopping cart operations (add, update, remove items)
- ✅ Order creation and management
- ✅ Checkout validation and payment processing (Stripe integration)
- ✅ Customer reviews and ratings
- ✅ Staff analytics dashboards
- ✅ Support ticket management
- ✅ Return and shipment tracking (staff/admin)
- ✅ Event publishing for agent integration

**What the CRUD Service Does NOT Do**:
- ❌ AI-powered recommendations (handled by agents)
- ❌ Semantic product search (handled by `ecommerce-catalog-search` agent)
- ❌ Dynamic pricing (handled by agents)
- ❌ Inventory intelligence (handled by inventory agents)
- ❌ Route optimization (handled by logistics agents)
- ❌ Customer segmentation (handled by CRM agents)

### Integration Patterns

```
┌─────────────────┐
│  Next.js UI     │
│  (apps/ui)      │
└────────┬────────┘
         │ HTTP/REST
         ▼
┌─────────────────┐      ┌──────────────────┐
│  CRUD Service   │─────►│  PostgreSQL       │
│  REST Endpoints │      │  (JSONB tables)   │
│  /products      │      │  asyncpg pool     │
│  /orders        │      └──────────────────┘
│  /cart          │
└───┬─────────┬───┘
    │         │
    │         │ Publishes Events
    │         ▼
    │  ┌─────────────────┐      ┌──────────────────────┐
    │  │  Event Hubs     │─────►│  21 Agent Services   │
    │  │  (5 topics)     │      │  ┌────────────────┐  │
    │  └─────────────────┘      │  │ REST Endpoints │  │
    │         ▲               │  │ /enrich        │  │
    │         │               │  │ /search        │  │
    │         │               │  │ /recommend     │  │
    │         │               │  └────────────────┘  │
    │         │               │  ┌────────────────┐  │
    │         │ Agents can    │  │ MCP Tools      │  │
    │         │ call CRUD     │  │ (agent↔agent)  │  │
    │         └───────────────┤  └────────────────┘  │
    │                         └──────────────────────┘
    │                                   ▲
    │  CRUD calls agents via APIM       │
    │  (circuit breaker + retry)        │
    ▼                                   │
┌─────────────────┐                     │
│  Azure APIM     │─────────────────────┘
│  (Gateway)      │
│  Rate limiting  │
│  Auth policies  │
└─────────────────┘
```

**Architecture Notes**:
- **CRUD REST endpoints**: Called by Frontend AND Agents (when agents need transactional operations)
- **Agent REST endpoints**: Called by CRUD via **APIM gateway** with circuit breaker + retry
- **Agent MCP tools**: Called by agents only (agent-to-agent communication)
- **Event Hubs**: CRUD publishes, agents subscribe (async processing)
- **APIM**: All CRUD→Agent traffic routes through Azure API Management for rate limiting, auth, and observability

---

## Implementation Details

### Project Structure

```
apps/crud-service/
├── src/
│   └── crud_service/
│       ├── main.py                    # FastAPI app (31 endpoints)
│       ├── config/
│       │   └── settings.py            # Pydantic Settings (PostgreSQL, APIM, agents)
│       ├── auth/
│       │   └── dependencies.py        # JWKS-based JWT validation, RBAC
│       ├── repositories/
│       │   ├── base.py                # Base PostgreSQL repository (asyncpg + JSONB)
│       │   ├── user.py
│       │   ├── product.py
│       │   ├── order.py
│       │   └── cart.py
│       ├── routes/
│       │   ├── health.py              # Health checks
│       │   ├── auth.py                # Authentication
│       │   ├── users.py               # User management
│       │   ├── products.py            # Product CRUD
│       │   ├── categories.py          # Categories
│       │   ├── cart.py                # Cart management
│       │   ├── orders.py              # Order management
│       │   ├── checkout.py            # Checkout flow
│       │   ├── payments.py            # Payment processing
│       │   ├── reviews.py             # Reviews
│       │   └── staff/
│       │       ├── analytics.py       # Analytics dashboard
│       │       ├── tickets.py         # Support tickets
│       │       ├── returns.py         # Return management
│       │       └── shipments.py       # Shipment tracking
│       ├── integrations/
│       │   ├── event_publisher.py     # Event Hubs publisher
│       │   └── agent_client.py        # APIM-routed agent calls (circuit breaker + retry)
│       └── scripts/
│           └── seed_demo_data.py      # Faker-based demo data seeder
├── tests/
│   ├── conftest.py                    # Shared fixtures
│   ├── unit/
│   │   ├── test_health.py
│   │   ├── test_repositories.py
│   │   ├── test_agent_client.py       # Circuit breaker, retry, APIM routing
│   │   ├── test_auth.py              # JWKS caching, JWT validation
│   │   └── test_settings.py          # Configuration validation
│   ├── integration/
│   │   ├── test_products_api.py       # Live PostgreSQL integration
│   │   ├── test_cart_api.py
│   │   └── conftest.py               # Per-test TestClient, pool reset
│   └── e2e/
│       └── test_checkout_flow.py
├── Dockerfile                         # Python 3.13 multi-stage
├── .env.example                       # Environment template (PostgreSQL, APIM, agents)
└── README.md
```

### API Endpoints (current implementation)

#### Anonymous Access (7 endpoints)
- `GET /health` - Health check
- `GET /health/live` - Liveness probe
- `GET /health/ready` - Readiness probe
- `GET /products` - List products (with search/filter)
- `GET /products/{id}` - Get product details
- `GET /categories` - List categories
- `GET /categories/{slug}` - Get category

#### Authenticated - Customer (10 endpoints)
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/register` - User registration
- `GET /users/me` - Get current user profile
- `PUT /users/me` - Update profile
- `GET /cart` - Get user's cart
- `POST /cart/items` - Add item to cart
- `PUT /cart/items/{id}` - Update cart item
- `DELETE /cart/items/{id}` - Remove cart item
- `POST /checkout/validate` - Validate checkout

#### Authenticated - Customer (continued) (9 endpoints)
- `POST /orders` - Create order
- `GET /orders` - List user's orders
- `GET /orders/{id}` - Get order details
- `GET /orders/{id}/track` - Track order shipment
- `POST /products/{id}/reviews` - Create review
- `GET /products/{id}/reviews` - Get product reviews
- `POST /payments/intent` - Create payment intent (Stripe)
- `POST /payments` - Server-side payment confirmation with payment method
- `POST /payments/confirm-intent` - Reconcile confirmed Stripe PaymentIntent to persisted payment + order
- `GET /payments/{id}` - Retrieve persisted payment details (ownership + role checks)

#### Authenticated - Staff (ticket and operations workflows)
- `GET /staff/analytics` - Sales analytics dashboard
- `GET /staff/tickets` - List support tickets
- `GET /staff/tickets/{id}` - Get ticket details
- `POST /staff/tickets` - Create support ticket (staff/admin)
- `PATCH /staff/tickets/{id}` - Update ticket fields/status (staff/admin)
- `POST /staff/tickets/{id}/escalate` - Escalate ticket with reason (staff/admin)
- `POST /staff/tickets/{id}/resolve` - Resolve ticket with note/reason (staff/admin)
- `GET /staff/shipments` - List shipments

#### Authenticated - Admin (2 endpoints)
- `GET /staff/returns` - List returns
- `PUT /staff/returns/{id}` - Process return

### Authentication & Authorization

**Microsoft Entra ID Integration**:
- OAuth 2.0 / OpenID Connect flow
- **JWKS-based JWT validation** with cached signing keys (TTL 3600s)
- `kid`-based key matching against Entra ID JWKS endpoint (`/discovery/v2.0/keys`)
- Graceful degradation: falls back to stale JWKS cache on fetch failure
- Token acquired via `@azure/msal-browser` (frontend)
- Token attached via Axios interceptors (Authorization: Bearer)

**Role-Based Access Control (RBAC)**:
```python
# auth/dependencies.py

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate JWT using JWKS and return user claims.
    
    1. Fetch JWKS from Entra ID (cached for JWKS_CACHE_TTL seconds)
    2. Match JWT 'kid' header to signing key
    3. Decode and validate: signature, audience, issuer, expiration
    4. Return UserClaims with oid, email, roles
    """

async def require_role(required_role: str):
    """Dependency for role-based access"""
    # Roles: 'anonymous', 'customer', 'staff', 'admin'
    # Extracted from JWT 'roles' claim
```

**Access Levels**:
| Role | Access |
|------|--------|
| **Anonymous** | Health checks, product browsing, categories |
| **Customer** | Cart, orders, reviews, profile, checkout |
| **Staff** | Analytics, ticket lifecycle actions (create/update/escalate/resolve), shipments |
| **Admin** | Returns (process), user management (future) |

### Database Schema

**PostgreSQL (JSONB tables via asyncpg)**:

All data is stored in PostgreSQL Flexible Server using JSONB columns. The `BaseRepository` manages table creation, connection pooling, and serialization.

**Connection Pool**:
- Shared `asyncpg.Pool` (class-level singleton)
- Configurable min/max pool sizes (`POSTGRES_MIN_POOL`, `POSTGRES_MAX_POOL`)
- SSL mode configurable (`POSTGRES_SSL`)

**Table Structure** (auto-created per entity):
```sql
CREATE TABLE IF NOT EXISTS {table_name} (
    id TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_{table_name}_data ON {table_name} USING GIN (data);
```

**Tables** (10):
1. **users** - User profiles, addresses, payment methods
2. **products** - Product catalog (ACP-compliant)
3. **orders** - Order headers
4. **order_items** - Order line items
5. **cart** - Shopping carts (session/user)
6. **reviews** - Product reviews and ratings
7. **payment_methods** - Saved payment methods
8. **tickets** - Support tickets
9. **shipments** - Shipment tracking
10. **audit_logs** - Audit trail for compliance

**Data Flow**:
- **Write**: `json.dumps(item)` → INSERT/UPDATE JSONB column
- **Read**: SELECT → `json.loads(row["data"])` → Python dict
- **Query**: In-memory filtering on deserialized JSONB (for compatibility with legacy Cosmos-style SQL queries)

### Event Publishing

**Event Hubs Topics** (5):
1. **user-events** - User registration, profile updates
2. **product-events** - Product created, updated, deleted
3. **order-events** - Order placed, status changed, cancelled
4. **inventory-events** - Stock updates (future)
5. **payment-events** - Payment succeeded, failed

**Event Schema**:
```python
{
    "event_id": "uuid",
    "event_type": "order.placed",
    "timestamp": "2026-01-29T10:30:00Z",
    "source": "crud-service",
    "data": {
        "order_id": "...",
        "user_id": "...",
        "total": 199.99
    },
    "metadata": {
        "correlation_id": "...",
        "causation_id": "..."
    }
}
```

**Agent Subscriptions**:
- **CRM agents**: Subscribe to `user-events`, `order-events`
- **Inventory agents**: Subscribe to `order-events`, `inventory-events`
- **Logistics agents**: Subscribe to `order-events`
- **Product agents**: Subscribe to `product-events`

### Checkout Payment Reconciliation Path

- Frontend-first flow uses `POST /payments/intent` + Stripe.js confirmation, then `POST /payments/confirm-intent`.
- Reconciliation validates order ownership and Stripe metadata (`order_id`, `user_id`) before persisting/returning payment.
- Existing payment records are reused when `order_id + transaction_id` already exists (idempotent behavior).
- Order status is updated to `paid` and `payment_id` is attached when needed.
- `payment.processed` event is published only when the order transitions from non-paid to paid.

### Agent Integration (APIM-Routed with Circuit Breaker)

**Resilient Agent Calls via APIM**:
```python
# integrations/agent_client.py

class AgentClient:
    """APIM-routed agent client with circuit breaker and retry.
    
    All 12 agent methods follow the same pattern:
    1. Resolve agent URL via APIM_BASE_URL + agent-specific path
    2. Call with circuit breaker (failure_threshold=5, recovery_timeout=60s)
    3. Retry with exponential backoff (3 attempts, 1-10s range)
    4. Return None on circuit-open or exhausted retries (graceful degradation)
    """
    
    # Uses httpx.AsyncClient for all HTTP calls
    # circuitbreaker library for fault isolation
    # tenacity library for retry with exponential backoff
```

**12 Agent Methods**:
| Method | Agent Service | Use Case |
|--------|--------------|----------|
| `enrich_product()` | product-detail-enrichment | AI-powered product descriptions |
| `get_cart_intelligence()` | ecommerce-cart-intelligence | Cart recommendations |
| `get_checkout_support()` | ecommerce-checkout-support | Checkout validation |
| `search_catalog()` | ecommerce-catalog-search | Semantic product search |
| `get_order_status()` | ecommerce-order-status | Intelligent order tracking |
| `get_crm_profile()` | crm-profile-aggregation | Customer 360 profile |
| `get_crm_campaign()` | crm-campaign-intelligence | Campaign recommendations |
| `get_crm_segmentation()` | crm-segmentation-personalization | Customer segments |
| `get_crm_support()` | crm-support-assistance | AI-assisted support |
| `get_inventory_alerts()` | inventory-alerts-triggers | Stock level alerts |
| `get_logistics_eta()` | logistics-eta-computation | Delivery ETA |
| `get_logistics_carrier()` | logistics-carrier-selection | Carrier selection |

**Use Cases**:
- Product enrichment (call `product-detail-enrichment` agent)
- Cart intelligence (call `cart-intelligence` agent for recommendations)
- Checkout support (call `checkout-support` agent for validation)

**Fallback Strategy**:
- If agent unavailable (circuit open or retries exhausted), returns `None`
- Calling code falls back to basic CRUD operations
- Agent failures logged to Application Insights
- Return degraded response (e.g., product without AI enrichment)

### Configuration

**Environment Variables**:
```bash
# PostgreSQL
POSTGRES_HOST=your-server.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_DATABASE=holiday_peak_crud
POSTGRES_USER=crud_admin
POSTGRES_PASSWORD=<from Key Vault>
POSTGRES_SSL=require
POSTGRES_MIN_POOL=2
POSTGRES_MAX_POOL=10

# Azure Resources (Managed Identity)
EVENTHUB_NAMESPACE=holiday-peak-hub-events.servicebus.windows.net
REDIS_URL=redis://holiday-peak-hub-redis.redis.cache.windows.net:6380
KEYVAULT_URL=https://holiday-peak-hub-kv.vault.azure.net/

# Authentication (Microsoft Entra ID / JWKS)
ENTRA_TENANT_ID=your-tenant-id
ENTRA_CLIENT_ID=your-client-id
ENTRA_ISSUER=https://sts.windows.net/{tenant_id}/
JWKS_CACHE_TTL=3600

# APIM Gateway
APIM_BASE_URL=https://your-apim.azure-api.net

# Agent URLs (12 agent services via APIM)
PRODUCT_ENRICHMENT_AGENT_URL=${APIM_BASE_URL}/product-enrichment
CART_INTELLIGENCE_AGENT_URL=${APIM_BASE_URL}/cart-intelligence
CHECKOUT_SUPPORT_AGENT_URL=${APIM_BASE_URL}/checkout-support
CATALOG_SEARCH_AGENT_URL=${APIM_BASE_URL}/catalog-search
ORDER_STATUS_AGENT_URL=${APIM_BASE_URL}/order-status
CRM_PROFILE_AGENT_URL=${APIM_BASE_URL}/crm-profile
CRM_CAMPAIGN_AGENT_URL=${APIM_BASE_URL}/crm-campaign
CRM_SEGMENTATION_AGENT_URL=${APIM_BASE_URL}/crm-segmentation
CRM_SUPPORT_AGENT_URL=${APIM_BASE_URL}/crm-support
INVENTORY_ALERTS_AGENT_URL=${APIM_BASE_URL}/inventory-alerts
LOGISTICS_ETA_AGENT_URL=${APIM_BASE_URL}/logistics-eta
LOGISTICS_CARRIER_AGENT_URL=${APIM_BASE_URL}/logistics-carrier

# Circuit Breaker
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_RECOVERY_TIMEOUT=60

# Stripe (Secret from Key Vault)
STRIPE_SECRET_KEY=sk_test_xxx

# Observability
APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey=xxx

# Feature Flags
ENABLE_AGENT_CALLS=true
ENABLE_EVENT_PUBLISHING=true
```

### Observability

**Application Insights Integration**:
- Distributed tracing (correlation IDs)
- Custom metrics (request latency, error rates)
- Dependency tracking (PostgreSQL, Event Hubs, APIM agent calls)
- Exception logging with stack traces

**Structured Logging**:
```python
import structlog

logger = structlog.get_logger()
logger.info(
    "order_created",
    order_id=order.id,
    user_id=order.user_id,
    total=order.total
)
```

**Health Checks**:
- `/health` - Overall health (200 OK)
- `/health/live` - Liveness (Kubernetes liveness probe)
- `/health/ready` - Readiness (checks PostgreSQL, Event Hubs)

---

## Testing Strategy

### Test Structure

**Unit Tests** (`tests/unit/`) — 10 files:
- Repository CRUD operations (mocked PostgreSQL pool)
- Auth dependencies (JWKS caching, JWT validation, kid matching)
- Agent client (circuit breaker, retry, APIM routing, graceful degradation)
- Settings validation (PostgreSQL, APIM, agent URLs, circuit breaker)
- Event publisher (mocked Event Hubs)
- Health endpoints

**Integration Tests** (`tests/integration/`) — 3 files:
- API endpoints against **live PostgreSQL** (Azure Flexible Server)
- Per-test `TestClient` fixture (avoids asyncio event loop reuse)
- `BaseRepository._pool = None` reset in teardown for clean pool state
- Auth override fixture (bypasses JWT validation)

**End-to-End Tests** (`tests/e2e/`) — 1 file:
- Checkout flow (add to cart → checkout → order)

### Test Coverage

**Current**: **87 tests passing** (85 unit + 2 integration)

**Critical Paths**:
- Authentication (JWKS caching, JWT validation, RBAC) - 100%
- Agent client (circuit breaker, retry, degradation) - 100%
- Repository CRUD operations - 90%
- API endpoints (happy path + error cases) - 80%
- Event publishing - 90%

### Running Tests

```bash
# Unit tests only
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# E2E tests (requires mocked dependencies)
pytest tests/e2e/ -v

# All tests with coverage
pytest --cov=crud_service --cov-report=html
```

---

## Deployment

### Docker

**Dockerfile** (Python 3.13, multi-stage):
```dockerfile
FROM python:3.13-slim AS base
WORKDIR /app
COPY src/pyproject.toml .
RUN pip install -e .

FROM base AS production
COPY src/crud_service ./crud_service
CMD ["uvicorn", "crud_service.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build & Run**:
```bash
docker build -t crud-service:latest .
docker run -p 8000:8000 --env-file .env crud-service:latest
```

### Kubernetes (AKS)

**Deployment** (dedicated node pool):
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crud-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: crud-service
  template:
    metadata:
      labels:
        app: crud-service
    spec:
      nodeSelector:
        agentpool: crud  # Dedicated node pool
      containers:
      - name: crud-service
        image: holiday-peak-hub-acr.azurecr.io/crud-service:latest
        ports:
        - containerPort: 8000
        env:
        - name: COSMOS_ACCOUNT_URI
          valueFrom:
            secretKeyRef:
              name: crud-secrets
              key: cosmos-uri
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

**Autoscaling** (HPA):
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: crud-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: crud-service
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Frontend Integration

### API Client

**Axios Client** (`apps/ui/lib/api/client.ts`):
```typescript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  timeout: 10000,
});

// Request interceptor: Attach JWT token
apiClient.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor: Handle 401/403
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Redirect to login
      window.location.href = '/login';
    }
    throw error;
  }
);
```

### Service Layer

**Product Service** (`apps/ui/lib/services/productService.ts`):
```typescript
import { apiClient } from '../api/client';

export const productService = {
  list: async (filters?: { search?: string; category?: string }) => {
    const response = await apiClient.get('/products', { params: filters });
    return response.data;
  },
  get: async (id: string) => {
    const response = await apiClient.get(`/products/${id}`);
    return response.data;
  },
};
```

### React Query Hooks

**useProducts Hook** (`apps/ui/lib/hooks/useProducts.ts`):
```typescript
import { useQuery } from '@tanstack/react-query';
import { productService } from '../services/productService';

export function useProducts(filters?: { search?: string; category?: string }) {
  return useQuery({
    queryKey: ['products', filters],
    queryFn: () => productService.list(filters),
    staleTime: 60 * 1000, // 1 minute
  });
}
```

### Authentication

**Auth Context** (`apps/ui/contexts/AuthContext.tsx`):
- Uses `@azure/msal-react` for Microsoft Entra ID integration
- Client-side only (SSR-safe with dynamic import)
- Token acquisition with silent + popup fallback
- Stores token in sessionStorage for API calls

**Protected Routes**:
```typescript
import { withAuth } from '@/contexts/AuthContext';

function CheckoutPage() {
  return <div>Protected checkout page</div>;
}

export default withAuth(CheckoutPage);
```

### Documentation

See [apps/ui/INTEGRATION.md](../../apps/ui/INTEGRATION.md) for complete frontend integration guide.

---

## Performance Considerations

### PostgreSQL Optimization

- **Connection Pooling**: Shared `asyncpg.Pool` class-level singleton (configurable min/max)
- **JSONB Indexes**: GIN indexes on `data` column for fast JSON path queries
- **B-tree Index**: On `id` column (primary key) for fast lookups
- **SSL**: TLS connections to Azure PostgreSQL Flexible Server
- **Async I/O**: All database operations use `asyncpg` async driver

### Caching

- **Redis**: Cache frequently accessed data (product catalog, user profiles)
- **TTL Strategy**: Products (5 min), User profiles (1 min), Cart (30 sec)
- **Cache Invalidation**: Publish invalidation events on updates

### Horizontal Scaling

- **Stateless Design**: No in-memory state (scales horizontally)
- **Load Balancing**: AKS Ingress distributes requests across pods
- **Autoscaling**: HPA scales based on CPU/memory (3-20 replicas)

---

## Security Considerations

### Authentication

- ✅ Microsoft Entra ID (OAuth 2.0 / OIDC)
- ✅ JWT validation (signature, audience, issuer, expiration)
- ✅ No passwords stored (delegated to Entra ID)

### Authorization

- ✅ Role-based access control (RBAC)
- ✅ Principle of least privilege
- ✅ API endpoints protected by role dependencies

### Data Protection

- ✅ Managed Identity (no hardcoded credentials)
- ✅ Secrets in Azure Key Vault
- ✅ TLS/HTTPS only (enforced by APIM)
- ✅ Private Endpoints (PostgreSQL, Event Hubs in production)

### Input Validation

- ✅ Pydantic models for request validation
- ✅ SQL injection prevention (parameterized queries)
- ✅ XSS prevention (sanitize user input)

---

## Monitoring & Alerting

### Key Metrics

- **Request Rate**: Requests per second (RPS)
- **Response Time**: p50, p95, p99 latency
- **Error Rate**: 4xx and 5xx error percentage
- **Dependency Latency**: PostgreSQL, Event Hubs, APIM agent call response times
- **Circuit Breaker State**: Open/closed/half-open per agent endpoint

### Alerts

- **Critical**: Error rate > 5% for 5 minutes
- **Warning**: p99 latency > 1 second for 5 minutes
- **Info**: Circuit breaker state change (open/closed/half-open)

### Dashboards

- **Grafana**: Real-time metrics (request rate, latency, errors)
- **Application Insights**: Distributed tracing, dependency map
- **Azure Monitor**: Resource health, scaling events

---

## Known Issues & TODO

### TODO Items in Routes

Several routes have `TODO` placeholders for future implementation:

1. **payments.py**:
   - Complete Stripe PaymentIntent retrieval
   - Add webhook handler for payment confirmation
   
2. **staff/analytics.py**:
   - Implement aggregation queries for sales metrics
   - Add time-series data (daily/weekly/monthly)
   
3. **checkout.py**:
   - Add inventory validation (call inventory agents)
   - Add address validation (geocoding)

4. **Test Mocks**:
   - ~~Complete Cosmos DB test fixtures in `conftest.py`~~ ✅ Replaced with asyncpg mocks
   - Add Event Hubs mock producer

### Future Enhancements

- [ ] Add GraphQL endpoint (optional alternative to REST)
- [ ] Implement webhook endpoint for Stripe events
- [ ] Add CSV/Excel export for staff analytics
- [ ] Implement soft delete for users and products
- [ ] Add batch operations for product updates
- [ ] Implement rate limiting per user (Redis-based)

---

## Related Documentation

- **[Implementation Roadmap](../IMPLEMENTATION_ROADMAP.md)** - Deployment and next steps
- **[Frontend Integration Guide](../../apps/ui/INTEGRATION.md)** - Frontend API setup
- **[CRUD Service README](../../apps/crud-service/README.md)** - Service-specific documentation
- **[ADR-019: Authentication & RBAC](./adrs/adr-019-authentication-rbac.md)** - Authentication decisions
- **[ADR-007: Event-Driven Architecture](./adrs/adr-007-saga-choreography.md)** - Event Hubs integration

---

## Conclusion

The **CRUD Service** is the foundational backend for the Holiday Peak Hub platform. It provides:

✅ **31 REST API endpoints** across 15 route modules  
✅ **PostgreSQL (asyncpg + JSONB)** data layer with connection pooling  
✅ **APIM-routed agent integration** with circuit breaker and retry (12 agent methods)  
✅ **JWKS-based JWT validation** with caching and graceful degradation  
✅ **Microsoft Entra ID authentication** with RBAC  
✅ **Event-driven integration** with 21 AI agents  
✅ **Complete frontend integration** (TypeScript client, services, hooks)  
✅ **87 tests passing** (unit, integration against live PostgreSQL, e2e)  
✅ **Production-ready**: Error handling, logging, observability, testing  

**Status**: Implementation complete and tested. Deployed via `azd` with CI/CD pipeline (`deploy-azd.yml`).

**Next Steps**: See [Implementation Roadmap - Phase 2](../IMPLEMENTATION_ROADMAP.md#phase-2-infrastructure-deployment).
