# Product Management Assortment Optimization

## Purpose
Optimizes assortment decisions using product performance and relevance signals.

## Responsibilities
- Rank product candidates for assortment planning.
- Evaluate keep/drop trade-offs for target assortments.
- Return explainable assortment recommendations.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/product-management-assortment-optimization/src
uv sync
uv run uvicorn product_management_assortment_optimization.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
