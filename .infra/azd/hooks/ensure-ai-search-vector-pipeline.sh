#!/usr/bin/env sh
set -eu

REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
RESOURCE_GROUP="${1:-${AZURE_RESOURCE_GROUP:-}}"
SEARCH_SERVICE_NAME="${2:-${AI_SEARCH_NAME:-}}"
VECTOR_INDEX_NAME="${3:-${AI_SEARCH_VECTOR_INDEX:-}}"
INDEXER_NAME="${4:-${AI_SEARCH_INDEXER_NAME:-}}"
EMBEDDING_DEPLOYMENT_NAME="${5:-${EMBEDDING_DEPLOYMENT_NAME:-}}"

resolve_from_azd_env() {
  KEY_PATTERN="$1"
  if [ -z "${AZURE_ENV_NAME:-}" ]; then
    return 0
  fi

  ENV_FILE="$REPO_ROOT/.azure/$AZURE_ENV_NAME/.env"
  if [ ! -f "$ENV_FILE" ]; then
    return 0
  fi

  grep -E "^(${KEY_PATTERN})=" "$ENV_FILE" | head -n 1 | cut -d '=' -f2- | tr -d '"' || true
}

if [ -z "$RESOURCE_GROUP" ]; then
  RESOURCE_GROUP="$(resolve_from_azd_env 'AZURE_RESOURCE_GROUP|resourceGroupName')"
fi

if [ -z "$SEARCH_SERVICE_NAME" ]; then
  SEARCH_SERVICE_NAME="$(resolve_from_azd_env 'AI_SEARCH_NAME|aiSearchName')"
fi

if [ -z "$VECTOR_INDEX_NAME" ]; then
  VECTOR_INDEX_NAME="$(resolve_from_azd_env 'AI_SEARCH_VECTOR_INDEX|aiSearchVectorIndexName')"
fi

if [ -z "$INDEXER_NAME" ]; then
  INDEXER_NAME="$(resolve_from_azd_env 'AI_SEARCH_INDEXER_NAME|aiSearchIndexerName')"
fi

if [ -z "$EMBEDDING_DEPLOYMENT_NAME" ]; then
  EMBEDDING_DEPLOYMENT_NAME="$(resolve_from_azd_env 'EMBEDDING_DEPLOYMENT_NAME|embeddingDeploymentName')"
fi

if [ -z "$RESOURCE_GROUP" ]; then
  echo 'Resource group could not be resolved. Set AZURE_RESOURCE_GROUP or run inside an azd environment.' >&2
  exit 1
fi

if [ -z "$SEARCH_SERVICE_NAME" ]; then
  SEARCH_SERVICE_NAME="$(az resource list --resource-group "$RESOURCE_GROUP" --resource-type Microsoft.Search/searchServices --query '[0].name' -o tsv 2>/dev/null || true)"
fi

if [ -z "$SEARCH_SERVICE_NAME" ]; then
  echo 'Azure AI Search service name could not be resolved. Set AI_SEARCH_NAME.' >&2
  exit 1
fi

[ -n "$VECTOR_INDEX_NAME" ] || VECTOR_INDEX_NAME='product_search_index'
[ -n "$INDEXER_NAME" ] || INDEXER_NAME='search-enriched-products-indexer'
[ -n "$EMBEDDING_DEPLOYMENT_NAME" ] || EMBEDDING_DEPLOYMENT_NAME='text-embedding-3-large'

DATA_SOURCE_NAME='search-enriched-products-datasource'
SKILLSET_NAME='search-enriched-products-skillset'

echo "Ensuring AI Search vector pipeline resources on '${SEARCH_SERVICE_NAME}' (RG: ${RESOURCE_GROUP})"

attempt=1
SERVICE_ID=''
while [ "$attempt" -le 18 ]; do
  SERVICE_ID="$(az resource show --resource-group "$RESOURCE_GROUP" --resource-type Microsoft.Search/searchServices --name "$SEARCH_SERVICE_NAME" --query id -o tsv 2>/dev/null || true)"
  if [ -n "$SERVICE_ID" ]; then
    break
  fi

  if [ "$attempt" -eq 18 ]; then
    echo "Azure AI Search service '${SEARCH_SERVICE_NAME}' was not reachable after waiting for postprovision readiness." >&2
    exit 1
  fi

  attempt=$((attempt + 1))
  sleep 10
done

SEARCH_ENDPOINT="$(az resource show --ids "$SERVICE_ID" --query properties.endpoint -o tsv)"
ADMIN_KEY="$(az rest --only-show-errors --method post --uri "https://management.azure.com${SERVICE_ID}/listAdminKeys?api-version=2022-09-01" --query primaryKey -o tsv)"

COSMOS_ACCOUNT_URI="$(resolve_from_azd_env 'COSMOS_ACCOUNT_URI|cosmosEndpoint')"
COSMOS_DATABASE="$(resolve_from_azd_env 'COSMOS_DATABASE|databaseName')"
[ -n "$COSMOS_DATABASE" ] || COSMOS_DATABASE='holiday-peak-db'

COSMOS_ACCOUNT_NAME=''
if [ -n "$COSMOS_ACCOUNT_URI" ]; then
  COSMOS_ACCOUNT_NAME="$(printf '%s' "$COSMOS_ACCOUNT_URI" | sed -E 's#https://([^\.]+)\.documents\.azure\.com/?#\1#')"
fi
if [ -z "$COSMOS_ACCOUNT_NAME" ]; then
  COSMOS_ACCOUNT_NAME="$(az cosmosdb list --resource-group "$RESOURCE_GROUP" --query '[0].name' -o tsv 2>/dev/null || true)"
fi
if [ -z "$COSMOS_ACCOUNT_NAME" ]; then
  echo 'Cosmos DB account could not be resolved for AI Search data source creation.' >&2
  exit 1
fi

COSMOS_CONNECTION_STRING="$(az cosmosdb keys list --resource-group "$RESOURCE_GROUP" --name "$COSMOS_ACCOUNT_NAME" --type connection-strings --query 'connectionStrings[0].connectionString' -o tsv)"
if [ -z "$COSMOS_CONNECTION_STRING" ]; then
  echo "Failed to resolve Cosmos DB connection string for account '${COSMOS_ACCOUNT_NAME}'." >&2
  exit 1
fi

PROJECT_ENDPOINT_VALUE="$(resolve_from_azd_env 'PROJECT_ENDPOINT')"
if [ -z "$PROJECT_ENDPOINT_VALUE" ]; then
  AI_SERVICES_NAME_VALUE="$(resolve_from_azd_env 'AI_SERVICES_NAME|aiServicesName')"
  if [ -n "$AI_SERVICES_NAME_VALUE" ]; then
    PROJECT_ENDPOINT_VALUE="https://${AI_SERVICES_NAME_VALUE}.cognitiveservices.azure.com"
  fi
fi
if [ -z "$PROJECT_ENDPOINT_VALUE" ]; then
  echo 'Foundry/Azure OpenAI endpoint could not be resolved. Set PROJECT_ENDPOINT or AI_SERVICES_NAME.' >&2
  exit 1
fi

DATA_SOURCE_URI="${SEARCH_ENDPOINT}/datasources('${DATA_SOURCE_NAME}')?api-version=2024-07-01"
SKILLSET_URI="${SEARCH_ENDPOINT}/skillsets('${SKILLSET_NAME}')?api-version=2024-07-01"
INDEX_URI="${SEARCH_ENDPOINT}/indexes('${VECTOR_INDEX_NAME}')?api-version=2024-07-01"
INDEXER_URI="${SEARCH_ENDPOINT}/indexers('${INDEXER_NAME}')?api-version=2024-07-01"

DATA_SOURCE_DEFINITION=$(cat <<EOF
{"name":"${DATA_SOURCE_NAME}","type":"cosmosdb","credentials":{"connectionString":"${COSMOS_CONNECTION_STRING}"},"container":{"name":"search_enriched_products"},"dataChangeDetectionPolicy":{"@odata.type":"#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy","highWaterMarkColumnName":"_ts"}}
EOF
)

SKILLSET_DEFINITION=$(cat <<EOF
{"name":"${SKILLSET_NAME}","description":"Split and embed enriched product descriptions.","skills":[{"@odata.type":"#Microsoft.Skills.Text.SplitSkill","name":"#splitDescription","context":"/document","textSplitMode":"pages","maximumPageLength":3000,"pageOverlapLength":200,"maximumPagesToTake":1,"inputs":[{"name":"text","source":"/document/enriched_description"}],"outputs":[{"name":"textItems","targetName":"description_chunks"}]},{"@odata.type":"#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill","name":"#descriptionEmbedding","context":"/document","resourceUri":"${PROJECT_ENDPOINT_VALUE}","deploymentId":"${EMBEDDING_DEPLOYMENT_NAME}","modelName":"${EMBEDDING_DEPLOYMENT_NAME}","dimensions":3072,"inputs":[{"name":"text","source":"/document/enriched_description"}],"outputs":[{"name":"embedding","targetName":"description_vector"}]}]}
EOF
)

INDEX_DEFINITION=$(cat <<EOF
{"name":"${VECTOR_INDEX_NAME}","fields":[{"name":"id","type":"Edm.String","key":true,"filterable":true},{"name":"entity_id","type":"Edm.String","filterable":true},{"name":"sku","type":"Edm.String","filterable":true,"searchable":true},{"name":"name","type":"Edm.String","searchable":true,"analyzer":"en.microsoft"},{"name":"brand","type":"Edm.String","filterable":true,"facetable":true,"searchable":true},{"name":"category","type":"Edm.String","filterable":true,"facetable":true},{"name":"description","type":"Edm.String","searchable":true,"analyzer":"en.microsoft"},{"name":"price","type":"Edm.Double","filterable":true,"sortable":true,"facetable":true},{"name":"use_cases","type":"Collection(Edm.String)","filterable":true,"searchable":true},{"name":"complementary_products","type":"Collection(Edm.String)","filterable":true},{"name":"substitute_products","type":"Collection(Edm.String)","filterable":true},{"name":"search_keywords","type":"Collection(Edm.String)","searchable":true},{"name":"enriched_description","type":"Edm.String","searchable":true},{"name":"description_vector","type":"Collection(Edm.Single)","searchable":true,"retrievable":true,"dimensions":3072,"vectorSearchProfile":"default-vector-profile"}],"vectorSearch":{"algorithms":[{"name":"hnsw-algo","kind":"hnsw","hnswParameters":{"m":4,"efConstruction":400,"efSearch":500,"metric":"cosine"}}],"profiles":[{"name":"default-vector-profile","algorithmConfigurationName":"hnsw-algo","vectorizer":"text-embedding-vectorizer"}],"vectorizers":[{"name":"text-embedding-vectorizer","kind":"azureOpenAI","azureOpenAIParameters":{"modelName":"${EMBEDDING_DEPLOYMENT_NAME}","deploymentId":"${EMBEDDING_DEPLOYMENT_NAME}","resourceUri":"${PROJECT_ENDPOINT_VALUE}"}}]},"semantic":{"configurations":[{"name":"default-semantic","prioritizedFields":{"titleField":{"fieldName":"name"},"contentFields":[{"fieldName":"enriched_description"},{"fieldName":"description"}],"keywordsFields":[{"fieldName":"search_keywords"},{"fieldName":"use_cases"}]}}]}}
EOF
)

INDEXER_DEFINITION=$(cat <<EOF
{"name":"${INDEXER_NAME}","dataSourceName":"${DATA_SOURCE_NAME}","targetIndexName":"${VECTOR_INDEX_NAME}","skillsetName":"${SKILLSET_NAME}","schedule":{"interval":"PT5M"},"parameters":{"batchSize":100,"maxFailedItems":10,"maxFailedItemsPerBatch":5,"configuration":{"parsingMode":"json","dataToExtract":"contentAndMetadata"}},"fieldMappings":[{"sourceFieldName":"entity_id","targetFieldName":"entity_id"},{"sourceFieldName":"sku","targetFieldName":"sku"},{"sourceFieldName":"name","targetFieldName":"name"},{"sourceFieldName":"brand","targetFieldName":"brand"},{"sourceFieldName":"category","targetFieldName":"category"},{"sourceFieldName":"description","targetFieldName":"description"},{"sourceFieldName":"price","targetFieldName":"price"},{"sourceFieldName":"use_cases","targetFieldName":"use_cases"},{"sourceFieldName":"complementary_products","targetFieldName":"complementary_products"},{"sourceFieldName":"substitute_products","targetFieldName":"substitute_products"},{"sourceFieldName":"search_keywords","targetFieldName":"search_keywords"},{"sourceFieldName":"enriched_description","targetFieldName":"enriched_description"}],"outputFieldMappings":[{"sourceFieldName":"/document/description_vector","targetFieldName":"description_vector"}]}
EOF
)

put_with_retry() {
  RESOURCE_NAME="$1"
  RESOURCE_URI="$2"
  RESOURCE_BODY="$3"

  attempt=1
  while [ "$attempt" -le 12 ]; do
    if curl -fsS -X PUT -H "api-key: ${ADMIN_KEY}" -H 'Content-Type: application/json' --data "$RESOURCE_BODY" "$RESOURCE_URI" >/dev/null; then
      echo "Azure AI Search resource '${RESOURCE_NAME}' is ready."
      return 0
    fi

    if [ "$attempt" -eq 12 ]; then
      echo "Failed to create or update Azure AI Search resource '${RESOURCE_NAME}'." >&2
      exit 1
    fi

    attempt=$((attempt + 1))
    sleep 10
  done
}

put_with_retry "$DATA_SOURCE_NAME" "$DATA_SOURCE_URI" "$DATA_SOURCE_DEFINITION"
put_with_retry "$SKILLSET_NAME" "$SKILLSET_URI" "$SKILLSET_DEFINITION"
put_with_retry "$VECTOR_INDEX_NAME" "$INDEX_URI" "$INDEX_DEFINITION"
put_with_retry "$INDEXER_NAME" "$INDEXER_URI" "$INDEXER_DEFINITION"

echo 'Azure AI Search vector indexing pipeline is ready.'
