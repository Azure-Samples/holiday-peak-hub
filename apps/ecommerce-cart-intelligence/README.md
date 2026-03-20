# Ecommerce Cart Intelligence

## Purpose
Analyzes carts to identify friction, abandonment risk, and conversion opportunities.

## Responsibilities
- Score cart-level conversion risk signals.
- Detect likely blockers in price, inventory, or composition.
- Recommend actions to improve checkout completion.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/ecommerce-cart-intelligence/src
uv sync
uv run uvicorn ecommerce_cart_intelligence.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
