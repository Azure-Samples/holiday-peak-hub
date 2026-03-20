targetScope = 'resourceGroup'

@description('Project name used for alert naming.')
param projectName string

@description('Environment name used for alert naming.')
param environment string

@description('Azure region for alerts resources.')
param location string = resourceGroup().location

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

var actionGroupShortName = take(replace('${projectName}${environment}', '-', ''), 12)

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
    description: 'Cosmos RU consumption exceeded baseline threshold.'
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
    description: 'Cosmos 5xx responses exceeded baseline threshold.'
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
    description: 'Cosmos request latency exceeded baseline threshold.'
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
    description: 'Redis memory utilization exceeded baseline threshold.'
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
    description: 'Redis connection failures detected.'
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
    description: 'Redis key eviction activity exceeded baseline threshold.'
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
    description: 'PostgreSQL CPU utilization exceeded baseline threshold.'
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
    description: 'PostgreSQL storage utilization exceeded baseline threshold.'
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
    description: 'PostgreSQL long-running query count exceeded baseline threshold.'
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
    description: 'Event Hubs throttled requests exceeded baseline threshold.'
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
    description: 'Event Hubs abandoned messages exceeded baseline threshold.'
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
    description: 'Event Hubs consumer lag proxy metric exceeded baseline threshold.'
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
    description: 'AKS node CPU utilization exceeded baseline threshold.'
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
    description: 'AKS pod restart activity exceeded baseline threshold.'
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
    description: 'AKS image pull failures exceeded baseline threshold.'
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
    description: 'APIM failed request count exceeded baseline threshold.'
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
    description: 'APIM request duration exceeded baseline threshold.'
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
    description: 'APIM 5xx error rate proxy exceeded baseline threshold.'
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

output actionGroupId string = actionGroup.id
output actionGroupName string = actionGroup.name
