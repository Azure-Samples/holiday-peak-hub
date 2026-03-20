# Inventory Alerts Triggers

## Purpose
Detects inventory alert conditions and emits actionable trigger guidance.

## Responsibilities
- Identify low-stock and pressure scenarios.
- Evaluate urgency and likely operational impact.
- Return recommended trigger actions for inventory operations.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/inventory-alerts-triggers/src
uv sync
uv run uvicorn inventory_alerts_triggers.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
