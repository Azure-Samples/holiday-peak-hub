# Product Management Consistency Validation

## Purpose
Validates product consistency and completeness against expected product schemas.

## Responsibilities
- Assess product records for schema consistency.
- Surface missing or conflicting attribute data.
- Return validation results used by enrichment and review flows.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/product-management-consistency-validation/src
uv sync
uv run uvicorn product_management_consistency_validation.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
