# Ecommerce Catalog Search

## Purpose
Provides product discovery and ACP-aligned catalog search responses.

## Responsibilities
- Resolve search queries into relevant product sets.
- Return inventory-aware and commerce-ready product context.
- Support intelligent search enrichment for downstream flows.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/ecommerce-catalog-search/src
uv sync
uv run uvicorn ecommerce_catalog_search.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
