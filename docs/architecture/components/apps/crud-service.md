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
- **Brand-shopping contract surface** for UI personalization orchestration

## Key Endpoints

### ACP Checkout

- `POST /acp/checkout/sessions` - Create checkout session
- `GET /acp/checkout/sessions/{id}` - Retrieve session
- `PATCH /acp/checkout/sessions/{id}` - Update items, address, or fulfillment
- `POST /acp/checkout/sessions/{id}/complete` - Complete with delegated token
- `DELETE /acp/checkout/sessions/{id}` - Cancel session

### ACP Delegate Payment

- `POST /acp/payments/delegate` - Create delegated payment token with allowance

### Brand Shopping Personalization (Issue #215)

- `GET /api/catalog/products/{sku}` - Canonical product contract for personalization context
- `GET /api/customers/{customer_id}/profile` - Customer + CRM/personalization profile contract (owner or `staff|admin`)
- `POST /api/pricing/offers` - Deterministic offer computation contract
- `POST /api/recommendations/rank` - Ranked recommendation scoring contract
- `POST /api/recommendations/compose` - Final recommendation composition contract

### Inventory & Reservation Lifecycle (Issue #216)

- `GET /api/inventory/{sku}` - Retrieve inventory snapshot
- `PATCH /api/inventory/{sku}` - Update quantity fields (`quantity_on_hand`, `reserved_quantity`) (`staff|admin`)
- `PATCH /api/inventory/{sku}/thresholds` - Update reorder/safety thresholds (`staff|admin`)
- `GET /api/inventory/health` - Inventory health summary (healthy/low_stock/out_of_stock)
- `POST /api/inventory/reservations` - Create reservation hold (`created`)
- `GET /api/inventory/reservations/{reservation_id}` - Retrieve reservation (owner or `staff|admin`)
- `POST /api/inventory/reservations/{reservation_id}/confirm` - Confirm hold (owner or `staff|admin`, idempotent when already confirmed)
- `POST /api/inventory/reservations/{reservation_id}/release` - Release hold and decrement reserved quantity (owner or `staff|admin`, idempotent when already released)

### Reservation State Machine

- Allowed transitions: `created -> confirmed`, `created -> released`
- Terminal states: `confirmed`, `released`
- Invalid transitions return `409 Conflict`

### Checkout Integration

- UI creates holds before order/payment setup.
- UI confirms holds only after successful `POST /api/payments/confirm-intent`.
- UI issues compensating release when setup fails or checkout is abandoned before payment confirmation.

### Personalization Orchestration Ownership

- **CRUD**: contract ownership, validation, schema stability.
- **UI**: flow orchestration (product/profile → offers → rank → compose).

### Contract Versioning Policy

- Current brand-shopping contracts are treated as `v1` under `/api`.
- Additive response fields are allowed without path changes.
- Breaking request/response or route changes require a new parallel versioned path (for example `/api/v2/...`) before deprecating `v1`.

### Returns & Refund Lifecycle Contracts (Issue #217)

#### Lifecycle State Machine

- States: `requested`, `approved`, `rejected`, `received`, `restocked`, `refunded`
- Allowed transitions: `requested->approved|rejected`, `approved->received`, `received->restocked`, `restocked->refunded`
- Terminal states: `rejected`, `refunded`
- Invalid transitions return `409 Conflict`
- Repeating the current target state returns `200` with `idempotent=true`

#### Customer API Contracts

- `POST /api/returns` creates a return in `requested` (`201`)
- `GET /api/returns` lists customer-owned returns
- `GET /api/returns/{return_id}` returns canonical lifecycle timeline
- `GET /api/returns/{return_id}/refund` returns refund progression (`issued`) or `404` when refund record does not exist

#### Staff API Contracts

- `GET /api/staff/returns/`, `GET /api/staff/returns/{return_id}`
- `POST /api/staff/returns/{return_id}/approve`
- `PATCH /api/staff/returns/{return_id}/approve` (legacy compatibility)
- `POST /api/staff/returns/{return_id}/reject`
- `POST /api/staff/returns/{return_id}/receive`
- `POST /api/staff/returns/{return_id}/restock`
- `POST /api/staff/returns/{return_id}/refund`
- `GET /api/staff/returns/{return_id}/refund`

Staff returns routes accept `staff|admin` roles.

#### Event Contracts

- Lifecycle topic: `return-events`
	- `ReturnRequested`, `ReturnApproved`, `ReturnRejected`, `ReturnReceived`, `ReturnRestocked`, `ReturnRefunded`
- Refund topic: `payment-events`
	- `RefundIssued`

Event payload data includes: `return_id`, `order_id`, `user_id`, `status`, `occurred_at`, `actor_id`, `actor_roles`, `sla`, `timestamp`.
The `sla` object carries lifecycle timestamps (`requested_at`, `approved_at`, `rejected_at`, `received_at`, `restocked_at`, `refunded_at`, `last_transition_at`).

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
