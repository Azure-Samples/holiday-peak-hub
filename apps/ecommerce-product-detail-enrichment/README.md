# Ecommerce Product Detail Enrichment

## Purpose
Enriches product detail context to improve product understanding and conversion readiness.

## Responsibilities
- Aggregate detail-page context from product and related signals.
- Identify missing or weak product detail attributes.
- Return enrichment guidance for product presentation quality.

## Key endpoints or interfaces
- `POST /invoke` for synchronous service requests.
- MCP interfaces under `/mcp/*` for agent-to-agent usage.
- Event Hub subscription for asynchronous processing.

## Run/Test commands
```bash
cd apps/ecommerce-product-detail-enrichment/src
uv sync
uv run uvicorn ecommerce_product_detail_enrichment.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
