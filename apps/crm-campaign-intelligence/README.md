# CRM Campaign Intelligence

## Purpose
Provides campaign intelligence by combining CRM context with campaign and funnel signals.

## Responsibilities
- Analyze campaign performance patterns.
- Surface likely drop-off and conversion risk points.
- Return recommendations to improve campaign outcomes.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/crm-campaign-intelligence/src
uv sync
uv run uvicorn crm_campaign_intelligence.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
