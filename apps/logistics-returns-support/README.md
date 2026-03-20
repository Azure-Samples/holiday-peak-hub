# Logistics Returns Support

## Purpose
Supports return-related logistics decisions and operational guidance.

## Responsibilities
- Assess return flow context and constraints.
- Provide recommendations for return handling steps.
- Surface issues that can delay or block return processing.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/logistics-returns-support/src
uv sync
uv run uvicorn logistics_returns_support.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
