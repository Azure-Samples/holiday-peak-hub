# CRUD Service

Transactional REST API for carts, orders, payments, and ACP checkout sessions.

## Purpose

The CRUD service is a non-agent FastAPI microservice that owns transactional state and exposes seller-side APIs for checkout and order fulfillment. It routes agent calls through Azure API Management (APIM) with circuit breaker and retry for resilient integration.

## Responsibilities

- Cart management and item pricing snapshots
- Order creation and state tracking
- Payment processing integration (Stripe placeholder)
- ACP checkout session lifecycle endpoints
- Delegated payment token validation (ACP demo PSP)
- **APIM-routed agent invocation** (12 agent methods with circuit breaker + retry)
- **JWKS-based JWT authentication** with Entra ID

## Key Endpoints

### ACP Checkout

- `POST /acp/checkout/sessions` - Create checkout session
- `GET /acp/checkout/sessions/{id}` - Retrieve session
- `PATCH /acp/checkout/sessions/{id}` - Update items, address, or fulfillment
- `POST /acp/checkout/sessions/{id}/complete` - Complete with delegated token
- `DELETE /acp/checkout/sessions/{id}` - Cancel session

### ACP Delegate Payment

- `POST /acp/payments/delegate` - Create delegated payment token with allowance

## Data Stores

- **PostgreSQL (asyncpg)**: JSONB tables — `cart`, `orders`, `checkout_sessions`, `payment_tokens`, `users`, `products`, `reviews`, `tickets`, `shipments`, `audit_logs`
- Connection pooling via shared `asyncpg.Pool` (class-level singleton)
- GIN + B-tree indexes on all JSONB tables
- Provisioned via Azure PostgreSQL Flexible Server

## Agent Integration

- 12 agent methods routed through **APIM gateway** (`APIM_BASE_URL`)
- `circuitbreaker` (failure_threshold=5, recovery_timeout=60s)
- `tenacity` retry with exponential backoff (3 attempts)
- Graceful degradation: returns `None` if agent unavailable

## Events

- Publishes `OrderCreated` and `PaymentProcessed` via Event Hubs

## ACP Notes

- Checkout sessions follow ACP lifecycle semantics (create, update, complete, cancel).
- Delegate payment is modeled as a demo PSP for local ACP flows.
