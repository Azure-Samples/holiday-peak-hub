# Ecommerce Checkout Support

## Purpose
Evaluates checkout flows and surfaces guidance to reduce checkout failures.

## Responsibilities
- Detect checkout blockers across inventory, payment, and order context.
- Return actionable guidance for completion paths.
- Support real-time checkout assistance workflows.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/ecommerce-checkout-support/src
uv sync
uv run uvicorn ecommerce_checkout_support.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
