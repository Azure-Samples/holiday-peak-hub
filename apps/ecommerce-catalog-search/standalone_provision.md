# Standalone Provisioning — `ecommerce-catalog-search`

This runbook provisions the **slim ACA-only** stack for the `ecommerce-catalog-search` agent, including a dedicated **Azure AI Search** service. It is the deployment path used by the [`Cataldir/wwwmsft`](https://github.com/Cataldir/wwwmsft) remote — a single-agent, self-contained topology that does not require the shared infrastructure (AKS, Foundry, Cosmos, Event Hubs, etc.) used by the canonical full deploy.

> **Why this path exists**: the canonical full deploy under `.infra/modules/shared-infrastructure/` provisions one AI Search via the AI Foundry AVM module shared by all agents, but its compiled ARM template exceeds the 4 MB Azure deployment request limit when run alone. The slim path under `.infra/azd/` strips shared infrastructure and provisions a standalone AI Search scoped to this single agent.

---

## Topology

| Resource | SKU / Tier | Purpose |
|----------|-----------|---------|
| Resource group | n/a | Container for everything below |
| Azure Container Registry | Basic | Hosts the catalog-search image |
| Log Analytics workspace | PerGB2018 | ACA logs |
| User-assigned managed identity | n/a | Workload identity for the Container App |
| Azure Container Apps environment | Consumption | Runtime |
| Azure Container App | Consumption (port 8000) | Runs `ecommerce-catalog-search` |
| **Azure AI Search** | **Basic** | Catalog index for hybrid + vector search |
| **Azure Cache for Redis** (Hot memory) | **Basic C0** | `HotMemory` — short-lived conversation context |
| **Azure Cosmos DB** (Warm memory) | **Serverless** | `WarmMemory` — conversation threads (`agent-memory` db/container) |
| **Azure Storage Account** (Cold memory) | **Standard_LRS** | `ColdMemory` — long-term agent state (`agent-memory` blob container) |
| RBAC: `Search Index Data Contributor` | n/a | Granted to the workload identity on AI Search |
| RBAC: `Search Service Contributor` | n/a | Granted to the workload identity on AI Search |
| RBAC: `Cosmos DB Built-in Data Contributor` | n/a | Granted to the workload identity on the Cosmos account (data plane) |
| RBAC: `Storage Blob Data Contributor` | n/a | Granted to the workload identity on the Storage account |
| RBAC: `AcrPull` | n/a | Granted to the workload identity on ACR |

> **Memory tiers are auto-provisioned and auto-wired.** `holiday_peak_lib`'s `create_standard_app()` constructs `HotMemory`/`WarmMemory`/`ColdMemory` automatically when their env vars are set, so the agent gets full conversation context out of the box. To bring your own memory infrastructure, set `PROVISION_MEMORY_TIERS=false` in the azd env and supply `REDIS_HOST`, `COSMOS_ACCOUNT_URI`, `COSMOS_DATABASE`, `COSMOS_CONTAINER`, `BLOB_ACCOUNT_URL`, and `BLOB_CONTAINER` overrides.

**Approximate provision time**: ~17 minutes (AI Search Basic SKU dominates at ~6–15 min; Cosmos serverless and Storage finish in seconds; Redis Basic C0 takes ~5–10 min in parallel).

---

## Prerequisites (one-time)

```pwsh
# Required tooling
azd version              # >= 1.23
az --version             # >= 2.60
git --version

# Sign in
az login --tenant <YOUR_TENANT_ID>
az account set --subscription "<YOUR_SUBSCRIPTION_NAME_OR_ID>"
azd auth login --tenant-id <YOUR_TENANT_ID>

# Register Azure providers (one-time per subscription)
az provider register --namespace Microsoft.App
az provider register --namespace Microsoft.ContainerRegistry
az provider register --namespace Microsoft.OperationalInsights
az provider register --namespace Microsoft.Search
az provider register --namespace Microsoft.ManagedIdentity
az provider register --namespace Microsoft.Cache         # Redis (Hot memory)
az provider register --namespace Microsoft.DocumentDB    # Cosmos DB (Warm memory)
az provider register --namespace Microsoft.Storage       # Blob (Cold memory)
```

---

## Step 1 — Clone the wwwmsft remote

```pwsh
cd <your-parent-dir>
git clone https://github.com/Cataldir/wwwmsft.git
cd wwwmsft
git checkout main
git log --oneline -1
# Expect at least: 2172eb19 feat(catalog-search): provision standalone Azure AI Search service in slim ACA stack
```

## Step 2 — Initialize the azd environment

`projectName` becomes the prefix for ACR (`<projectName><env>acr`), AI Search (`<projectName><env>search`), and the resource group (`<projectName>-<env>-rg`). It must be **lowercase, alphanumeric, ~12–15 chars**, and yield globally unique resource names.

```pwsh
$envName     = 'dev'
$location    = 'northcentralus'
$projectName = '<pick-fresh-suffix>'    # e.g. wwwmsftaca408 — must produce unique ACR/Search names

azd env new $envName --location $location --subscription (az account show --query id -o tsv)
azd env select $envName
```

## Step 3 — Configure environment variables

These map directly to parameters in `.infra/azd/main.bicep`.

### Required

```pwsh
azd env set AZURE_LOCATION              $location
azd env set AZURE_RESOURCE_GROUP        "$projectName-$envName-rg"
azd env set projectName                 $projectName

# Slim ACA path — disable shared infra, enable catalog-search
azd env set deployShared                false
azd env set deployCatalogSearchAca      true
azd env set privateNetworkingEnabled    false

# AI Search — provisioned standalone in this stack
azd env set provisionAiSearch           true
azd env set aiSearchSku                 basic
azd env set catalogSearchRequireAiSearch true

# Azure AI Foundry — REQUIRED. Bicep enforces @minLength(10) on projectEndpoint;
# `azd provision` fails fast if missing, by design. The catalog-search agent
# cannot generate grounded answers without Foundry, so deployments must not
# silently land in degraded mode.
azd env set PROJECT_ENDPOINT            'https://<foundry>.services.ai.azure.com/api/projects/<project>'
azd env set MODEL_DEPLOYMENT_NAME_FAST  gpt-5-nano
azd env set MODEL_DEPLOYMENT_NAME_RICH  gpt-5
```

### Optional

Point at an existing AI Search instead of provisioning a new one:

```pwsh
azd env set provisionAiSearch  false
azd env set aiSearchEndpoint   'https://<existing>.search.windows.net'
```

Pin specific Foundry agent IDs (instead of letting the SDK pick by deployment):

```pwsh
azd env set FOUNDRY_AGENT_ID_FAST   '<agent-id>'
azd env set FOUNDRY_AGENT_ID_RICH   '<agent-id>'
azd env set FOUNDRY_PROJECT_NAME    '<friendly-project-name>'
```

Bring your own memory tiers (skip Redis/Cosmos/Blob provisioning) — the slim stack provisions all three by default:

```pwsh
azd env set PROVISION_MEMORY_TIERS  false
azd env set REDIS_HOST              '<existing-cache>.redis.cache.windows.net'
azd env set COSMOS_ACCOUNT_URI      'https://<existing-cosmos>.documents.azure.com:443/'
azd env set COSMOS_DATABASE         '<existing-database>'
azd env set COSMOS_CONTAINER        '<existing-container>'
azd env set BLOB_ACCOUNT_URL        'https://<existing-storage>.blob.core.windows.net/'
azd env set BLOB_CONTAINER          '<existing-container>'
# When BYO Redis, store the primary key in your Key Vault and set:
azd env set KEY_VAULT_URI           'https://<your-keyvault>.vault.azure.net/'
azd env set REDIS_PASSWORD_SECRET_NAME  'redis-primary-key'
```

## Step 4 — Preview (recommended)

```pwsh
azd provision --preview --no-prompt
```

Expect a plan that includes `Create: Search service: <projectName><env>search` alongside the ACR, ACA env, Container App, and Log Analytics resources.

## Step 5 — Provision infrastructure

```pwsh
azd provision --no-prompt
```

Expected wall time: **~17 minutes**. Successful output ends with:

```
(✓) Done: Resource group: <projectName>-<env>-rg
(✓) Done: Container Registry: <projectName><env>acr
(✓) Done: Log Analytics workspace: <projectName>-<env>-aca-law
(✓) Done: Container Apps Environment: ecommerce-catalog-search-<env>-env
(✓) Done: Container App: ecommerce-catalog-search
(✓) Done: Search service: <projectName><env>search
(✓) Done: Redis Cache: <projectName>-<env>-redis
(✓) Done: Cosmos DB account: <projectName><env>cos
(✓) Done: Storage account: <projectName><env>store

SUCCESS: Your application was provisioned in Azure in ~17 minutes.
```

## Step 6 — Build and deploy the catalog-search image

This builds the container image via remote ACR and rolls a new ACA revision with the real image. Takes **~3–5 min**.

```pwsh
azd deploy ecommerce-catalog-search --no-prompt
```

> **Cosmetic post-deploy warning you can ignore**:
> `extension azure.ai.agents project hook postdeploy failed: ... default environment not found`
> This comes from an unrelated azd extension (Foundry agents) and runs **after** the ACA deploy succeeds. The deploy itself is reported with `(✓) Done: Deploying service ecommerce-catalog-search` immediately above the warning.

## Step 7 — Verify

```pwsh
$rg         = (azd env get-values | Select-String '^AZURE_RESOURCE_GROUP=').ToString().Split('=',2)[1].Trim('"')
$searchName = (az resource list -g $rg --resource-type Microsoft.Search/searchServices --query "[0].name" -o tsv)

# Resources
az resource list -g $rg --query "[].{name:name, type:type, state:provisioningState}" -o table

# AI Search health
az resource show -g $rg -n $searchName --resource-type Microsoft.Search/searchServices `
  --query "{state:properties.provisioningState, status:properties.status, sku:sku.name}" -o table

# RBAC on AI Search (expect Search Index Data Contributor + Search Service Contributor on the workload identity)
$searchId = az resource show -g $rg -n $searchName --resource-type Microsoft.Search/searchServices --query id -o tsv
az role assignment list --scope $searchId --query "[].{role:roleDefinitionName, principalId:principalId}" -o table

# Container App revision and AI_SEARCH_ENDPOINT
az containerapp show -n ecommerce-catalog-search -g $rg --query "{
  revision: properties.latestRevisionName,
  image:    properties.template.containers[0].image,
  fqdn:     properties.configuration.ingress.fqdn,
  AI_SEARCH_ENDPOINT: properties.template.containers[0].env[?name=='AI_SEARCH_ENDPOINT'].value | [0]
}" -o json
```

## Step 8 — Smoke-test the public endpoint

```pwsh
$fqdn = az containerapp show -n ecommerce-catalog-search -g $rg --query "properties.configuration.ingress.fqdn" -o tsv
Invoke-WebRequest "https://$fqdn/health" -UseBasicParsing -TimeoutSec 30
```

> **Expected gotcha — readiness probe gates external traffic**
>
> With `catalogSearchRequireAiSearch=true` (default), `/ready` returns **503** until the `catalog-products` index exists and contains at least one document. ACA's readiness probe withholds external traffic until `/ready` is 200, so public requests will time out until you either:
>
> 1. **Seed the index** — create `catalog-products` in AI Search and push at least one document. Use `holiday_peak_lib.mcp.ai_search_indexing` or the `search-enrichment-agent` data path.
> 2. **Loosen the gate for smoke tests** —
>    ```pwsh
>    az containerapp update -n ecommerce-catalog-search -g $rg --set-env-vars CATALOG_SEARCH_REQUIRE_AI_SEARCH=false
>    ```

---

## Quick-reference happy path

```pwsh
git clone https://github.com/Cataldir/wwwmsft.git
cd wwwmsft
azd auth login --tenant-id <YOUR_TENANT_ID>
azd env new dev --location northcentralus --subscription (az account show --query id -o tsv)
azd env set projectName              <pick-fresh-suffix>
azd env set deployShared             false
azd env set deployCatalogSearchAca   true
azd env set provisionAiSearch        true
azd env set aiSearchSku              basic
azd env set PROJECT_ENDPOINT         'https://<foundry>.services.ai.azure.com/api/projects/<project>'
azd env set MODEL_DEPLOYMENT_NAME_FAST gpt-5-nano
azd env set MODEL_DEPLOYMENT_NAME_RICH gpt-5
azd provision --no-prompt
azd deploy ecommerce-catalog-search --no-prompt
```

Total wall time: **~22 minutes** (17 provision + 5 deploy).

---

## Cleanup

```pwsh
azd down --purge --force --no-prompt
```

`--purge` is required because AI Search and ACR have soft-delete behavior; without it a redeploy with the same `projectName`/`env` may fail with name conflicts.

---

## Troubleshooting

### `azd deploy` fails with `0 resource groups with prefix or suffix with value: '<env-name>'`
`azd` cannot resolve the Container App's resource group. The slim Bicep emits `AZURE_RESOURCE_GROUP` as a deployment output so this is normally written automatically into `.azure/<env-name>/.env` after `azd provision`. If the file is missing or stale (typically because you ran `azd deploy` before `azd provision`, or your env was created from a tip that predates the output), set it manually:

```pwsh
azd env set AZURE_RESOURCE_GROUP "$projectName-$envName-rg"
azd deploy ecommerce-catalog-search --no-prompt
```

Verify the env file then has both keys:

```pwsh
Get-Content .azure\$envName\.env | Select-String 'AZURE_RESOURCE_GROUP|AZURE_CONTAINER_APP_NAME'
```

### `azd provision` fails with `parameter 'projectEndpoint' must have a length of at least 10`
Foundry is a hard requirement of the agent — Bicep enforces this so deployments cannot silently run in degraded mode. Set the env var before re-running:

```pwsh
azd env set PROJECT_ENDPOINT 'https://<foundry>.services.ai.azure.com/api/projects/<project>'
azd provision --no-prompt
```

### `RuntimeError: Event Hub binding missing` on container start
The slim stack does not provision Event Hubs. The Bicep already sets `EVENT_HUB_OPTIONAL=true` so the lifespan factory in `holiday_peak_lib.utils.event_hub` logs `eventhub_binding_skipped` and continues. If you see the runtime error anyway, confirm:

```pwsh
az containerapp show -n ecommerce-catalog-search -g $rg `
  --query "properties.template.containers[0].env[?name=='EVENT_HUB_OPTIONAL'].value | [0]" -o tsv
```

It must return `true`. If it does not, your image predates the [Event Hub optional change](../../lib/src/holiday_peak_lib/utils/event_hub.py) — rerun `azd deploy`.

### `/ready` returns 503 with `ai_search_not_configured`
The container started before `AI_SEARCH_ENDPOINT` was wired. Force a new revision:

```pwsh
az containerapp revision restart -n ecommerce-catalog-search -g $rg `
  --revision (az containerapp show -n ecommerce-catalog-search -g $rg --query "properties.latestRevisionName" -o tsv)
```

### `/ready` returns 503 with `index 'catalog-products' was not found`
Expected — see Step 8. Seed the index or temporarily set `CATALOG_SEARCH_REQUIRE_AI_SEARCH=false`.

### `az acr task logs` crashes with `UnicodeEncodeError: 'charmap' codec`
Known Windows charmap codec bug in the Azure CLI. Use `az acr task list-runs --registry <acr-name>` instead.

### `azd provision` fails with template size > 4 MB
You are running the canonical full template, not the slim path. Confirm `deployShared=false` and `deployCatalogSearchAca=true` in `azd env get-values`. The slim `.infra/azd/main.json` should compile to ~76 KB (Redis + Cosmos + Storage + AI Search + ACA + ACR + Log Analytics + RBAC).

### Container starts but logs `hot_memory.* degraded to fail-open mode`
The Hot memory tier (Redis) cannot reach its host or authenticate. `HotMemory` fails open by design so degraded cache does not crash agents, but conversation context is lost across requests. Verify:

```pwsh
$rg = (azd env get-values | Select-String '^AZURE_RESOURCE_GROUP=').ToString().Split('=',2)[1].Trim('"')
$redis = (az resource list -g $rg --resource-type Microsoft.Cache/Redis --query "[0].name" -o tsv)
az redis show -g $rg -n $redis --query "{state:provisioningState, host:hostName, sslPort:sslPort}" -o table
az containerapp show -g $rg -n ecommerce-catalog-search --query "properties.template.containers[0].env[?name=='REDIS_HOST'].value | [0]" -o tsv
```

`REDIS_HOST` must equal the cache `hostName`. If empty, you set `PROVISION_MEMORY_TIERS=false` without supplying a `REDIS_HOST` override — re-run `azd provision` with the env unset (or set to `true`).

### `WarmMemory` writes fail with `Forbidden` from Cosmos DB
Cosmos data-plane RBAC propagation can lag account creation by a few minutes. The slim Bicep assigns the workload identity the **Built-in Data Contributor** SQL role at account scope, but the role assignment is eventually consistent. Wait 2–5 min after the first cold start, then verify:

```pwsh
$cosmos = (az resource list -g $rg --resource-type Microsoft.DocumentDB/databaseAccounts --query "[0].name" -o tsv)
$principalId = (azd env get-values | Select-String 'CATALOG_SEARCH_MANAGED_IDENTITY_PRINCIPAL_ID=').ToString().Split('=',2)[1].Trim('"')
az cosmosdb sql role assignment list -g $rg -a $cosmos --query "[?principalId=='$principalId'].{role:roleDefinitionId, scope:scope}" -o table
```

If the assignment is missing, re-run `azd provision` — Bicep is idempotent and will reconcile.

### `ColdMemory` writes return `AuthorizationPermissionMismatch` from Blob Storage
Same pattern as Cosmos — `Storage Blob Data Contributor` propagation is eventually consistent (typically < 60 s). Confirm the role is assigned:

```pwsh
$storage = (az resource list -g $rg --resource-type Microsoft.Storage/storageAccounts --query "[0].name" -o tsv)
az role assignment list --assignee $principalId --scope (az storage account show -g $rg -n $storage --query id -o tsv) -o table
```

---

## What this runbook does NOT cover

- **Index schema creation and seeding**: the `catalog-products` index schema lives in the catalog ingestion pipeline, not in this Bicep. Application data work is required after provisioning to make `/ready` return 200.
- **Foundry deployment provisioning**: this runbook assumes you already have a Foundry project and deployments. `PROJECT_ENDPOINT` is enforced by Bicep `@minLength(10)` so provisioning fails fast if missing — there is no degraded-mode path.
- **Private networking**: the slim stack uses public ingress on the Container App. Set `privateNetworkingEnabled=true` in upstream `main` (canonical path), not here.
- **Multi-agent topology**: this runbook deploys only `ecommerce-catalog-search`. For the full 26-agent platform, use the canonical `.infra/modules/shared-infrastructure/shared-infrastructure-main.bicep` deployment via the upstream AKS workflow.
