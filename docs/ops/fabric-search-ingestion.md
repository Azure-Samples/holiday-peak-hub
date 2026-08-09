# Fabric Search Ingestion Runbook

This runbook covers the `search-enrichment-agent` Fabric-to-Azure-AI-Search MCP tools. The search-enrichment bounded context owns search document shaping and AI Search publication; `ecommerce-catalog-search` only queries the resulting catalog indexes.

## Supported Sources

Use `FABRIC_SOURCE_KIND=sql` for Fabric SQL database, Warehouse, or SQL analytics endpoint tables/views exposed over TDS with Entra authentication. Azure AI Search SQL indexers require a single table or view and a target index created up front.

Use `FABRIC_SOURCE_KIND=onelake_files` only for Fabric lakehouse Files or shortcuts. Do not point `FABRIC_ONELAKE_FILES_PATH` at `Tables/`, Parquet, or Delta table content; those are rejected by the service-local guard because the OneLake Files indexer does not support them.

## Operator Flow

1. Configure Fabric and AI Search environment variables on `search-enrichment-agent`.
2. Call `/fabric-search-ingestion/discover_source`. If the SQL driver is unavailable, pass `source_metadata.columns` in the MCP payload for offline planning or install the Microsoft ODBC Driver for SQL Server plus `pyodbc` in the runtime image.
3. Call `/fabric-search-ingestion/build_mapping_plan` and review `confidence`, `evidence`, and `governance.approval_signal`.
4. Call `/fabric-search-ingestion/build_search_resources` and review the redacted index, skillset, data source, and indexer payloads.
5. Call `/fabric-search-ingestion/provision_search_resources` to create or update Azure AI Search resources through managed identity or `AI_SEARCH_ADMIN_KEY`.
6. Call `/fabric-search-ingestion/run_indexer` for an on-demand ingestion run.

## Standalone Skillset Deployment

This section deploys only the Fabric ingestion Search resources: the Azure AI Search index, skillset, data source, and indexer. It does not deploy the whole product and it does not change truth lifecycle state.

Use this path when `search-enrichment-agent` is already running and you only need to prepare or refresh the Fabric ingestion resources consumed by `ecommerce-catalog-search`.

### What Gets Created

| Resource | Default env var | Purpose |
| --- | --- | --- |
| Search index | `AI_SEARCH_VECTOR_INDEX` or `AI_SEARCH_INDEX` | Unified hybrid catalog index with text, facets, semantic config, and `content_vector` |
| Search skillset | `AI_SEARCH_SKILLSET_NAME` | Embeds `/document/content` into one vector per product document |
| Search data source | `AI_SEARCH_DATASOURCE_NAME` | Points Azure AI Search at Fabric SQL or OneLake Files |
| Search indexer | `AI_SEARCH_INDEXER_NAME` | Pulls Fabric content, runs the skillset, and writes documents into the index |

### 0. Choose How You Will Call The Tools

Local port-forwarded service:

```powershell
$env:SEARCH_ENRICHMENT_BASE_URL = "http://localhost:8080"
kubectl port-forward -n holiday-peak-agents deployment/search-enrichment-agent 8080:8000
```

APIM route:

```powershell
$env:SEARCH_ENRICHMENT_BASE_URL = "https://<apim-host>/agents/search-enrichment-agent"
```

The MCP URL pattern is always:

```text
${SEARCH_ENRICHMENT_BASE_URL}/mcp/<tool-path-without-leading-slash>
```

For example:

```text
http://localhost:8080/mcp/fabric-search-ingestion/build_search_resources
```

### 1. Configure The Running Service

Set these values in the selected `azd` environment before deploying or redeploying `search-enrichment-agent`:

```powershell
azd env select dev

azd env set AI_SEARCH_ENDPOINT "https://<search-service>.search.windows.net"
azd env set AI_SEARCH_AUTH_MODE "managed_identity"
azd env set AI_SEARCH_INDEX "catalog-products"
azd env set AI_SEARCH_VECTOR_INDEX "catalog-products"
azd env set AI_SEARCH_VECTOR_FIELD "content_vector"
azd env set AI_SEARCH_DATASOURCE_NAME "fabric-products-ds"
azd env set AI_SEARCH_SKILLSET_NAME "fabric-products-skillset"
azd env set AI_SEARCH_INDEXER_NAME "fabric-products-indexer"
azd env set AI_SEARCH_SEMANTIC_CONFIG_NAME "catalog-semantic"

azd env set EMBEDDING_RESOURCE_URI "https://<openai-or-foundry-resource>.openai.azure.com/"
azd env set EMBEDDING_DEPLOYMENT_NAME "text-embedding-3-small"
azd env set EMBEDDING_MODEL_NAME "text-embedding-3-small"
azd env set EMBEDDING_DIMENSIONS "1536"
```

For key auth in a dev-only environment, set `AI_SEARCH_AUTH_MODE=api_key` and `AI_SEARCH_ADMIN_KEY`. Do not commit keys or paste them into docs, issues, or logs.

### 2. Configure Fabric SQL Source

Use this for Fabric SQL database, Warehouse, or SQL analytics endpoint tables/views:

```powershell
azd env set FABRIC_SOURCE_KIND "sql"
azd env set FABRIC_SQL_ENDPOINT "<fabric-sql-endpoint>.fabric.microsoft.com"
azd env set FABRIC_SQL_DATABASE "<database-or-warehouse-name>"
azd env set FABRIC_SQL_SCHEMA "dbo"
azd env set FABRIC_SQL_TABLE "ProductsForSearch"
azd env set FABRIC_AUTH_MODE "managed_identity"
azd env set FABRIC_INCREMENTAL_COLUMN "modified_at"
azd env set FABRIC_SOFT_DELETE_COLUMN "is_deleted"
azd env set FABRIC_SOFT_DELETE_MARKER "true"
azd env set FABRIC_APPROVAL_COLUMN "approval_status"
azd env set FABRIC_APPROVAL_ACCEPTED_VALUES "approved,published"
```

Recommended source shape:

| Source column | Why it matters |
| --- | --- |
| `product_id` or `sku` | Becomes `id`, `sku`, and `entity_id` |
| `name` or `title` | Product title and semantic title field |
| `description` or `long_description` | Main retrieval text |
| `content` | Best option if you can expose a SQL view with pre-concatenated retrieval text |
| `brand`, `category`, `price`, `currency`, `availability` | Filters, facets, and ranking context |
| `approval_status` | Governance signal that operators review before provisioning |
| `modified_at` | Optional high-water mark for incremental indexing |
| `is_deleted` | Optional soft-delete signal |

If your table does not already have a `content` column, create a Fabric SQL view such as `ProductsForSearch` that concatenates high-signal fields. Azure AI Search field mappings copy fields; they do not concatenate SQL columns for you.

### 3. Alternative: Configure OneLake Files Source

Use this only for lakehouse Files or shortcuts containing supported formats such as JSON, CSV, Markdown, or text:

```powershell
azd env set FABRIC_SOURCE_KIND "onelake_files"
azd env set FABRIC_WORKSPACE_ID "<fabric-workspace-guid>"
azd env set FABRIC_ONELAKE_LAKEHOUSE_ID "<lakehouse-guid>"
azd env set FABRIC_ONELAKE_FILES_PATH "Files/catalog-search/products"
```

Do not use `Tables/...`, Parquet, or Delta paths. The service rejects those paths because Azure AI Search OneLake indexing does not support OneLake workspace Tables or Parquet/Delta table content.

### 4. Redeploy The Service If Env Changed

If you changed `azd` environment values, redeploy the service so the pod receives them:

```powershell
azd deploy --service search-enrichment-agent -e dev --no-prompt
```

Verify the service is reachable:

```powershell
curl.exe -s "$env:SEARCH_ENRICHMENT_BASE_URL/ready"
curl.exe -s "$env:SEARCH_ENRICHMENT_BASE_URL/mcp/tool_descriptions"
```

### 5. Discover The Source

Live discovery needs the runtime image to have the Microsoft ODBC Driver for SQL Server plus `pyodbc`. If that is not installed, pass metadata manually as shown in the offline example below.

Live discovery:

```powershell
curl.exe -s -X POST "$env:SEARCH_ENRICHMENT_BASE_URL/mcp/fabric-search-ingestion/discover_source" `
  -H "Content-Type: application/json" `
  -d "{}"
```

Offline discovery payload:

```powershell
$payload = @'
{
  "source_metadata": {
    "source_kind": "sql",
    "source_name": "RetailWarehouse.dbo.ProductsForSearch",
    "columns": [
      { "name": "product_id", "data_type": "nvarchar", "nullable": false },
      { "name": "title", "data_type": "nvarchar" },
      { "name": "long_description", "data_type": "nvarchar" },
      { "name": "brand_name", "data_type": "nvarchar" },
      { "name": "category_name", "data_type": "nvarchar" },
      { "name": "list_price", "data_type": "decimal", "sample_values": ["19.95", "24.00"] },
      { "name": "currency_code", "data_type": "nvarchar", "sample_values": ["USD"] },
      { "name": "approval_status", "data_type": "nvarchar", "sample_values": ["approved"] },
      { "name": "modified_at", "data_type": "datetime2" },
      { "name": "is_deleted", "data_type": "bit" }
    ]
  }
}
'@

curl.exe -s -X POST "$env:SEARCH_ENRICHMENT_BASE_URL/mcp/fabric-search-ingestion/discover_source" `
  -H "Content-Type: application/json" `
  -d $payload
```

### 6. Build And Review The Mapping Plan

```powershell
curl.exe -s -X POST "$env:SEARCH_ENRICHMENT_BASE_URL/mcp/fabric-search-ingestion/build_mapping_plan" `
  -H "Content-Type: application/json" `
  -d $payload
```

Before continuing, check:

| Response field | Accept when |
| --- | --- |
| `status` | `ok` |
| `mapping_plan.confidence` | High enough for your data, usually above `0.7` |
| `mapping_plan.mappings` | `id`, `sku`, `name`, `description`, and `content` are mapped |
| `governance.status` | `configured`, or the source is already an approved-only view |
| `warnings` | Understood and acceptable |

### 7. Build The Search Resources Without Creating Them

This is the dry run. It redacts connection strings and shows the exact index, skillset, data source, and indexer payloads.

```powershell
curl.exe -s -X POST "$env:SEARCH_ENRICHMENT_BASE_URL/mcp/fabric-search-ingestion/build_search_resources" `
  -H "Content-Type: application/json" `
  -d $payload
```

Confirm the generated payload includes:

| Payload | Expected detail |
| --- | --- |
| `resources.index.fields` | `id`, `sku`, `name`, `content`, facets, enrichment fields, and `content_vector` |
| `resources.index.vectorSearch` | HNSW cosine profile |
| `resources.index.semantic` | Title `name`; content `content`, `enriched_description`, `description` |
| `resources.skillset.skills` | One Azure OpenAI Embedding skill over `/document/content` |
| `resources.indexer.outputFieldMappings` | `/document/embedding/*` to `content_vector` |

### 8. Provision The Skillset, Index, Data Source, And Indexer

Run this only after the dry run looks correct:

```powershell
curl.exe -s -X POST "$env:SEARCH_ENRICHMENT_BASE_URL/mcp/fabric-search-ingestion/provision_search_resources" `
  -H "Content-Type: application/json" `
  -d $payload
```

Successful output has `status: ok` and one `ok` entry for each resource type: `index`, `skillset`, `data_source`, and `indexer`.

### 9. Run The Indexer

```powershell
curl.exe -s -X POST "$env:SEARCH_ENRICHMENT_BASE_URL/mcp/fabric-search-ingestion/run_indexer" `
  -H "Content-Type: application/json" `
  -d "{}"
```

Expected output has `status: accepted` or `status: ok`.

### 10. Verify The Index

Check index stats through the existing AI Search indexing MCP tool:

```powershell
curl.exe -s -X POST "$env:SEARCH_ENRICHMENT_BASE_URL/mcp/ai-search-indexing/get_index_stats" `
  -H "Content-Type: application/json" `
  -d '{ "index_name": "catalog-products" }'
```

Then confirm `ecommerce-catalog-search` uses the same index values:

```powershell
azd env get-values -e dev | Select-String "AI_SEARCH_INDEX|AI_SEARCH_VECTOR_INDEX|AI_SEARCH_VECTOR_FIELD"
```

For this standalone skillset path, the expected catalog-search values are:

```text
AI_SEARCH_INDEX=catalog-products
AI_SEARCH_VECTOR_INDEX=catalog-products
AI_SEARCH_VECTOR_FIELD=content_vector
```

### 11. If Something Goes Wrong

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `fabric_sql_driver_unavailable` | Runtime image lacks SQL ODBC driver or `pyodbc` | Use offline metadata payload, or add the driver before live discovery |
| `unsupported_onelake_table_location` | Path points at `Tables/` | Use Fabric SQL source or materialize supported Files content |
| `embedding_configuration_missing` | Embedding env vars missing | Set `EMBEDDING_RESOURCE_URI` and `EMBEDDING_DEPLOYMENT_NAME` |
| `permission_error` | Managed identity lacks Search or Fabric access | Grant Search resource provisioning roles and Fabric source read permissions |
| Indexer runs but zero docs appear | Source table empty, approval view filters all rows, or wrong table/view | Query the Fabric source directly and re-check `FABRIC_SQL_TABLE` |

Rollback is resource-specific. If you created the wrong indexer or data source, delete or recreate those Azure AI Search resources in the Search service. Do not change Product Truth Layer records to fix a search-only ingestion mistake.

## Governance Notes

The mapping/provisioning responses include an approval signal and explicitly report that truth lifecycle state was not mutated. For production catalog indexing, prefer an approved-only Fabric SQL view or configure `FABRIC_APPROVAL_COLUMN` and `FABRIC_APPROVAL_ACCEPTED_VALUES` so operators can verify the source governance signal before provisioning.

Set `AI_SEARCH_INDEX` and `AI_SEARCH_VECTOR_INDEX` to the same name when Fabric ingestion owns the unified hybrid catalog index. The generated index includes `content_vector` by default, HNSW cosine vector search, semantic ranking fields, and a single Azure OpenAI Embedding skill over `/document/content` whose dimensions match `EMBEDDING_DIMENSIONS`. Product-row ingestion intentionally avoids Text Split so each catalog product remains one search document with one vector.
