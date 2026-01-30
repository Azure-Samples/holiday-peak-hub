# CRUD Service

**Holiday Peak Hub CRUD API** - Transactional data operations and user-facing REST APIs.

## Purpose

This service handles all **non-agent CRUD operations**:
- User authentication and profile management
- Product catalog CRUD (fallback when agents unavailable)
- Order management and checkout flow
- Cart operations
- Payment processing (Stripe integration)
- Staff analytics and customer support
- Admin operations

## Architecture

**NOT an Agent Service** - This is a pure FastAPI microservice with:
- ❌ No agent logic (no `BaseRetailAgent`)
- ❌ No memory tiers (stateless, uses Cosmos DB directly)
- ❌ No MCP exposition (REST-only for frontend consumption)
- ✅ Event publisher (publishes domain events for agents)
- ✅ Optional agent calls (can invoke agent MCP tools with fallback)
- ✅ Separate deployment (dedicated node pool in AKS)

## Deployment Strategy

**Microservice Pattern**:
- Deployed to AKS `crud` node pool (separate from agents)
- Scales based on HTTP request rate (HPA)
- Stateless design (horizontally scalable)
- Event-driven integration with agents (async via Event Hubs)

## Tech Stack

- **FastAPI** 0.115+ - REST API framework
- **Pydantic** 2.10+ - Data validation and settings
- **Azure Cosmos DB** - NoSQL database (10 containers)
- **Azure Event Hubs** - Event publishing
- **Azure Key Vault** - Secrets management (Managed Identity)
- **Stripe** - Payment processing
- **Microsoft Entra ID** - Authentication (OAuth2)

## Project Structure

```
crud-service/
├── src/
│   ├── crud_service/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI application
│   │   ├── config/
│   │   │   ├── __init__.py
│   │   │   └── settings.py           # Environment config (Pydantic)
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── entra.py              # Microsoft Entra ID OAuth
│   │   │   ├── middleware.py         # JWT validation
│   │   │   ├── rbac.py               # Role-based access control
│   │   │   └── dependencies.py       # FastAPI auth dependencies
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── base.py               # Base Cosmos DB repository
│   │   │   ├── user.py
│   │   │   ├── product.py
│   │   │   ├── order.py
│   │   │   ├── cart.py
│   │   │   ├── review.py
│   │   │   ├── address.py
│   │   │   ├── payment_method.py
│   │   │   ├── ticket.py
│   │   │   └── shipment.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── user.py               # Business logic
│   │   │   ├── product.py
│   │   │   ├── order.py
│   │   │   ├── cart.py
│   │   │   ├── checkout.py
│   │   │   ├── analytics.py
│   │   │   └── notification.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── health.py             # Health checks
│   │   │   ├── auth.py               # Authentication endpoints
│   │   │   ├── users.py              # User management
│   │   │   ├── products.py           # Product CRUD
│   │   │   ├── categories.py         # Category endpoints
│   │   │   ├── cart.py               # Cart management
│   │   │   ├── orders.py             # Order management
│   │   │   ├── checkout.py           # Checkout flow
│   │   │   ├── payments.py           # Payment processing
│   │   │   ├── reviews.py            # Review endpoints
│   │   │   └── staff/
│   │   │       ├── __init__.py
│   │   │       ├── analytics.py      # Staff analytics
│   │   │       ├── tickets.py        # Support tickets
│   │   │       ├── returns.py        # Return management
│   │   │       └── shipments.py      # Logistics tracking
│   │   └── integrations/
│   │       ├── __init__.py
│   │       ├── stripe.py             # Stripe payment client
│   │       ├── agent_client.py       # Optional agent MCP calls
│   │       ├── event_publisher.py    # Event Hubs publisher
│   │       └── carrier_apis.py       # FedEx, UPS, USPS
│   ├── pyproject.toml
│   └── Dockerfile
└── tests/
    ├── __init__.py
    ├── conftest.py                   # Pytest fixtures
    ├── unit/
    │   ├── test_repositories.py
    │   ├── test_services.py
    │   └── test_auth.py
    ├── integration/
    │   ├── test_api_users.py
    │   ├── test_api_products.py
    │   ├── test_api_orders.py
    │   └── test_api_checkout.py
    └── e2e/
        └── test_checkout_flow.py
```

## Environment Variables

```bash
# Azure Resources (use Managed Identity, no connection strings needed)
COSMOS_ACCOUNT_URI=https://holidaypeakhub-dev-cosmos.documents.azure.com:443/
COSMOS_DATABASE=holiday-peak-db
EVENT_HUB_NAMESPACE=holidaypeakhub-dev-eventhub.servicebus.windows.net
KEY_VAULT_URI=https://holidaypeakhub-dev-kv.vault.azure.net/
REDIS_HOST=holidaypeakhub-dev-redis.redis.cache.windows.net
REDIS_PORT=6380
REDIS_DB=0

# Authentication (Microsoft Entra ID)
ENTRA_TENANT_ID=<from-key-vault>
ENTRA_CLIENT_ID=<from-key-vault>
ENTRA_CLIENT_SECRET=<from-key-vault>
ENTRA_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0

# Application
SERVICE_NAME=crud-service
LOG_LEVEL=INFO
ENVIRONMENT=dev

# Feature Flags (optional)
ENABLE_AGENT_FALLBACK=true
AGENT_TIMEOUT_SECONDS=3
```

## Development

### Prerequisites

- Python 3.13+
- Azure CLI (authenticated)
- Docker (for local testing)
- uv (package manager)

### Local Setup

```bash
# Navigate to service
cd apps/crud-service/src

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .[dev]

# Run locally
uvicorn crud_service.main:app --reload --port 8001

# Run tests
pytest
```

### Local Development with Docker

```bash
# Build
docker build -t crud-service:dev --target dev .

# Run
docker run -p 8001:8000 \
  -e COSMOS_ACCOUNT_URI=$COSMOS_ACCOUNT_URI \
  -e COSMOS_DATABASE=holiday-peak-db \
  crud-service:dev
```

## API Endpoints

### Anonymous (Public)
- `GET /health` - Health check
- `GET /api/auth/login` - Redirect to Entra ID login
- `GET /api/auth/callback` - OAuth callback
- `POST /api/auth/guest` - Create guest session
- `GET /api/products` - List products (paginated)
- `GET /api/products/{id}` - Get product details
- `GET /api/categories` - List categories
- `GET /api/orders/{id}?email={email}` - Order tracking (email verification)

### Customer (Authenticated)
- `GET /api/users/me` - Get current user
- `PUT /api/users/me` - Update profile
- `GET /api/cart` - Get cart
- `POST /api/cart/items` - Add to cart
- `POST /api/orders` - Create order
- `GET /api/users/me/orders` - Order history
- `POST /api/payments/create-intent` - Create payment intent

### Staff (Role: staff)
- `GET /api/staff/analytics/sales` - Sales analytics
- `GET /api/staff/tickets` - Customer support tickets
- `PUT /api/staff/tickets/{id}/status` - Update ticket
- `GET /api/staff/shipments` - Shipment tracking
- `POST /api/staff/returns` - Process return request

### Admin (Role: admin)
- `GET /api/admin/health` - System health
- `GET /api/admin/users` - User management
- `PUT /api/admin/users/{id}/role` - Assign role
- `GET /api/admin/config` - System configuration

## Event-Driven Integration

### Events Published (to Event Hubs)

**Order Events** → `order-events` topic:
```json
{
  "type": "OrderCreated",
  "order_id": "order-uuid-123",
  "user_id": "user-uuid-456",
  "items": [...],
  "total": 99.99,
  "timestamp": "2026-01-29T12:34:56Z"
}
```

**Inventory Events** → `inventory-events` topic:
```json
{
  "type": "StockUpdated",
  "product_id": "product-uuid-789",
  "quantity_change": -5,
  "timestamp": "2026-01-29T12:34:56Z"
}
```

**Payment Events** → `payment-events` topic:
```json
{
  "type": "PaymentProcessed",
  "order_id": "order-uuid-123",
  "amount": 99.99,
  "status": "succeeded",
  "timestamp": "2026-01-29T12:34:56Z"
}
```

### Agent Invocation (Optional, Sync)

When agent intelligence is needed for user-facing features:

```python
# Example: Smart product search with fallback
try:
    result = await agent_client.call_mcp_tool(
        service="ecommerce-catalog-search",
        tool="search_products",
        params={"query": "red dress", "filters": {...}},
        timeout=3.0
    )
except (TimeoutError, AgentUnavailableError):
    # Fallback to basic search
    result = await product_repository.search("red dress", {...})
```

## Deployment

### AKS Deployment

```bash
# Build and push image
docker build -t holidaypeakhub.azurecr.io/crud-service:1.0.0 .
docker push holidaypeakhub.azurecr.io/crud-service:1.0.0

# Deploy to AKS
kubectl apply -f .kubernetes/crud-service/

# Verify
kubectl get pods -l app=crud-service -n default
kubectl logs -l app=crud-service -n default --tail=100
```

### Kubernetes Resources

- **Deployment**: 3 replicas (prod), 1 replica (dev)
- **Service**: ClusterIP on port 8001
- **Ingress**: `/api/*` routes through APIM
- **HPA**: Auto-scale 1-10 replicas based on CPU/memory
- **Node Affinity**: Runs on `crud` node pool

### Health Checks

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
```

## Testing

### Unit Tests
```bash
pytest tests/unit/ -v
```

### Integration Tests (requires Cosmos DB)
```bash
pytest tests/integration/ -v
```

### E2E Tests
```bash
pytest tests/e2e/ -v
```

### Coverage
```bash
pytest --cov=crud_service --cov-report=html
```

## Monitoring

### Application Insights
- Request telemetry (all endpoints)
- Dependency telemetry (Cosmos DB, Event Hubs, agents)
- Custom events (order created, payment processed)
- Custom metrics (cart abandonment rate, checkout success rate)

### Metrics
- `crud_api_requests_total` - Total API requests
- `crud_api_response_time_seconds` - Response time histogram
- `crud_order_created_total` - Orders created counter
- `crud_payment_success_rate` - Payment success percentage

### Logs
- Structured JSON logging (use `structlog`)
- Correlation IDs for distributed tracing
- Log to stdout (captured by AKS)

## Security

- ✅ **Managed Identity** - No passwords for Azure services
- ✅ **Key Vault** - Secrets stored securely
- ✅ **Entra ID** - OAuth2 authentication
- ✅ **RBAC** - Role-based access control (4 roles)
- ✅ **TLS** - All connections use TLS 1.2+
- ✅ **Input Validation** - Pydantic models validate all inputs
- ✅ **SQL Injection** - Not applicable (NoSQL with parameterized queries)
- ✅ **Rate Limiting** - Configured in APIM

## Related Documentation

- [Implementation Roadmap](../../docs/IMPLEMENTATION_ROADMAP.md)
- [CRUD Service Implementation Guide](../../docs/architecture/crud-service-implementation.md)
- [Shared Infrastructure](../../.infra/modules/shared-infrastructure/README.md)
- [ADR-007: SAGA Choreography](../../docs/architecture/adrs/adr-007-saga-choreography.md)
- [ADR-009: AKS Deployment](../../docs/architecture/adrs/adr-009-aks-deployment.md)
- [ADR-010: REST + MCP Exposition](../../docs/architecture/adrs/adr-010-rest-and-mcp-exposition.md)
