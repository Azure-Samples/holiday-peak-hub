# CRUD Service

## Purpose
Provides the transactional FastAPI microservice for Holiday Peak Hub domain operations.

## Responsibilities
- Own customer, catalog, cart, order, payment, and operational CRUD workflows.
- Expose API surfaces used by frontend and service integrations.
- Publish domain events consumed by asynchronous agent services.
- Compose routes through bounded groups (`platform`, `commerce`, `staff`, `truth`) while preserving existing API paths.
- Treat connector bootstrap as optional runtime wiring when connector domains are configured.

## Key endpoints or interfaces
- Root and health endpoints: `GET /`, `GET /health`, `GET /ready`.
- Primary API namespaces under `/api/*` (auth, users, products, cart, orders, inventory, payments, staff, truth).
- ACP endpoints under `/acp/*` (products, checkout, and delegated payment paths).
- Webhook endpoints for Stripe and connector integrations.

## Run/Test commands
```bash
cd apps/crud-service/src
uv sync
uv run uvicorn crud_service.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses PostgreSQL settings, auth settings, and Event Hub publisher configuration from environment variables.
- Supports Entra/password database auth modes and optional Key Vault secret resolution.
- Includes optional telemetry and connector settings for operational integration.
