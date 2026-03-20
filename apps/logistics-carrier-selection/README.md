# Logistics Carrier Selection

## Purpose
Recommends carrier options based on shipment requirements and constraints.

## Responsibilities
- Evaluate candidate carriers for a shipment.
- Compare trade-offs such as service level and risk.
- Return the recommended carrier decision context.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/logistics-carrier-selection/src
uv sync
uv run uvicorn logistics_carrier_selection.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
