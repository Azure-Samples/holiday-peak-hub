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
- ❌ No memory tiers (stateless, uses PostgreSQL directly)
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
- **Azure Database for PostgreSQL** - Transactional relational database
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
│   │   │   ├── base.py               # Base PostgreSQL repository (JSONB-backed)
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
# Azure Resources
POSTGRES_HOST=holidaypeakhub-dev-postgres.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_DATABASE=holiday_peak_crud
POSTGRES_USER=crud_admin
POSTGRES_PASSWORD=
POSTGRES_PASSWORD_SECRET_NAME=postgres-admin-password
POSTGRES_SSL=true
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

### Team Deployment Template (recommended)

Use the team-scoped template [apps/crud-service/.env.deploy.sample](apps/crud-service/.env.deploy.sample).

Each team/environment must have its own `.env` values (do not reuse from another deployment).

**When to provision/update these values**:

1. Right after `azd provision` for a new team environment.
2. Any time infrastructure is reprovisioned or environment name changes.
3. Before deploying `crud-service` if APIM name/URL changed.

**How to populate values from azd env**:

```bash
# Example: team-a-dev
azd env get-values -e <env-name>
```

Or generate CRUD `.env` automatically from that azd environment:

```powershell
# Windows
pwsh ./.infra/azd/hooks/generate-crud-env.ps1 -EnvironmentName <env-name> -Force
```

```bash
# Linux/macOS
FORCE=true ./.infra/azd/hooks/generate-crud-env.sh <env-name>
```

Set `AGENT_APIM_BASE_URL` from that environment:

```text
https://<apimName>.azure-api.net
```

You can also verify quickly with:

```bash
az apim show -g <resourceGroup> -n <apimName> --query gatewayUrl -o tsv
```

`AGENT_APIM_BASE_URL` is now the default route for CRUD synchronous agent calls.
Per-agent URL variables remain optional overrides for troubleshooting.

## Development

The service resolves `POSTGRES_PASSWORD` from Key Vault at startup when the env var is empty, using managed identity and `POSTGRES_PASSWORD_SECRET_NAME`.

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
  -e POSTGRES_HOST=$POSTGRES_HOST \
  -e POSTGRES_DATABASE=holiday_peak_crud \
  -e POSTGRES_USER=$POSTGRES_USER \
  -e POSTGRES_PASSWORD=$POSTGRES_PASSWORD \
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
- `POST /api/returns` - Create return request (requested state)
- `GET /api/returns` - List own returns
- `GET /api/returns/{return_id}` - Get own return lifecycle timeline
- `GET /api/returns/{return_id}/refund` - Get refund progression

### Staff (Role: staff)
- `GET /api/staff/analytics/sales` - Sales analytics
- `GET /api/staff/tickets` - Customer support tickets
- `PUT /api/staff/tickets/{id}/status` - Update ticket
- `GET /api/staff/shipments` - Shipment tracking
- `GET /api/staff/returns` - List returns with lifecycle state
- `POST /api/staff/returns/{id}/approve` - requested → approved
- `POST /api/staff/returns/{id}/reject` - requested → rejected
- `POST /api/staff/returns/{id}/receive` - approved → received
- `POST /api/staff/returns/{id}/restock` - received → restocked
- `POST /api/staff/returns/{id}/refund` - restocked → refunded
- `GET /api/staff/returns/{id}/refund` - Get refund progression

### Admin (Role: admin)
- `GET /api/admin/health` - System health
- `GET /api/admin/users` - User management
- `PUT /api/admin/users/{id}/role` - Assign role
- `GET /api/admin/config` - System configuration

## Event-Driven Integration

### Events Published (to Event Hubs)

The CRUD service publishes domain events to Azure Event Hubs using **Managed Identity** (no connection strings). Agents subscribe to these events for asynchronous processing.

**Event Publisher Implementation:**
```python
# apps/crud-service/src/crud_service/integrations/event_publisher.py
class EventPublisher:
    """Publishes domain events to Azure Event Hubs."""
    
    async def publish(self, topic: str, event_type: str, data: dict[str, Any]):
        """Publish event with automatic retry and error handling."""
        event_payload = {
            "event_type": event_type,
            "data": data,
            "timestamp": data.get("timestamp")
        }
        await producer.send_batch([EventData(json.dumps(event_payload))])
```

**Order Events** → `order-events` topic:
```json
{
  "event_type": "OrderCreated",
  "data": {
    "order_id": "order-uuid-123",
    "user_id": "user-uuid-456",
    "items": [
      {"sku": "SKU-001", "quantity": 2, "price": 49.99}
    ],
    "total": 99.99,
    "status": "pending"
  },
  "timestamp": "2026-02-03T12:34:56Z"
}
```

**Subscribers**: `ecommerce-checkout-support`, `ecommerce-order-status`, `inventory-reservation-validation`, `logistics-eta-computation`, `crm-profile-aggregation`, `crm-support-assistance`, `crm-segmentation-personalization`

**Payment Events** → `payment-events` topic:
```json
{
  "event_type": "PaymentProcessed",
  "data": {
    "order_id": "order-uuid-123",
    "payment_id": "payment-uuid-456",
    "amount": 99.99,
    "currency": "USD",
    "status": "succeeded",
    "payment_method": "card_visa_4242"
  },
  "timestamp": "2026-02-03T12:35:10Z"
}
```

**Subscribers**: `ecommerce-checkout-support`, `crm-campaign-intelligence`

**Return Events** → `return-events` topic:
- `ReturnRequested`
- `ReturnApproved`
- `ReturnRejected`
- `ReturnReceived`
- `ReturnRestocked`
- `ReturnRefunded`

**Refund Events** → `payment-events` topic:
- `RefundIssued`

**Inventory Events** → `inventory-events` topic:
```json
{
  "event_type": "InventoryReserved",
  "data": {
    "product_id": "product-uuid-789",
    "sku": "SKU-001",
    "quantity_reserved": 5,
    "order_id": "order-uuid-123",
    "warehouse_id": "warehouse-001"
  },
  "timestamp": "2026-02-03T12:34:57Z"
}
```

**Subscribers**: `inventory-health-check`, `inventory-jit-replenishment`, `inventory-alerts-triggers`

**User Events** → `user-events` topic:
```json
{
  "event_type": "UserRegistered",
  "data": {
    "user_id": "user-uuid-456",
    "email": "user@example.com",
    "first_name": "Jane",
    "last_name": "Smith",
    "marketing_opt_in": true
  },
  "timestamp": "2026-02-03T12:30:00Z"
}
```

**Subscribers**: `crm-profile-aggregation`, `crm-campaign-intelligence`

**Shipment Events** → `shipment-events` topic:
```json
{
  "event_type": "ShipmentCreated",
  "data": {
    "shipment_id": "shipment-uuid-111",
    "order_id": "order-uuid-123",
    "carrier": "FedEx",
    "tracking_number": "1234567890",
    "estimated_delivery": "2026-02-05T18:00:00Z"
  },
  "timestamp": "2026-02-03T14:00:00Z"
}
```

**Subscribers**: `logistics-eta-computation`, `logistics-route-issue-detection`

### Agent Invocation (Synchronous with Circuit Breaker)

When agent intelligence is needed for real-time user-facing features, CRUD calls agent REST endpoints with **resilience patterns**:

**Circuit Breaker Configuration:**
```python
# apps/crud-service/src/crud_service/config/settings.py
agent_timeout_seconds: float = 0.5           # 500ms timeout
agent_retry_attempts: int = 2                # Max 2 retries
agent_circuit_failure_threshold: int = 5     # Open after 5 failures
agent_circuit_recovery_seconds: int = 60     # 1-minute recovery window
enable_agent_fallback: bool = True           # Graceful degradation
```

**Agent Client Implementation:**
```python
# apps/crud-service/src/crud_service/integrations/agent_client.py
from circuitbreaker import circuit
from tenacity import retry, stop_after_attempt, wait_exponential

class AgentClient:
  def _resolve_agent_url(self, explicit_url: str | None, service_name: str) -> str | None:
    if explicit_url:
      return explicit_url.rstrip("/")
    if settings.agent_apim_base_url:
      return f"{settings.agent_apim_base_url.rstrip('/')}/agents/{service_name}"
    return None

    @circuit(failure_threshold=5, recovery_timeout=60)
    @retry(stop=stop_after_attempt(2), wait=wait_exponential(0.5, 0.5, 2))
    async def _call_endpoint(self, agent_url: str, endpoint: str, data: dict):
        """Call agent with circuit breaker and retry logic."""
        async with httpx.AsyncClient(timeout=0.5) as client:
            response = await client.post(f"{agent_url}{endpoint}", json=data)
            response.raise_for_status()
            return response.json()
    
    async def call_endpoint(self, agent_url, endpoint, data, fallback_value=None):
        """Invoke agent with automatic fallback on failure."""
        try:
            return await self._call_endpoint(agent_url, endpoint, data)
        except (httpx.TimeoutException, httpx.HTTPError, CircuitBreakerError):
            logger.warning("Agent call failed; using fallback")
            if self.enable_fallback:
                return fallback_value
            raise
```

      **Routing Configuration (recommended):**

      ```dotenv
      AGENT_APIM_BASE_URL=https://<apimName>.azure-api.net

      # Optional per-agent overrides (only when needed)
      PRODUCT_ENRICHMENT_AGENT_URL=
      CART_INTELLIGENCE_AGENT_URL=
      INVENTORY_HEALTH_AGENT_URL=
      CHECKOUT_SUPPORT_AGENT_URL=
      ```

      With this setup, CRUD calls agents through APIM routes such as:

      - `/agents/ecommerce-product-detail-enrichment/invoke`
      - `/agents/ecommerce-cart-intelligence/invoke`
      - `/agents/ecommerce-checkout-support/invoke`
      - `/agents/inventory-health-check/invoke`

**Example: Product Enrichment (with fallback)**
```python
# apps/crud-service/src/crud_service/routes/products.py
@router.get("/products/{product_id}")
async def get_product(product_id: str, agent_client: AgentClient):
    # Get base product from PostgreSQL
    product = await product_repository.get(product_id)
    
    # Try to enrich with agent intelligence
    enrichment = await agent_client.get_product_enrichment(
        product.sku,
        fallback_value=None  # Graceful degradation
    )
    
    if enrichment:
        product.description = enrichment.get("description", product.description)
        product.rating = enrichment.get("rating")
        product.review_count = enrichment.get("review_count")
        product.related_products = enrichment.get("related", [])
    
    return product
```

**Example: Cart Recommendations (with fallback)**
```python
# apps/crud-service/src/crud_service/routes/cart.py
@router.get("/cart/recommendations")
async def get_cart_recommendations(user_id: str, agent_client: AgentClient):
    cart = await cart_repository.get(user_id)
    
    # Try to get AI recommendations
    recommendations = await agent_client.get_user_recommendations(
        user_id=user_id,
        items=cart.items,
        fallback_value={"recommended_products": []}  # Empty list on failure
    )
    
    return recommendations
```

**Example: Dynamic Pricing (with fallback to base price)**
```python
# apps/crud-service/src/crud_service/routes/checkout.py
@router.post("/checkout/validate")
async def validate_checkout(user_id: str, agent_client: AgentClient):
    cart = await cart_repository.get(user_id)
    
    for item in cart.items:
        # Try to get dynamic pricing
        dynamic_price = await agent_client.calculate_dynamic_pricing(
            item.sku,
            fallback_value=None
        )
        
        if dynamic_price:
            item.price = dynamic_price  # Use AI-optimized price
        # else: use base price from cart (already set)
    
    return {"cart": cart, "total": sum(i.price * i.quantity for i in cart.items)}
```

**Resilience Behavior:**

| Scenario | Behavior | User Impact |
|----------|----------|-------------|
| Agent responds < 500ms | Use agent result | ✅ Enhanced experience |
| Agent timeout (> 500ms) | Use fallback | ⚠️ Degraded experience (still works) |
| Agent returns error | Use fallback | ⚠️ Degraded experience (still works) |
| Circuit open (5+ failures) | Skip agent call, use fallback | ⚠️ Degraded experience (still works) |
| Fallback disabled | Raise exception | ❌ Feature unavailable (fail fast) |

**Benefits:**
- ✅ **Prevents cascading failures**: Circuit breaker stops calls to unhealthy agents
- ✅ **Fast timeouts**: 500ms limit prevents slow agent calls from blocking CRUD operations
- ✅ **Graceful degradation**: Fallback to basic logic when agents unavailable
- ✅ **Automatic recovery**: Circuit closes after 60s, allowing agents to recover
- ✅ **Retry on transients**: Exponential backoff handles temporary network issues

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

### Integration Tests (requires PostgreSQL)
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
- Dependency telemetry (PostgreSQL, Event Hubs, agents)
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
- ✅ **SQL Injection** - Mitigated via parameterized queries in the repository layer
- ✅ **Rate Limiting** - Configured in APIM

## Related Documentation

- [Implementation Roadmap](../../docs/IMPLEMENTATION_ROADMAP.md)
- [CRUD Service Implementation Guide](../../docs/architecture/crud-service-implementation.md)
- [Shared Infrastructure](../../.infra/modules/shared-infrastructure/README.md)
- [ADR-007: SAGA Choreography](../../docs/architecture/adrs/adr-007-saga-choreography.md)
- [ADR-009: AKS Deployment](../../docs/architecture/adrs/adr-009-aks-deployment.md)
- [ADR-010: REST + MCP Exposition](../../docs/architecture/adrs/adr-010-rest-and-mcp-exposition.md)
