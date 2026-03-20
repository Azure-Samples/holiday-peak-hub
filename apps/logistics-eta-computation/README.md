# Logistics ETA Computation

## Purpose
Computes ETA projections and delay-risk indicators for logistics workflows.

## Responsibilities
- Estimate shipment arrival windows.
- Detect signals that reduce ETA confidence.
- Return ETA updates with concise risk context.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/logistics-eta-computation/src
uv sync
uv run uvicorn logistics_eta_computation.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
