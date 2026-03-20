# Product Management Normalization Classification

## Purpose
Normalizes and classifies product attributes into canonical representations.

## Responsibilities
- Normalize product values into expected format and taxonomy.
- Classify product attributes for downstream indexing and logic.
- Return normalization and classification outcomes.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/product-management-normalization-classification/src
uv sync
uv run uvicorn product_management_normalization_classification.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
