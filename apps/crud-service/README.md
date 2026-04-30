# CRUD Service

> Last Updated: 2026-04-30

## Purpose

The transactional FastAPI microservice that owns all CRUD operations for Holiday Peak Hub. This is **not** an agent service — it is a pure REST API for deterministic, transactional data operations (orders, products, users, cart, payments, inventory, returns) and the sole publisher of domain events to Azure Event Hubs consumed by 26 agent services.

## Domain Bounded Context
- **Owner**: Platform team
- **Bounded Context**: Transactional platform (cross-domain data ownership)

## Responsibilities
- Own customer, catalog, cart, order, payment, inventory, returns, and operational CRUD workflows
- Expose REST API surfaces consumed by the Next.js frontend and agent services
- Publish domain events to 7 Event Hub topics consumed by asynchronous agent services
- Compose routes through bounded groups (`platform`, `commerce`, `staff`, `truth`)
- Provide ACP (Akeneo Connector Protocol) and UCP (Unified Commerce Protocol) endpoints
- Manage Truth Layer persistence (attributes, proposals, completeness, audit trail)
- Treat connector bootstrap as optional runtime wiring when connector domains are configured

## Endpoints

### Platform Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root status |
| GET | `/health` | Liveness probe |
| GET | `/ready` | Readiness probe (DB pool, event publisher) |
| POST | `/api/auth/register` | User registration |
| POST | `/api/auth/login` | User authentication |
| POST | `/api/auth/refresh` | Token refresh |
| * | `/api/users/*` | User CRUD |
| POST | `/webhooks/stripe` | Stripe webhook receiver |
| POST | `/webhooks/connectors/*` | Connector integration webhooks |

### Commerce Routes

| Method | Path | Description |
|--------|------|-------------|
| GET/POST/PUT/DELETE | `/api/products/*` | Product catalog CRUD |
| GET/POST | `/api/categories/*` | Product category management |
| GET/POST/PUT/DELETE | `/api/cart/*` | Shopping cart operations |
| GET/POST/PUT | `/api/orders/*` | Order lifecycle management |
| GET/POST | `/api/inventory/*` | Inventory levels and reservations |
| POST | `/api/checkout/*` | Checkout flow |
| POST | `/api/payments/*` | Payment processing |
| GET/POST/PUT | `/api/returns/*` | Customer returns lifecycle |
| GET/POST | `/api/reviews/*` | Product reviews |
| GET | `/api/brand-shopping/*` | Brand-filtered shopping |
| GET/POST | `/acp/products/*` | ACP product endpoints |
| POST | `/acp/checkout/*` | ACP checkout |
| POST | `/acp/payments/*` | ACP payment delegation |

### Truth Layer Routes

| Method | Path | Description |
|--------|------|-------------|
| GET/POST/PUT | `/api/truth-attributes/*` | Truth attribute management |
| GET/POST/PUT | `/api/proposed-attributes/*` | Enrichment proposal CRUD |
| GET | `/api/schemas-registry/*` | Schema registry for truth layer |
| GET | `/api/completeness/*` | Product completeness scoring |
| GET | `/api/audit-trail/*` | Enrichment and approval audit logs |
| GET | `/api/ucp-products/*` | UCP product views |

### Staff Routes

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/staff/analytics/*` | Staff analytics dashboards |
| GET/POST/PUT | `/api/staff/tickets/*` | Support ticket management |
| GET/POST/PUT | `/api/staff/returns/*` | Staff returns processing |
| GET/POST | `/api/staff/shipments/*` | Shipment management |

## Event Hub Publications

The CRUD service publishes domain events to these topics:

| Topic | Events Published | Triggered By |
|-------|-----------------|--------------|
| `order-events` | `OrderCreated`, `OrderUpdated`, `OrderCancelled` | Order lifecycle mutations |
| `payment-events` | `PaymentProcessed`, `PaymentFailed`, `RefundIssued` | Payment processing |
| `return-events` | `ReturnRequested`, `ReturnApproved`, `ReturnRejected`, `ReturnReceived`, `ReturnRestocked`, `ReturnRefunded` | Returns lifecycle |
| `inventory-events` | `InventoryReserved`, `InventoryReleased` | Reservation/release operations |
| `shipment-events` | `ShipmentCreated`, `ShipmentUpdated` | Shipment mutations |
| `product-events` | `ProductCreated`, `ProductUpdated`, `ProductDeleted` | Product catalog changes |
| `user-events` | `UserRegistered`, `UserUpdated` | User lifecycle |

All events are published with:
- Correlation ID propagation for distributed tracing
- Critical saga reliability profiles (retries + dead-letter)
- Self-healing kernel integration for publish failure detection

## Architecture Notes

- **No agent logic**: This is a pure microservice — no `BaseRetailAgent`, no model invocation
- **PostgreSQL**: Primary data store via `asyncpg` connection pool
- **Entra ID / password auth**: Dual authentication mode for PostgreSQL
- **Key Vault integration**: Secrets resolved at startup for DB and Redis passwords
- **Connector registry**: Optional enterprise connector bootstrap (PIM, DAM, CRM domains)
- **Connector sync consumer**: Listens for connector-originated data sync events
- **OpenTelemetry**: Optional Azure Monitor/Application Insights instrumentation

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_HOST` | Yes | PostgreSQL server hostname |
| `POSTGRES_DATABASE` | Yes | Database name |
| `POSTGRES_USER` | Yes | Database user |
| `POSTGRES_PASSWORD` | No | DB password (resolved from Key Vault if not set) |
| `POSTGRES_AUTH_MODE` | No | `password` or `entra` (default: `password`) |
| `EVENTHUB_NAMESPACE` | Yes | Event Hub namespace for domain event publishing |
| `REDIS_HOST` | No | Redis cache hostname |
| `REDIS_PASSWORD` | No | Redis password (resolved from Key Vault) |
| `KEY_VAULT_URI` | No | Azure Key Vault URI for secret resolution |
| `APP_INSIGHTS_CONNECTION_STRING` | No | Application Insights connection |
| `CONNECTOR_ENABLED_DOMAINS` | No | Comma-separated connector domains to bootstrap |
| `CONNECTOR_HEALTH_INTERVAL_SECONDS` | No | Health monitor interval (default: 60) |

## Local Development

```bash
cd apps/crud-service/src
uv sync
uv run uvicorn crud_service.main:app --reload --port 8000
```

## Test Coverage

```bash
python -m pytest apps/crud-service/tests
```

Test files located in `apps/crud-service/tests/`.
