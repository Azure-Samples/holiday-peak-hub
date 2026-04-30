targetScope = 'resourceGroup'

@description('Project name used for alert naming.')
param projectName string

@description('Environment name used for alert naming.')
param environment string

@description('Azure region for alerts resources.')
param location string = resourceGroup().location

@description('Resource ID of Log Analytics workspace used for scheduled query alerts.')
param monitoringWorkspaceResourceId string

@description('Optional email receiver for action group notifications.')
param alertEmailAddress string = ''

@secure()
@description('Optional Microsoft Teams incoming webhook URL for action group notifications.')
param teamsWebhookUrl string = ''

@description('Resource ID of Azure Cosmos DB account.')
param cosmosResourceId string

@description('Resource ID of Azure Cache for Redis.')
param redisResourceId string

@description('Resource ID of PostgreSQL Flexible Server.')
param postgresResourceId string

@description('Resource ID of Event Hubs namespace.')
param eventHubsNamespaceResourceId string

@description('Resource ID of AKS cluster.')
param aksResourceId string

@description('Resource ID of API Management service.')
param apimResourceId string

@description('Resource ID of Azure AI Search service.')
param aiSearchResourceId string

@description('Resource ID of Storage Account used by Blob Storage.')
param storageAccountResourceId string

@description('Indexer name to monitor for AI Search failed document processing. Use * to include all indexers.')
param aiSearchIndexerName string = '*'

var blobServiceResourceId = '${storageAccountResourceId}/blobServices/default'

var actionGroupShortName = take(replace('${projectName}${environment}', '-', ''), 12)

var uiProxyWarn502Query = '''
let criticalPaths = dynamic([
  '/api/health',
  '/api/products',
  '/api/categories',
  '/api/admin/agent-activity',
  '/api/admin/enrichment-monitor'
]);
let proxyRequests =
  union isfuzzy=true
    (
      AppRequests
      | project
          eventTime = TimeGenerated,
          requestUrl = tostring(Url),
          requestName = tostring(Name),
          statusCode = tostring(ResultCode),
          dimensions = todynamic(Properties)
    ),
    (
      requests
      | project
          eventTime = timestamp,
          requestUrl = tostring(url),
          requestName = tostring(name),
          statusCode = tostring(resultCode),
          dimensions = todynamic(customDimensions)
    );
proxyRequests
| where eventTime > ago(10m)
| where requestUrl has '/api/' or requestName has '/api/'
| extend normalizedNamePath = iif(requestName has '/api/', tostring(split(requestName, ' ')[1]), requestName)
| extend upstreamPath = coalesce(
    tostring(dimensions.upstreamPath),
    tostring(dimensions['proxy.attemptedPath']),
    tostring(dimensions.attemptedPath),
    tostring(parse_url(requestUrl).Path),
    normalizedNamePath
  )
| where isnotempty(upstreamPath) and upstreamPath in~ (criticalPaths)
| extend status = statusCode
| extend failureKind = coalesce(
    tostring(dimensions.failureKind),
    tostring(dimensions['proxy.failureKind']),
    tostring(dimensions['x-holiday-peak-proxy-failure-kind']),
    'unknown'
  )
| extend sourceKey = coalesce(
    tostring(dimensions.sourceKey),
    tostring(dimensions['proxy.sourceKey']),
    tostring(dimensions['x-holiday-peak-proxy-source']),
    'unknown'
  )
| extend fallbackToken = coalesce(
    tostring(dimensions.fallbackUsed),
    tostring(dimensions['x-holiday-peak-proxy-fallback']),
    ''
  )
| extend fallbackUsed = iff(tolower(fallbackToken) in ('true', '1') or isnotempty(fallbackToken), 'true', 'false')
| summarize requestCount=count(), failureCount=countif(status == '502') by upstreamPath, failureKind, sourceKey, fallbackUsed
| extend status = '502'
| extend failureRatePct = iff(requestCount == 0, 0.0, todouble(failureCount) * 100.0 / todouble(requestCount))
| where requestCount >= 30 and failureRatePct >= 3.0
| extend breach = failureRatePct
| project breach, failureRatePct, requestCount, failureCount, upstreamPath, failureKind, sourceKey, status, fallbackUsed
'''

var uiProxyCritical502Query = '''
let criticalPaths = dynamic([
  '/api/health',
  '/api/products',
  '/api/categories',
  '/api/admin/agent-activity',
  '/api/admin/enrichment-monitor'
]);
let proxyRequests =
  union isfuzzy=true
    (
      AppRequests
      | project
          eventTime = TimeGenerated,
          requestUrl = tostring(Url),
          requestName = tostring(Name),
          statusCode = tostring(ResultCode),
          dimensions = todynamic(Properties)
    ),
    (
      requests
      | project
          eventTime = timestamp,
          requestUrl = tostring(url),
          requestName = tostring(name),
          statusCode = tostring(resultCode),
          dimensions = todynamic(customDimensions)
    );
proxyRequests
| where eventTime > ago(5m)
| where requestUrl has '/api/' or requestName has '/api/'
| extend normalizedNamePath = iif(requestName has '/api/', tostring(split(requestName, ' ')[1]), requestName)
| extend upstreamPath = coalesce(
    tostring(dimensions.upstreamPath),
    tostring(dimensions['proxy.attemptedPath']),
    tostring(dimensions.attemptedPath),
    tostring(parse_url(requestUrl).Path),
    normalizedNamePath
  )
| where isnotempty(upstreamPath) and upstreamPath in~ (criticalPaths)
| extend status = statusCode
| extend failureKind = coalesce(
    tostring(dimensions.failureKind),
    tostring(dimensions['proxy.failureKind']),
    tostring(dimensions['x-holiday-peak-proxy-failure-kind']),
    'unknown'
  )
| extend sourceKey = coalesce(
    tostring(dimensions.sourceKey),
    tostring(dimensions['proxy.sourceKey']),
    tostring(dimensions['x-holiday-peak-proxy-source']),
    'unknown'
  )
| extend fallbackToken = coalesce(
    tostring(dimensions.fallbackUsed),
    tostring(dimensions['x-holiday-peak-proxy-fallback']),
    ''
  )
| extend fallbackUsed = iff(tolower(fallbackToken) in ('true', '1') or isnotempty(fallbackToken), 'true', 'false')
| summarize requestCount=count(), failureCount=countif(status == '502') by upstreamPath, failureKind, sourceKey, fallbackUsed
| extend status = '502'
| extend failureRatePct = iff(requestCount == 0, 0.0, todouble(failureCount) * 100.0 / todouble(requestCount))
| where requestCount >= 50 and failureRatePct >= 8.0
| extend breach = failureRatePct
| project breach, failureRatePct, requestCount, failureCount, upstreamPath, failureKind, sourceKey, status, fallbackUsed
'''

resource actionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = {
  name: '${projectName}-${environment}-ops-ag'
  location: 'global'
  properties: {
    enabled: true
    groupShortName: actionGroupShortName
    emailReceivers: empty(alertEmailAddress) ? [] : [
      {
        name: 'platform-email'
        emailAddress: alertEmailAddress
        useCommonAlertSchema: true
      }
    ]
    webhookReceivers: empty(teamsWebhookUrl) ? [] : [
      {
        name: 'teams-webhook'
        serviceUri: teamsWebhookUrl
        useCommonAlertSchema: true
      }
    ]
  }
}

resource cosmosRuAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-cosmos-ru-high'
  location: 'global'
  properties: {
    description: 'Cosmos TotalRequestUnits average > 80 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      cosmosResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'CosmosRUConsumption'
          metricNamespace: 'Microsoft.DocumentDB/databaseAccounts'
          metricName: 'TotalRequestUnits'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource cosmos5xxAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-cosmos-5xx-high'
  location: 'global'
  properties: {
    description: 'Cosmos ServerSideRequests total > 5 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      cosmosResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'CosmosServerErrors'
          metricNamespace: 'Microsoft.DocumentDB/databaseAccounts'
          metricName: 'ServerSideRequests'
          operator: 'GreaterThan'
          threshold: 5
          timeAggregation: 'Total'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource cosmosLatencyAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-cosmos-latency-high'
  location: 'global'
  properties: {
    description: 'Cosmos TotalRequestLatency average > 200ms over PT15M (evaluated every PT5M).'
    severity: 3
    enabled: true
    scopes: [
      cosmosResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'CosmosLatency'
          metricNamespace: 'Microsoft.DocumentDB/databaseAccounts'
          metricName: 'TotalRequestLatency'
          operator: 'GreaterThan'
          threshold: 200
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource redisMemoryAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-redis-memory-high'
  location: 'global'
  properties: {
    description: 'Redis usedmemorypercentage average > 80 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      redisResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'RedisMemoryUsage'
          metricNamespace: 'Microsoft.Cache/Redis'
          metricName: 'usedmemorypercentage'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource redisConnectionAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-redis-connections-failed'
  location: 'global'
  properties: {
    description: 'Redis errors total > 1 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      redisResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'RedisErrors'
          metricNamespace: 'Microsoft.Cache/Redis'
          metricName: 'errors'
          operator: 'GreaterThan'
          threshold: 1
          timeAggregation: 'Total'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource redisEvictionsAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-redis-evictions-high'
  location: 'global'
  properties: {
    description: 'Redis evictedkeys total > 0 over PT15M (evaluated every PT5M).'
    severity: 3
    enabled: true
    scopes: [
      redisResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'RedisEvictedKeys'
          metricNamespace: 'Microsoft.Cache/Redis'
          metricName: 'evictedkeys'
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Total'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource postgresCpuAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-postgres-cpu-high'
  location: 'global'
  properties: {
    description: 'PostgreSQL cpu_percent average > 80 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      postgresResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'PostgresCPUPercent'
          metricNamespace: 'Microsoft.DBforPostgreSQL/flexibleServers'
          metricName: 'cpu_percent'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource postgresStorageAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-postgres-storage-high'
  location: 'global'
  properties: {
    description: 'PostgreSQL storage_percent average > 85 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      postgresResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'PostgresStoragePercent'
          metricNamespace: 'Microsoft.DBforPostgreSQL/flexibleServers'
          metricName: 'storage_percent'
          operator: 'GreaterThan'
          threshold: 85
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource postgresLongQueryAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-postgres-long-queries'
  location: 'global'
  properties: {
    description: 'PostgreSQL long_running_queries average > 5 over PT15M (evaluated every PT5M).'
    severity: 3
    enabled: true
    scopes: [
      postgresResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'PostgresLongRunningQueries'
          metricNamespace: 'Microsoft.DBforPostgreSQL/flexibleServers'
          metricName: 'long_running_queries'
          operator: 'GreaterThan'
          threshold: 5
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource eventHubsThrottledAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-eventhubs-throttled'
  location: 'global'
  properties: {
    description: 'Event Hubs ThrottledRequests total > 0 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      eventHubsNamespaceResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'EventHubsThrottledRequests'
          metricNamespace: 'Microsoft.EventHub/namespaces'
          metricName: 'ThrottledRequests'
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Total'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource eventHubsAbandonedMessagesAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-eventhubs-abandoned'
  location: 'global'
  properties: {
    description: 'Event Hubs OutgoingMessages average < 1 over PT15M (evaluated every PT5M).'
    severity: 3
    enabled: true
    scopes: [
      eventHubsNamespaceResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'EventHubsAbandonedMessages'
          metricNamespace: 'Microsoft.EventHub/namespaces'
          metricName: 'OutgoingMessages'
          operator: 'LessThan'
          threshold: 1
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource eventHubsConsumerLagAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-eventhubs-consumer-lag'
  location: 'global'
  properties: {
    description: 'Event Hubs IncomingMessages total > 100000 over PT15M (evaluated every PT5M) as consumer lag proxy.'
    severity: 2
    enabled: true
    scopes: [
      eventHubsNamespaceResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'EventHubsIncomingMessagesHigh'
          metricNamespace: 'Microsoft.EventHub/namespaces'
          metricName: 'IncomingMessages'
          operator: 'GreaterThan'
          threshold: 100000
          timeAggregation: 'Total'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource aksNodeCpuAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-aks-node-cpu-high'
  location: 'global'
  properties: {
    description: 'AKS node_cpu_usage_percentage average > 80 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      aksResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'AksNodeCPUUsage'
          metricNamespace: 'Microsoft.ContainerService/managedClusters'
          metricName: 'node_cpu_usage_percentage'
          operator: 'GreaterThan'
          threshold: 80
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource aksPodRestartAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-aks-pod-restarts-high'
  location: 'global'
  properties: {
    description: 'AKS pod_restart_count total > 5 over PT15M (evaluated every PT5M).'
    severity: 3
    enabled: true
    scopes: [
      aksResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'AksPodRestartCount'
          metricNamespace: 'Microsoft.ContainerService/managedClusters'
          metricName: 'pod_restart_count'
          operator: 'GreaterThan'
          threshold: 5
          timeAggregation: 'Total'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource aksImagePullFailuresAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-aks-image-pull-failures'
  location: 'global'
  properties: {
    description: 'AKS image_pull_failed_count total > 0 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      aksResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'AksImagePullFailed'
          metricNamespace: 'Microsoft.ContainerService/managedClusters'
          metricName: 'image_pull_failed_count'
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Total'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource apimFailedRequestsAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-apim-failed-requests'
  location: 'global'
  properties: {
    description: 'APIM FailedRequests total > 10 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      apimResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'ApimFailedRequests'
          metricNamespace: 'Microsoft.ApiManagement/service'
          metricName: 'FailedRequests'
          operator: 'GreaterThan'
          threshold: 10
          timeAggregation: 'Total'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource apimLatencyAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-apim-latency-p95'
  location: 'global'
  properties: {
    description: 'APIM Duration average > 2000ms over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      apimResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'ApimDurationP95'
          metricNamespace: 'Microsoft.ApiManagement/service'
          metricName: 'Duration'
          operator: 'GreaterThan'
          threshold: 2000
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource apim5xxRateAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-apim-5xx-rate'
  location: 'global'
  properties: {
    description: 'APIM FailedRequests average > 1 over PT15M (evaluated every PT5M) as 5xx proxy.'
    severity: 2
    enabled: true
    scopes: [
      apimResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'ApimGateway5xxProxy'
          metricNamespace: 'Microsoft.ApiManagement/service'
          metricName: 'FailedRequests'
          operator: 'GreaterThan'
          threshold: 1
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource aiSearchIndexerFailuresAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-aisearch-indexer-failures'
  location: 'global'
  properties: {
    description: 'AI Search indexer failed document processing > 0 over PT15M (evaluated every PT5M).'
    severity: 2
    enabled: true
    scopes: [
      aiSearchResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'AiSearchFailedDocuments'
          metricNamespace: 'Microsoft.Search/searchServices'
          metricName: 'DocumentsProcessedCount'
          operator: 'GreaterThan'
          threshold: 0
          timeAggregation: 'Total'
          dimensions: [
            {
              name: 'Failed'
              operator: 'Include'
              values: [
                'true'
              ]
            }
            {
              name: 'IndexerName'
              operator: 'Include'
              values: [
                aiSearchIndexerName
              ]
            }
          ]
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource blobCapacityAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-blob-capacity-high'
  location: 'global'
  properties: {
    description: 'BlobCapacity > 500GB over PT1H (evaluated every PT1H).'
    severity: 3
    enabled: true
    scopes: [
      blobServiceResourceId
    ]
    evaluationFrequency: 'PT1H'
    windowSize: 'PT1H'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'BlobCapacityBytes'
          metricNamespace: 'Microsoft.Storage/storageAccounts/blobServices'
          metricName: 'BlobCapacity'
          operator: 'GreaterThan'
          threshold: 536870912000
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource blobUsedCapacityAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-blob-used-capacity-high'
  location: 'global'
  properties: {
    description: 'UsedCapacity > 750GB over PT1H (evaluated every PT1H) to flag account-level blob growth pressure.'
    severity: 3
    enabled: true
    scopes: [
      storageAccountResourceId
    ]
    evaluationFrequency: 'PT1H'
    windowSize: 'PT1H'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'StorageUsedCapacityBytes'
          metricNamespace: 'Microsoft.Storage/storageAccounts'
          metricName: 'UsedCapacity'
          operator: 'GreaterThan'
          threshold: 805306368000
          timeAggregation: 'Average'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource apimLatencyP99ProxyAlert 'Microsoft.Insights/metricAlerts@2018-03-01' = {
  name: '${projectName}-${environment}-apim-latency-p99-proxy'
  location: 'global'
  properties: {
    description: 'APIM tail latency proxy: Duration maximum > 3000ms over PT15M (evaluated every PT5M); complements average latency alerts.'
    severity: 2
    enabled: true
    scopes: [
      apimResourceId
    ]
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    criteria: {
      'odata.type': 'Microsoft.Azure.Monitor.SingleResourceMultipleMetricCriteria'
      allOf: [
        {
          criterionType: 'StaticThresholdCriterion'
          name: 'ApimDurationTailLatencyProxy'
          metricNamespace: 'Microsoft.ApiManagement/service'
          metricName: 'Duration'
          operator: 'GreaterThan'
          threshold: 3000
          timeAggregation: 'Maximum'
        }
      ]
    }
    actions: [
      {
        actionGroupId: actionGroup.id
      }
    ]
  }
}

resource uiProxyWarn502Alert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: '${projectName}-${environment}-ui-proxy-502-warn'
  location: location
  kind: 'LogAlert'
  properties: {
    description: 'UI proxy sustained 502 warn alert for critical API paths: failure rate >= 3% over 10 minutes with at least 30 requests.'
    displayName: '${projectName}-${environment} ui proxy 502 warn'
    enabled: true
    severity: 2
    evaluationFrequency: 'PT5M'
    windowSize: 'PT10M'
    scopes: [
      monitoringWorkspaceResourceId
    ]
    targetResourceTypes: [
      'Microsoft.OperationalInsights/workspaces'
    ]
    criteria: {
      allOf: [
        {
          query: uiProxyWarn502Query
          timeAggregation: 'Maximum'
          metricMeasureColumn: 'breach'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
          dimensions: [
            {
              name: 'upstreamPath'
              operator: 'Include'
              values: [
                '*'
              ]
            }
            {
              name: 'failureKind'
              operator: 'Include'
              values: [
                '*'
              ]
            }
            {
              name: 'sourceKey'
              operator: 'Include'
              values: [
                '*'
              ]
            }
            {
              name: 'status'
              operator: 'Include'
              values: [
                '502'
              ]
            }
          ]
        }
      ]
    }
    autoMitigate: true
    skipQueryValidation: false
    actions: {
      actionGroups: [
        actionGroup.id
      ]
      customProperties: {
        playbook: 'docs/architecture/playbooks/playbook-ui-proxy-failures.md'
        threshold: 'warn-3pct-10m-min30'
      }
    }
  }
}

resource uiProxyCritical502Alert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: '${projectName}-${environment}-ui-proxy-502-critical'
  location: location
  kind: 'LogAlert'
  properties: {
    description: 'UI proxy sustained 502 critical alert for critical API paths: failure rate >= 8% over 5 minutes with at least 50 requests.'
    displayName: '${projectName}-${environment} ui proxy 502 critical'
    enabled: true
    severity: 1
    evaluationFrequency: 'PT1M'
    windowSize: 'PT5M'
    scopes: [
      monitoringWorkspaceResourceId
    ]
    targetResourceTypes: [
      'Microsoft.OperationalInsights/workspaces'
    ]
    criteria: {
      allOf: [
        {
          query: uiProxyCritical502Query
          timeAggregation: 'Maximum'
          metricMeasureColumn: 'breach'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 1
            minFailingPeriodsToAlert: 1
          }
          dimensions: [
            {
              name: 'upstreamPath'
              operator: 'Include'
              values: [
                '*'
              ]
            }
            {
              name: 'failureKind'
              operator: 'Include'
              values: [
                '*'
              ]
            }
            {
              name: 'sourceKey'
              operator: 'Include'
              values: [
                '*'
              ]
            }
            {
              name: 'status'
              operator: 'Include'
              values: [
                '502'
              ]
            }
          ]
        }
      ]
    }
    autoMitigate: true
    skipQueryValidation: false
    actions: {
      actionGroups: [
        actionGroup.id
      ]
      customProperties: {
        playbook: 'docs/architecture/playbooks/playbook-ui-proxy-failures.md'
        threshold: 'critical-8pct-5m-min50'
      }
    }
  }
}

// ─── Agent Mode-Aware Alert Rules (ADR-024 Part 4) ────────────────────────────

var syncAgentP95Query = '''
let syncServices = dynamic([
  "ecommerce-catalog-search",
  "ecommerce-cart-intelligence",
  "ecommerce-checkout-support",
  "ecommerce-order-status",
  "ecommerce-product-detail-enrichment",
  "crm-profile-aggregation",
  "crm-support-assistance",
  "inventory-reservation-validation",
  "logistics-eta-computation",
  "logistics-carrier-selection",
  "logistics-returns-support"
]);
let agentRequests =
  union isfuzzy=true
    (AppRequests | project eventTime = TimeGenerated, name = tostring(Name), duration = DurationMs),
    (requests | project eventTime = timestamp, name = tostring(name), duration = toint(duration));
agentRequests
| where eventTime > ago(15m)
| extend serviceName = extract(@"/agents/([^/]+)/invoke", 1, name)
| where isnotempty(serviceName) and serviceName in~ (syncServices)
| summarize p95_ms = percentile(duration, 95) by serviceName
| where p95_ms > 8000
| extend breach = 1
'''

var asyncConsumerLagQuery = '''
let asyncServices = dynamic([
  "crm-campaign-intelligence",
  "crm-segmentation-personalization",
  "inventory-alerts-triggers",
  "inventory-health-check",
  "inventory-jit-replenishment",
  "logistics-route-issue-detection",
  "product-management-acp-transformation",
  "product-management-assortment-optimization",
  "product-management-consistency-validation",
  "product-management-normalization-classification",
  "search-enrichment-agent",
  "truth-ingestion",
  "truth-enrichment",
  "truth-hitl",
  "truth-export"
]);
AzureMetrics
| where TimeGenerated > ago(15m)
| where ResourceProvider == "MICROSOFT.EVENTHUB"
| where MetricName == "OutgoingMessages"
| extend consumerGroup = tostring(split(Resource, "/")[2])
| extend serviceName = iif(consumerGroup has_any (asyncServices), consumerGroup, "")
| where isnotempty(serviceName)
| summarize totalOutgoing = sum(Total) by serviceName
| join kind=inner (
    AzureMetrics
    | where TimeGenerated > ago(15m)
    | where ResourceProvider == "MICROSOFT.EVENTHUB"
    | where MetricName == "IncomingMessages"
    | summarize totalIncoming = sum(Total) by Resource
  ) on $left.serviceName == $right.Resource
| extend lagEstimate = totalIncoming - totalOutgoing
| where lagEstimate > 600
| extend breach = 1
'''

resource syncAgentLatencyAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: '${projectName}-${environment}-sync-agent-p95-latency'
  location: location
  kind: 'LogAlert'
  properties: {
    description: 'Sync agent invoke P95 latency exceeds 8 seconds over 15-minute window. Per ADR-024 Part 4, only sync (user-facing) agents are subject to invoke latency SLA.'
    displayName: '${projectName}-${environment} sync agent P95 latency breach'
    enabled: true
    severity: 2
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    scopes: [
      monitoringWorkspaceResourceId
    ]
    targetResourceTypes: [
      'Microsoft.OperationalInsights/workspaces'
    ]
    criteria: {
      allOf: [
        {
          query: syncAgentP95Query
          timeAggregation: 'Maximum'
          metricMeasureColumn: 'breach'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 3
            minFailingPeriodsToAlert: 2
          }
          dimensions: [
            {
              name: 'serviceName'
              operator: 'Include'
              values: [
                '*'
              ]
            }
          ]
        }
      ]
    }
    autoMitigate: true
    skipQueryValidation: false
    actions: {
      actionGroups: [
        actionGroup.id
      ]
      customProperties: {
        agentClass: 'sync'
        slaTarget: 'P95 < 8s'
        adr: 'ADR-024-Part4'
      }
    }
  }
}

resource asyncAgentConsumerLagAlert 'Microsoft.Insights/scheduledQueryRules@2023-12-01' = {
  name: '${projectName}-${environment}-async-agent-consumer-lag'
  location: location
  kind: 'LogAlert'
  properties: {
    description: 'Async agent consumer lag exceeds 10-minute threshold. Per ADR-024 Part 4, async agents are measured on throughput and lag, not invoke latency.'
    displayName: '${projectName}-${environment} async agent consumer lag breach'
    enabled: true
    severity: 3
    evaluationFrequency: 'PT5M'
    windowSize: 'PT15M'
    scopes: [
      monitoringWorkspaceResourceId
    ]
    targetResourceTypes: [
      'Microsoft.OperationalInsights/workspaces'
    ]
    criteria: {
      allOf: [
        {
          query: asyncConsumerLagQuery
          timeAggregation: 'Maximum'
          metricMeasureColumn: 'breach'
          operator: 'GreaterThan'
          threshold: 0
          failingPeriods: {
            numberOfEvaluationPeriods: 3
            minFailingPeriodsToAlert: 2
          }
          dimensions: [
            {
              name: 'serviceName'
              operator: 'Include'
              values: [
                '*'
              ]
            }
          ]
        }
      ]
    }
    autoMitigate: true
    skipQueryValidation: false
    actions: {
      actionGroups: [
        actionGroup.id
      ]
      customProperties: {
        agentClass: 'async'
        slaTarget: 'consumer lag < 10min'
        adr: 'ADR-024-Part4'
      }
    }
  }
}

output actionGroupId string = actionGroup.id
output actionGroupName string = actionGroup.name
