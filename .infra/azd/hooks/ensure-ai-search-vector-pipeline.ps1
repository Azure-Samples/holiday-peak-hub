#!/usr/bin/env pwsh
<#!
.SYNOPSIS
    Ensures Azure AI Search vector indexing resources exist after provisioning.

.DESCRIPTION
    Creates or updates AI Search data source, skillset, vector index, and indexer
    for Cosmos DB container `search_enriched_products`.
#>
param(
    [string]$ResourceGroup = $env:AZURE_RESOURCE_GROUP,
    [string]$SearchServiceName = $env:AI_SEARCH_NAME,
    [string]$VectorIndexName = $env:AI_SEARCH_VECTOR_INDEX,
    [string]$IndexerName = $env:AI_SEARCH_INDEXER_NAME,
    [string]$EmbeddingDeploymentName = $env:EMBEDDING_DEPLOYMENT_NAME
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path "$PSScriptRoot\..\..\.."

function Get-EnvValueFromFile {
    param([string]$FilePath, [string]$Key)
    if (-not (Test-Path $FilePath)) { return '' }
    foreach ($line in Get-Content $FilePath) {
        if ($line -match "^$Key=(.*)$") { return $Matches[1].Trim('"') }
    }
    return ''
}

function Resolve-FromAzdEnv {
    param([string[]]$Keys)
    if (-not $env:AZURE_ENV_NAME) { return '' }

    $envFile = Join-Path $repoRoot ".azure\$($env:AZURE_ENV_NAME)\.env"
    foreach ($key in $Keys) {
        $value = Get-EnvValueFromFile -FilePath $envFile -Key $key
        if ($value) { return $value }
    }

    return ''
}

if (-not $ResourceGroup) {
    $ResourceGroup = Resolve-FromAzdEnv -Keys @('AZURE_RESOURCE_GROUP', 'resourceGroupName')
}

if (-not $SearchServiceName) {
    $SearchServiceName = Resolve-FromAzdEnv -Keys @('AI_SEARCH_NAME', 'aiSearchName')
}

if (-not $VectorIndexName) {
    $VectorIndexName = Resolve-FromAzdEnv -Keys @('AI_SEARCH_VECTOR_INDEX', 'aiSearchVectorIndexName')
}

if (-not $IndexerName) {
    $IndexerName = Resolve-FromAzdEnv -Keys @('AI_SEARCH_INDEXER_NAME', 'aiSearchIndexerName')
}

if (-not $EmbeddingDeploymentName) {
    $EmbeddingDeploymentName = Resolve-FromAzdEnv -Keys @('EMBEDDING_DEPLOYMENT_NAME', 'embeddingDeploymentName')
}

if (-not $ResourceGroup) {
    Write-Error 'Resource group could not be resolved. Set AZURE_RESOURCE_GROUP or run inside an azd environment.'
    exit 1
}

if (-not $SearchServiceName) {
    $SearchServiceName = az resource list --resource-group $ResourceGroup --resource-type Microsoft.Search/searchServices --query '[0].name' -o tsv 2>$null
}

if (-not $SearchServiceName) {
    Write-Error 'Azure AI Search service name could not be resolved. Set AI_SEARCH_NAME.'
    exit 1
}

if (-not $VectorIndexName) {
    $VectorIndexName = 'product_search_index'
}

if (-not $IndexerName) {
    $IndexerName = 'search-enriched-products-indexer'
}

if (-not $EmbeddingDeploymentName) {
    $EmbeddingDeploymentName = 'text-embedding-3-large'
}

$dataSourceName = 'search-enriched-products-datasource'
$skillsetName = 'search-enriched-products-skillset'

Write-Host "Ensuring AI Search vector pipeline resources on '$SearchServiceName' (RG: $ResourceGroup)"

$serviceId = ''
for ($attempt = 1; $attempt -le 18; $attempt++) {
    $serviceId = az resource show --resource-group $ResourceGroup --resource-type Microsoft.Search/searchServices --name $SearchServiceName --query id -o tsv 2>$null
    if ($LASTEXITCODE -eq 0 -and $serviceId) {
        break
    }

    if ($attempt -eq 18) {
        Write-Error "Azure AI Search service '$SearchServiceName' was not reachable after waiting for postprovision readiness."
        exit 1
    }

    Start-Sleep -Seconds 10
}

$searchEndpoint = az resource show --ids $serviceId --query properties.endpoint -o tsv
$adminKey = az rest --only-show-errors --method post --uri "https://management.azure.com$serviceId/listAdminKeys?api-version=2022-09-01" --query primaryKey -o tsv

$cosmosAccountUri = Resolve-FromAzdEnv -Keys @('COSMOS_ACCOUNT_URI', 'cosmosEndpoint')
$cosmosDatabase = Resolve-FromAzdEnv -Keys @('COSMOS_DATABASE', 'databaseName')
if (-not $cosmosAccountUri) {
    $cosmosAccountUri = az cosmosdb show --resource-group $ResourceGroup --name (Resolve-FromAzdEnv -Keys @('cosmosAccountName')) --query documentEndpoint -o tsv 2>$null
}
if (-not $cosmosDatabase) {
    $cosmosDatabase = 'holiday-peak-db'
}

$cosmosAccountName = ''
if ($cosmosAccountUri -match 'https://([^\.]+)\.documents\.azure\.com') {
    $cosmosAccountName = $Matches[1]
}
if (-not $cosmosAccountName) {
    $cosmosAccountName = az cosmosdb list --resource-group $ResourceGroup --query '[0].name' -o tsv 2>$null
}
if (-not $cosmosAccountName) {
    Write-Error 'Cosmos DB account could not be resolved for AI Search data source creation.'
    exit 1
}

$cosmosConnectionString = az cosmosdb keys list --resource-group $ResourceGroup --name $cosmosAccountName --type connection-strings --query 'connectionStrings[0].connectionString' -o tsv
if (-not $cosmosConnectionString) {
    Write-Error "Failed to resolve Cosmos DB connection string for account '$cosmosAccountName'."
    exit 1
}

$projectEndpoint = Resolve-FromAzdEnv -Keys @('PROJECT_ENDPOINT')
if (-not $projectEndpoint) {
    $aiServicesName = Resolve-FromAzdEnv -Keys @('AI_SERVICES_NAME', 'aiServicesName')
    if ($aiServicesName) {
        $projectEndpoint = "https://$aiServicesName.cognitiveservices.azure.com"
    }
}

if (-not $projectEndpoint) {
    Write-Error 'Foundry/Azure OpenAI endpoint could not be resolved. Set PROJECT_ENDPOINT or AI_SERVICES_NAME.'
    exit 1
}

$dataSourceUri = "$searchEndpoint/datasources('$dataSourceName')?api-version=2024-07-01"
$skillsetUri = "$searchEndpoint/skillsets('$skillsetName')?api-version=2024-07-01"
$indexUri = "$searchEndpoint/indexes('$VectorIndexName')?api-version=2024-07-01"
$indexerUri = "$searchEndpoint/indexers('$IndexerName')?api-version=2024-07-01"

$dataSourceDefinition = @{
    name = $dataSourceName
    type = 'cosmosdb'
    credentials = @{ connectionString = $cosmosConnectionString }
    container = @{ name = 'search_enriched_products' }
    dataChangeDetectionPolicy = @{ '@odata.type' = '#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy'; highWaterMarkColumnName = '_ts' }
} | ConvertTo-Json -Depth 12 -Compress

$skillsetDefinition = @{
    name = $skillsetName
    description = 'Split and embed enriched product descriptions.'
    skills = @(
        @{
            '@odata.type' = '#Microsoft.Skills.Text.SplitSkill'
            name = '#splitDescription'
            context = '/document'
            textSplitMode = 'pages'
            maximumPageLength = 3000
            pageOverlapLength = 200
            maximumPagesToTake = 1
            inputs = @(
                @{ name = 'text'; source = '/document/enriched_description' }
            )
            outputs = @(
                @{ name = 'textItems'; targetName = 'description_chunks' }
            )
        }
        @{
            '@odata.type' = '#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill'
            name = '#descriptionEmbedding'
            context = '/document'
            resourceUri = $projectEndpoint
            deploymentId = $EmbeddingDeploymentName
            modelName = $EmbeddingDeploymentName
            dimensions = 3072
            inputs = @(
                @{ name = 'text'; source = '/document/enriched_description' }
            )
            outputs = @(
                @{ name = 'embedding'; targetName = 'description_vector' }
            )
        }
    )
} | ConvertTo-Json -Depth 12 -Compress

$indexDefinition = @{
    name = $VectorIndexName
    fields = @(
        @{ name = 'id'; type = 'Edm.String'; key = $true; filterable = $true }
        @{ name = 'entity_id'; type = 'Edm.String'; filterable = $true }
        @{ name = 'sku'; type = 'Edm.String'; searchable = $true; filterable = $true }
        @{ name = 'name'; type = 'Edm.String'; searchable = $true; analyzer = 'en.microsoft' }
        @{ name = 'brand'; type = 'Edm.String'; searchable = $true; filterable = $true; facetable = $true }
        @{ name = 'category'; type = 'Edm.String'; filterable = $true; facetable = $true }
        @{ name = 'description'; type = 'Edm.String'; searchable = $true; analyzer = 'en.microsoft' }
        @{ name = 'price'; type = 'Edm.Double'; filterable = $true; sortable = $true; facetable = $true }
        @{ name = 'use_cases'; type = 'Collection(Edm.String)'; searchable = $true; filterable = $true }
        @{ name = 'complementary_products'; type = 'Collection(Edm.String)'; filterable = $true }
        @{ name = 'substitute_products'; type = 'Collection(Edm.String)'; filterable = $true }
        @{ name = 'search_keywords'; type = 'Collection(Edm.String)'; searchable = $true }
        @{ name = 'enriched_description'; type = 'Edm.String'; searchable = $true }
        @{ name = 'description_vector'; type = 'Collection(Edm.Single)'; searchable = $true; retrievable = $true; dimensions = 3072; vectorSearchProfile = 'default-vector-profile' }
    )
    vectorSearch = @{
        algorithms = @(
            @{ name = 'hnsw-algo'; kind = 'hnsw'; hnswParameters = @{ m = 4; efConstruction = 400; efSearch = 500; metric = 'cosine' } }
        )
        profiles = @(
            @{ name = 'default-vector-profile'; algorithmConfigurationName = 'hnsw-algo'; vectorizer = 'text-embedding-vectorizer' }
        )
        vectorizers = @(
            @{ name = 'text-embedding-vectorizer'; kind = 'azureOpenAI'; azureOpenAIParameters = @{ modelName = $EmbeddingDeploymentName; deploymentId = $EmbeddingDeploymentName; resourceUri = $projectEndpoint } }
        )
    }
    semantic = @{
        configurations = @(
            @{ name = 'default-semantic'; prioritizedFields = @{ titleField = @{ fieldName = 'name' }; contentFields = @(@{ fieldName = 'enriched_description' }, @{ fieldName = 'description' }); keywordsFields = @(@{ fieldName = 'search_keywords' }, @{ fieldName = 'use_cases' }) } }
        )
    }
} | ConvertTo-Json -Depth 20 -Compress

$indexerDefinition = @{
    name = $IndexerName
    dataSourceName = $dataSourceName
    targetIndexName = $VectorIndexName
    skillsetName = $skillsetName
    schedule = @{ interval = 'PT5M' }
    parameters = @{
        batchSize = 100
        maxFailedItems = 10
        maxFailedItemsPerBatch = 5
        configuration = @{
            parsingMode = 'json'
            dataToExtract = 'contentAndMetadata'
        }
    }
    fieldMappings = @(
        @{ sourceFieldName = 'entity_id'; targetFieldName = 'entity_id' }
        @{ sourceFieldName = 'sku'; targetFieldName = 'sku' }
        @{ sourceFieldName = 'name'; targetFieldName = 'name' }
        @{ sourceFieldName = 'brand'; targetFieldName = 'brand' }
        @{ sourceFieldName = 'category'; targetFieldName = 'category' }
        @{ sourceFieldName = 'description'; targetFieldName = 'description' }
        @{ sourceFieldName = 'price'; targetFieldName = 'price' }
        @{ sourceFieldName = 'use_cases'; targetFieldName = 'use_cases' }
        @{ sourceFieldName = 'complementary_products'; targetFieldName = 'complementary_products' }
        @{ sourceFieldName = 'substitute_products'; targetFieldName = 'substitute_products' }
        @{ sourceFieldName = 'search_keywords'; targetFieldName = 'search_keywords' }
        @{ sourceFieldName = 'enriched_description'; targetFieldName = 'enriched_description' }
    )
    outputFieldMappings = @(
        @{ sourceFieldName = '/document/description_vector'; targetFieldName = 'description_vector' }
    )
} | ConvertTo-Json -Depth 16 -Compress

$headers = @{ 'api-key' = $adminKey; 'Content-Type' = 'application/json' }

function Invoke-SearchPut {
    param([string]$Name, [string]$Uri, [string]$Body)
    for ($attempt = 1; $attempt -le 12; $attempt++) {
        try {
            Invoke-RestMethod -Method Put -Uri $Uri -Headers $headers -Body $Body | Out-Null
            Write-Host "Azure AI Search resource '$Name' is ready."
            return
        }
        catch {
            if ($attempt -eq 12) {
                Write-Error "Failed to create or update Azure AI Search resource '$Name': $($_.Exception.Message)"
                exit 1
            }
            Start-Sleep -Seconds 10
        }
    }
}

Invoke-SearchPut -Name $dataSourceName -Uri $dataSourceUri -Body $dataSourceDefinition
Invoke-SearchPut -Name $skillsetName -Uri $skillsetUri -Body $skillsetDefinition
Invoke-SearchPut -Name $VectorIndexName -Uri $indexUri -Body $indexDefinition
Invoke-SearchPut -Name $IndexerName -Uri $indexerUri -Body $indexerDefinition

Write-Host 'Azure AI Search vector indexing pipeline is ready.'
