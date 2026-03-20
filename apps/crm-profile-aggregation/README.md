# CRM Profile Aggregation

## Purpose
Builds a unified customer profile from distributed CRM and interaction sources.

## Responsibilities
- Aggregate identity, contact, and engagement context.
- Resolve profile-level signals for downstream decisioning.
- Provide a consistent profile view for other services.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/crm-profile-aggregation/src
uv sync
uv run uvicorn crm_profile_aggregation.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
