# Inventory Health Check

## Purpose
Assesses inventory quality and health signals for operational monitoring.

## Responsibilities
- Evaluate inventory consistency and anomaly patterns.
- Surface health signals relevant to availability planning.
- Return remediation guidance for detected issues.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/inventory-health-check/src
uv sync
uv run uvicorn inventory_health_check.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
