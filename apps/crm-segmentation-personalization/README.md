# CRM Segmentation Personalization

## Purpose
Segments customers and proposes personalization actions based on customer context.

## Responsibilities
- Classify users into actionable engagement segments.
- Generate channel and content personalization guidance.
- Provide explainable segment-level recommendations.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/crm-segmentation-personalization/src
uv sync
uv run uvicorn crm_segmentation_personalization.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
