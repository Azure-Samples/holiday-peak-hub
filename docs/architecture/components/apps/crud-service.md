# CRUD Service

Transactional REST API for carts, orders, payments, and ACP checkout sessions.

## Purpose

The CRUD service is a non-agent FastAPI microservice that owns transactional state and exposes seller-side APIs for checkout and order fulfillment.

## Responsibilities

- Cart management and item pricing snapshots
- Order creation and state tracking
- Payment processing integration (Stripe placeholder)
- ACP checkout session lifecycle endpoints
- Delegated payment token validation (ACP demo PSP)

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

- Cosmos DB containers: `cart`, `orders`, `checkout_sessions`, `payment_tokens`
- Provisioned via shared infrastructure Bicep module

## Events

- Publishes `OrderCreated` and `PaymentProcessed` via Event Hubs

## ACP Notes

- Checkout sessions follow ACP lifecycle semantics (create, update, complete, cancel).
- Delegate payment is modeled as a demo PSP for local ACP flows.
