# Search Enrichment Agent

## Purpose
Enriches search-oriented product data and processing outputs for discovery workflows.

## Responsibilities
- Process search enrichment tasks from asynchronous jobs.
- Improve product search representation quality.
- Provide enrichment outputs for downstream indexing and retrieval.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/search-enrichment-agent/src
uv sync
uv run uvicorn search_enrichment_agent.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
