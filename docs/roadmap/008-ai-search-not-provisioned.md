# 008: Azure AI Search Not Provisioned

**Severity**: Medium  
**Category**: Infrastructure  
**Discovered**: February 2026

## Summary

The `ecommerce-catalog-search` agent depends on Azure AI Search for vector/hybrid search, but the AI Search resource is not provisioned in the shared infrastructure Bicep module.

## Current State

- `apps/ecommerce-catalog-search/` has settings and dependencies for Azure AI Search
- `lib/src/holiday_peak_lib/config/settings.py` includes AI Search configuration fields
- `.infra/modules/shared-infrastructure/` Bicep does **not** include an `Microsoft.Search/searchServices` resource
- No AI Search index schema has been deployed
- The catalog-search agent cannot fulfill its primary purpose without this resource

## Expected Behavior

- Azure AI Search should be provisioned as part of shared infrastructure
- An index schema should be created for product catalog data
- The catalog-search agent should populate and query the index
- Vector search embeddings should be generated using Azure OpenAI

## Suggested Fix

1. Add Azure AI Search Bicep module to `.infra/modules/shared-infrastructure/`
2. Define index schema for product catalog (fields: name, description, category, price, embedding vector)
3. Add indexer or push-based indexing from the CRUD service product events
4. Configure the catalog-search agent with AI Search endpoint and key
5. Update `deploy-azd.yml` to include AI Search provisioning

## Files to Modify

- `.infra/modules/shared-infrastructure/shared-infrastructure-main.bicep` — Add AI Search resource
- `apps/ecommerce-catalog-search/src/` — Ensure AI Search client is configured
- `.github/workflows/deploy-azd.yml` — Add index schema deployment step

## Implementation Notes (Issue #32)

- Shared infra now provisions a single Azure AI Search service and `catalog-products` index in `.infra/modules/shared-infrastructure/shared-infrastructure.bicep`.
- Outputs now propagate through `.infra/modules/shared-infrastructure/shared-infrastructure-main.bicep` and `.infra/azd/main.bicep`:
	- `AI_SEARCH_ENDPOINT`
	- `AI_SEARCH_INDEX`
	- `AI_SEARCH_AUTH_MODE`
- Deployment wiring now forwards these values through `.github/workflows/deploy-azd.yml` and Helm render hooks:
	- `.infra/azd/hooks/render-helm.sh`
	- `.infra/azd/hooks/render-helm.ps1`
- `apps/ecommerce-catalog-search` runtime now:
	- Queries Azure AI Search when configured (`ai_search.py` + `agents.py`)
	- Falls back safely to existing hash/mock retrieval path when AI Search is missing/unavailable
	- Upserts/deletes index documents from existing product event flow (`event_handlers.py`)

## Cost Considerations

- AI Search Basic tier: ~$75/month (1 replica, 1 partition)
- Free tier available for development (limited to 50MB, 3 indexes)
- Consider using Free tier for dev environment and Basic/Standard for staging/prod
