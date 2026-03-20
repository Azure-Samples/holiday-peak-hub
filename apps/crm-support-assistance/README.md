# CRM Support Assistance

## Purpose
Produces support-facing assistance with CRM context and next-best-action recommendations.

## Responsibilities
- Assemble customer context for support interactions.
- Identify sentiment and escalation risk cues.
- Suggest prioritized response actions.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/crm-support-assistance/src
uv sync
uv run uvicorn crm_support_assistance.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
