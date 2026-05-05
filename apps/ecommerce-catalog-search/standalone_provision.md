# Standalone Provisioning — `ecommerce-catalog-search`

This runbook provisions the **slim ACA-only** stack for the `ecommerce-catalog-search` agent, including a dedicated **Azure AI Search** service, **Azure AI Foundry** account/project/model deployments, and the three-tier memory stores (Redis / Cosmos / Blob). It is the deployment path used by the [`Cataldir/wwwmsft`](https://github.com/Cataldir/wwwmsft) remote — a single-agent, self-contained topology that does not require the shared platform infrastructure (AKS, Event Hubs, Postgres, etc.) used by the canonical full deploy.

> **Why this path exists**: the canonical full deploy under `.infra/modules/shared-infrastructure/` provisions one AI Search via the AI Foundry AVM module shared by all 26 agents, but its compiled ARM template exceeds the 4 MB Azure deployment request limit when run alone. The slim path under `.infra/azd/` strips shared infrastructure and provisions a standalone AI Search, Foundry account, and memory tier set scoped to this single agent — so a clean subscription gets a fully working agent in one `azd up`.

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
| **Azure AI Foundry account** (AIServices) | **S0** | Foundry account hosting the project + model deployments (deployed in `westus3` for gpt-5 availability) |
| **Azure AI Foundry project** | n/a | Project consumed by the agent runtime via `PROJECT_ENDPOINT` |
| **gpt-5** model deployment | **GlobalStandard, 50 TPM** | Rich-role model target |
| **gpt-5-nano** model deployment | **GlobalStandard, 50 TPM** | Fast-role model target (`dependsOn` gpt-5 to serialize writes) |
| RBAC: `Search Index Data Contributor` | n/a | Granted to the workload identity on AI Search |
| RBAC: `Search Service Contributor` | n/a | Granted to the workload identity on AI Search |
| RBAC: `Cosmos DB Built-in Data Contributor` | n/a | Granted to the workload identity on the Cosmos account (data plane) |
| RBAC: `Storage Blob Data Contributor` | n/a | Granted to the workload identity on the Storage account |
| RBAC: `Cognitive Services User` | n/a | Granted to the workload identity on the Foundry account (inference data plane) |
| RBAC: `Azure AI Developer` | n/a | Granted to the workload identity on the Foundry account (agent runtime + project ops) |
| RBAC: `AcrPull` | n/a | Granted to the workload identity on ACR |

> **Memory tiers and Foundry are auto-provisioned and auto-wired.** `holiday_peak_lib`'s `create_standard_app()` constructs `HotMemory`/`WarmMemory`/`ColdMemory` and resolves the Foundry agent runtime automatically when their env vars are set, so the agent gets full conversation context and a working model target out of the box. To bring your own infrastructure, set `PROVISION_MEMORY_TIERS=false` and/or `PROVISION_FOUNDRY=false` in the azd env and supply the corresponding overrides.

**Approximate provision time**: ~22 minutes (AI Search Basic SKU dominates at ~6–15 min; gpt-5 + gpt-5-nano deployments take ~5–8 min; Cosmos serverless and Storage finish in seconds; Redis Basic C0 takes ~5–10 min in parallel).

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
az provider register --namespace Microsoft.Cache             # Redis (Hot memory)
az provider register --namespace Microsoft.DocumentDB        # Cosmos DB (Warm memory)
az provider register --namespace Microsoft.Storage           # Blob (Cold memory)
az provider register --namespace Microsoft.CognitiveServices # Azure AI Foundry account + projects + deployments
```

> **Quota requirements**: gpt-5 / gpt-5-nano deployments need `OpenAI.GlobalStandard.gpt-5` and `OpenAI.GlobalStandard.gpt-5-nano` capacity in the chosen Foundry region (default `westus3`). The slim Bicep requests **50 TPM** for each. If your subscription has zero quota, request via the Azure portal *Azure AI services → Quotas* blade before running `azd provision`, or override `fastModelCapacity` / `richModelCapacity` to a smaller value.

---

## Step 1 — Clone the wwwmsft remote

```pwsh
cd <your-parent-dir>
git clone https://github.com/Cataldir/wwwmsft.git
cd wwwmsft
git checkout main
git log --oneline -1
# Expect at least: 2a2c5ef3 feat(catalog-search): provision Azure AI Foundry account, project, and gpt-5/gpt-5-nano deployments in slim ACA stack
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

# Azure AI Foundry — auto-provisioned by default. The slim Bicep creates an
# AIServices account, a project, and gpt-5 / gpt-5-nano deployments in westus3.
# Override the model deployment names only if you want non-default identifiers;
# the defaults match the agent runtime expectations.
azd env set PROVISION_FOUNDRY           true
azd env set AI_FOUNDRY_LOCATION         westus3
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

Bring your own Foundry project (skip the AIServices account / project / deployments) — the slim stack provisions Foundry by default:

```pwsh
azd env set PROVISION_FOUNDRY     false
azd env set PROJECT_ENDPOINT      'https://<existing-foundry>.services.ai.azure.com/api/projects/<existing-project>'
azd env set FOUNDRY_PROJECT_NAME  '<existing-project>'
# Tune model deployments to match your existing project
azd env set MODEL_DEPLOYMENT_NAME_FAST  '<your-fast-deployment>'
azd env set MODEL_DEPLOYMENT_NAME_RICH  '<your-rich-deployment>'
```

> When using BYO Foundry, you must grant the Container App's UAMI **Cognitive Services User** + **Azure AI Developer** roles on your existing Foundry account *before* the first request. The slim Bicep does not modify pre-existing Foundry RBAC.

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

Expected wall time: **~22 minutes** (AI Search Basic dominates; gpt-5 + gpt-5-nano deployments take ~5–8 min; Cosmos serverless and Storage finish in seconds; Redis Basic C0 takes ~5–10 min in parallel). Successful output ends with:

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
(✓) Done: Cognitive Services account: <projectName><env>foundry
(✓) Done: Cognitive Services account project: <projectName>-<env>-proj
(✓) Done: Cognitive Services deployment: gpt-5
(✓) Done: Cognitive Services deployment: gpt-5-nano

SUCCESS: Your application was provisioned in Azure in ~22 minutes.
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

Fully auto-provisioned (Foundry + memory tiers + AI Search) — no BYO infra required:

```pwsh
git clone https://github.com/Cataldir/wwwmsft.git
cd wwwmsft
azd auth login --tenant-id <YOUR_TENANT_ID>
azd env new dev --location northcentralus --subscription (az account show --query id -o tsv)
azd env set AZURE_RESOURCE_GROUP     '<pick-fresh-suffix>-dev-rg'
azd env set projectName              <pick-fresh-suffix>
azd env set deployShared             false
azd env set deployCatalogSearchAca   true
azd env set provisionAiSearch        true
azd env set aiSearchSku              basic
azd env set PROVISION_FOUNDRY        true
azd env set AI_FOUNDRY_LOCATION      westus3
azd env set PROVISION_MEMORY_TIERS   true
azd provision --no-prompt
azd deploy ecommerce-catalog-search --no-prompt
```

Total wall time: **~25–27 minutes** (~22 provision + ~3–5 deploy).

---

## Cleanup

```pwsh
azd down --purge --force --no-prompt
```

`--purge` is required because AI Search, ACR, **Azure AI Foundry (Cognitive Services account)**, and Key Vault all have soft-delete behavior; without it a redeploy with the same `projectName`/`env` may fail with name conflicts. Foundry soft-delete in particular blocks re-creating an account with the same `customSubDomainName` until the previous account is purged (`az cognitiveservices account purge`).

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
This is the old Foundry-required behavior from a pre-Foundry-auto-provision commit. The slim stack now auto-provisions Foundry by default. Confirm you are on the up-to-date `wwwmsft/main`:

```pwsh
git pull wwwmsft main
git log --oneline wwwmsft/main -1
# Expect: 2a2c5ef3 feat(catalog-search): provision Azure AI Foundry account, project, and gpt-5/gpt-5-nano deployments in slim ACA stack
```

Then re-provision with auto-provisioning enabled:

```pwsh
azd env set PROVISION_FOUNDRY true
azd env unset PROJECT_ENDPOINT
azd provision --no-prompt
```

If you intend to bring your own Foundry instead, supply a non-empty `PROJECT_ENDPOINT` (length ≥ 10) before re-running.

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
You are running the canonical full template, not the slim path. Confirm `deployShared=false` and `deployCatalogSearchAca=true` in `azd env get-values`. The slim `.infra/azd/main.json` should compile to ~91 KB (Redis + Cosmos + Storage + AI Search + Foundry account + project + 2 model deployments + ACA + ACR + Log Analytics + RBAC).

### `azd provision` fails with `InsufficientQuota` on `gpt-5` or `gpt-5-nano` deployment
Foundry model deployments are subject to per-region TPM quota. The slim Bicep requests **50 TPM** for each model. If your subscription has zero quota in the chosen region:

1. Request quota via the Azure portal: *Azure AI services → Quotas* → select region (default `westus3`) and model (`OpenAI.GlobalStandard.gpt-5` and `OpenAI.GlobalStandard.gpt-5-nano`).
2. Or override capacity at provision time:

```pwsh
az deployment sub create --name retry --location $env:AZURE_LOCATION --template-file .infra/azd/main.bicep `
  --parameters .infra/azd/main.parameters.json `
  --parameters fastModelCapacity=10 richModelCapacity=10
```

Or switch regions:

```pwsh
azd env set AI_FOUNDRY_LOCATION eastus2  # or another region with available quota
azd provision --no-prompt
```

### Container starts but `PROJECT_ENDPOINT` is empty / agent returns `No model target configured`
Most commonly caused by `PROVISION_FOUNDRY=false` without supplying `PROJECT_ENDPOINT`. Check:

```pwsh
azd env get-values | Select-String 'PROJECT_ENDPOINT|PROVISION_FOUNDRY|MODEL_DEPLOYMENT_NAME'
az containerapp show -g $rg -n ecommerce-catalog-search --query "properties.template.containers[0].env[?name=='PROJECT_ENDPOINT'].value | [0]" -o tsv
```

Fix by re-enabling auto-provisioning:

```pwsh
azd env set PROVISION_FOUNDRY true
azd env unset PROJECT_ENDPOINT
azd provision --no-prompt
```

### Foundry calls fail with `403 Forbidden` from `services.ai.azure.com`
Foundry RBAC propagation can lag account creation by up to 5 minutes. The slim Bicep assigns **Cognitive Services User** and **Azure AI Developer** to the workload identity at account scope. Verify:

```pwsh
$foundry = (az resource list -g $rg --resource-type Microsoft.CognitiveServices/accounts --query "[0].id" -o tsv)
$principalId = (azd env get-values | Select-String 'CATALOG_SEARCH_MANAGED_IDENTITY_PRINCIPAL_ID=').ToString().Split('=',2)[1].Trim('"')
az role assignment list --assignee $principalId --scope $foundry --query "[].roleDefinitionName" -o tsv
# Expect: 'Cognitive Services User' and 'Azure AI Developer'
```

If calls still fail after 5 minutes, restart the Container App revision to refresh the token cache:

```pwsh
az containerapp revision restart -g $rg -n ecommerce-catalog-search --revision $(az containerapp show -g $rg -n ecommerce-catalog-search --query 'properties.latestRevisionName' -o tsv)
```

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
- **Foundry agent CRUD**: the slim Bicep provisions a Foundry **account + project + model deployments** but does not create named agents (the agent runtime auto-discovers them by deployment when `FOUNDRY_AGENT_ID_*` is unset). Use the Foundry portal or SDK to create persistent named agents if you need IDs to pin in `FOUNDRY_AGENT_ID_FAST` / `FOUNDRY_AGENT_ID_RICH`.
- **Private networking**: the slim stack uses public ingress on the Container App. Set `privateNetworkingEnabled=true` in upstream `main` (canonical path), not here.
- **Multi-agent topology**: this runbook deploys only `ecommerce-catalog-search`. For the full 26-agent platform, use the canonical `.infra/modules/shared-infrastructure/shared-infrastructure-main.bicep` deployment via the upstream AKS workflow.
