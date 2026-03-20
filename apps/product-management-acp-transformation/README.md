# Product Management ACP Transformation

## Purpose
Transforms product payloads into ACP-aligned structures for downstream consumption.

## Responsibilities
- Map source product fields to ACP-oriented output.
- Detect required-field gaps during transformation.
- Return transformation results and validation context.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/product-management-acp-transformation/src
uv sync
uv run uvicorn product_management_acp_transformation.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
