# search-enrichment-agent

Search enrichment producer service for Issue #347.

## Purpose

- Consumes approved truth data and generates search-ready enrichment fields.
- Handles event-driven jobs from `search-enrichment-jobs`.
- Exposes MCP tools:
  - `/search-enrichment/enrich`
  - `/search-enrichment/status`
  - `/ai-search-indexing/trigger_indexer_run`
  - `/ai-search-indexing/get_indexer_status`
  - `/ai-search-indexing/reset_indexer`
  - `/ai-search-indexing/index_documents`
  - `/ai-search-indexing/get_index_stats`
- Upserts `SearchEnrichedProduct` records into logical container `search_enriched_products`.

## Required environment (optional for local tests)

- `PROJECT_ENDPOINT` / `FOUNDRY_ENDPOINT`
- `FOUNDRY_AGENT_ID_FAST`
- `FOUNDRY_AGENT_ID_RICH`
- `MODEL_DEPLOYMENT_NAME_FAST`
- `MODEL_DEPLOYMENT_NAME_RICH`
- `EVENTHUB_CONNECTION_STRING`
- `AI_SEARCH_ENDPOINT`
- `AI_SEARCH_ADMIN_KEY` (optional fallback when managed identity is unavailable)
- `AI_SEARCH_VECTOR_INDEX` (default: `product_search_index`)
- `AI_SEARCH_INDEXER_NAME`
- `AI_SEARCH_PUSH_IMMEDIATE` (`true|false`, default `false`)

## Local test command

`python -m pytest apps/search-enrichment-agent/tests -q`
