# Observability Query Templates

## Scope

Baseline Log Analytics queries used for first-response investigations across CRUD and agent services.

## Prerequisites

- Infrastructure deployed through `azd` with shared observability resources enabled.
- Action group notification receivers configured via:
  - `alertNotificationEmail`
  - `alertTeamsWebhookUrl`

## Correlation-first Trace Walk

Use this when a request fails or latency spikes and you have `X-Correlation-ID`.

```kusto
traces
| where timestamp > ago(2h)
| where message has "correlation_id"
| where message has "<correlation-id>"
| project timestamp, cloud_RoleName, severityLevel, message, operation_Id
| order by timestamp asc
```

## APIM Failed Requests

```kusto
AzureDiagnostics
| where TimeGenerated > ago(2h)
| where ResourceProvider == "MICROSOFT.APIMANAGEMENT"
| where toint(ResponseCode) >= 500
| summarize failures=count() by bin(TimeGenerated, 5m), Resource
| order by TimeGenerated desc
```

## AKS Pod Restart and Pull Failures

```kusto
KubePodInventory
| where TimeGenerated > ago(2h)
| summarize restartCount=sum(ContainerRestartCount) by bin(TimeGenerated, 5m), Namespace, PodName
| where restartCount > 0
| order by TimeGenerated desc
```

```kusto
ContainerLog
| where TimeGenerated > ago(2h)
| where LogEntry has_any ("ImagePullBackOff", "ErrImagePull")
| project TimeGenerated, Name, LogEntry
| order by TimeGenerated desc
```

## Cosmos RU and Throttling Pressure

```kusto
AzureMetrics
| where TimeGenerated > ago(2h)
| where MetricName in ("TotalRequestUnits", "TotalRequests", "ServerSideRequests")
| summarize avgVal=avg(Total), maxVal=max(Total) by MetricName, bin(TimeGenerated, 5m), ResourceId
| order by TimeGenerated desc
```

## Redis Evictions and Errors

```kusto
AzureMetrics
| where TimeGenerated > ago(2h)
| where MetricName in ("usedmemorypercentage", "errors", "evictedkeys")
| summarize value=max(Total) by MetricName, bin(TimeGenerated, 5m), ResourceId
| order by TimeGenerated desc
```

## PostgreSQL Hotspot Indicators

```kusto
AzureMetrics
| where TimeGenerated > ago(2h)
| where MetricName in ("cpu_percent", "storage_percent", "long_running_queries")
| summarize value=max(Average) by MetricName, bin(TimeGenerated, 5m), ResourceId
| order by TimeGenerated desc
```

## Event Hubs Backlog and Throttling Signals

```kusto
AzureMetrics
| where TimeGenerated > ago(2h)
| where MetricName in ("IncomingMessages", "OutgoingMessages", "ThrottledRequests")
| summarize value=max(Total) by MetricName, bin(TimeGenerated, 5m), ResourceId
| order by TimeGenerated desc
```
