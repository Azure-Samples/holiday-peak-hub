# Ecommerce Order Status

## Purpose
Provides intelligent order and shipment status interpretation for customer-facing workflows.

## Responsibilities
- Consolidate status timeline signals for orders.
- Identify delay and exception indicators.
- Return concise status guidance and next actions.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/ecommerce-order-status/src
uv sync
uv run uvicorn ecommerce_order_status.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
