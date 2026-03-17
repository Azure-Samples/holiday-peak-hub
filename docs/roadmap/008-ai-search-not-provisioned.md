# 008: Azure AI Search Not Provisioned

**Severity**: Medium  
**Category**: Infrastructure  
**Discovered**: February 2026

## Summary

The `ecommerce-catalog-search` agent depends on Azure AI Search for vector/hybrid search, but the AI Search resource is not provisioned in the shared infrastructure Bicep module.

## Current State

- `apps/ecommerce-catalog-search/` has settings and dependencies for Azure AI Search
- `lib/src/holiday_peak_lib/config/settings.py` includes AI Search configuration fields
- `.infra/modules/shared-infrastructure/` Bicep provisions the shared `Microsoft.Search/searchServices` resource
- `azd` `postprovision` ensures the `catalog-products` index after the service is reachable
- The catalog-search agent can query the shared index when configured and degrade safely when Search is unavailable

## Expected Behavior

- Azure AI Search should be provisioned as part of shared infrastructure
- An index schema should be created for product catalog data
- The catalog-search agent should populate and query the index
- Vector search embeddings should be generated using Azure OpenAI

## Resolution

1. Shared infrastructure provisions the Azure AI Search service.
2. `azd` `postprovision` ensures the `catalog-products` index after service readiness.
3. The catalog-search runtime consumes `AI_SEARCH_ENDPOINT`, `AI_SEARCH_INDEX`, and `AI_SEARCH_AUTH_MODE` from deploy outputs.
4. Product event handlers maintain Search documents when Search configuration is present.

## Files Updated

- `.infra/modules/shared-infrastructure/shared-infrastructure.bicep` — Shared AI Search service provisioning
- `.infra/azd/hooks/ensure-ai-search-index.ps1` — Windows postprovision index ensure hook
- `.infra/azd/hooks/ensure-ai-search-index.sh` — POSIX postprovision index ensure hook
- `azure.yaml` — Postprovision orchestration for index ensure
- `apps/ecommerce-catalog-search/src/` — AI Search client/runtime usage

## Implementation Notes (Issue #32)

- Shared infra now provisions a single Azure AI Search service in `.infra/modules/shared-infrastructure/shared-infrastructure.bicep`.
- The `catalog-products` index is ensured after resource creation by `azd` `postprovision` hooks.
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
