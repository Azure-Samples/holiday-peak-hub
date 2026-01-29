# Load and Resilience Test Plan: Azure Cosmos DB

**Version**: 1.0  
**Last Updated**: 2026-01  
**Owner**: Architecture Team

## Executive Summary

This test plan validates the Holiday Peak Hub accelerator's resilience to Azure Cosmos DB throttling (429 responses), high RU consumption, and partition key hotspots. Tests ensure the application gracefully handles resource constraints, implements proper retry logic, and maintains acceptable performance under load.

---

## Test Objectives

### Primary Goals
1. **Validate 429 Handling**: Confirm retry-after logic works correctly
2. **Measure RU Consumption**: Establish baseline and peak RU usage patterns
3. **Detect Hot Partitions**: Identify skewed partition key distributions
4. **Test Circuit Breaker**: Verify adapter circuit breaker activates appropriately
5. **Validate Degradation**: Ensure graceful degradation when Cosmos is throttled

### Success Criteria
- **429 Recovery**: 100% of throttled requests eventually succeed within 5 retries
- **Latency**: P95 latency stays < 1s under normal load, < 3s under throttling
- **No Data Loss**: All writes succeed or fail gracefully with explicit errors
- **Monitoring**: All 429 responses logged with diagnostic strings
- **Autoscaling**: Cosmos DB autoscale activates within 60s of sustained high load

---

## Test Environment

### Cosmos DB Configuration
```json
{
  "account": "holidaypeakhub-cosmos-test",
  "database": "retail_test",
  "containers": {
    "agent_memory": {
      "partition_key": "/user_id",
      "throughput": {
        "mode": "autoscale",
        "max_ru": 4000,
        "initial_ru": 400
      },
      "indexing_policy": {
        "indexing_mode": "consistent",
        "included_paths": ["/user_id/?", "/created_at/?"],
        "excluded_paths": ["/state/*"]
      }
    },
    "conversation_history": {
      "partition_key": "/user_id",
      "throughput": {
        "mode": "autoscale",
        "max_ru": 4000,
        "initial_ru": 400
      }
    },
    "profiles": {
      "partition_key": "/user_id",
      "throughput": {
        "mode": "provisioned",
        "ru": 1000
      }
    }
  }
}
```

### Application Configuration
```python
# apps/*/src/config.py
COSMOS_CONFIG = {
    "account_uri": os.getenv("COSMOS_ACCOUNT_URI"),
    "database": "retail_test",
    "container": "agent_memory",
    "connection_mode": "Gateway",  # For testing; Direct for prod
    "retry_total": 5,
    "retry_backoff_factor": 2,
    "retry_status_codes": [429, 503],
    "timeout": 5.0,
    "consistency_level": "Session"
}
```

---

## Test Scenarios

### Scenario 1: Baseline Load Test

**Objective**: Establish baseline RU consumption and latency under normal load.

**Load Profile**:
- **Duration**: 30 minutes
- **Virtual Users**: 100
- **Request Rate**: 50 req/s (steady state)
- **Operations**: 70% reads, 30% writes
- **Data Distribution**: Uniform across 1000 partition keys

**Test Script** (using Locust):
```python
# tests/load/cosmos_baseline.py
from locust import User, task, between, constant_throughput
from azure.cosmos import CosmosClient
import random
import uuid

class CosmosUser(User):
    wait_time = constant_throughput(0.5)  # 50 req/s per 100 users
    
    def on_start(self):
        self.client = CosmosClient(
            url=os.getenv("COSMOS_ACCOUNT_URI"),
            credential=os.getenv("COSMOS_KEY")
        )
        self.container = self.client.get_database_client("retail_test") \
                                    .get_container_client("agent_memory")
        self.user_ids = [f"user-{i:04d}" for i in range(1000)]
    
    @task(70)
    def read_profile(self):
        user_id = random.choice(self.user_ids)
        try:
            response = self.container.read_item(
                item=f"profile:{user_id}",
                partition_key=user_id
            )
            # Log RU consumption
            ru_charge = response.headers.get('x-ms-request-charge')
            self.environment.events.request.fire(
                request_type="cosmos_read",
                name="read_profile",
                response_time=response.headers.get('x-ms-elapsed-time-ms'),
                response_length=len(str(response)),
                exception=None,
                context={"ru": ru_charge}
            )
        except Exception as e:
            self.environment.events.request.fire(
                request_type="cosmos_read",
                name="read_profile",
                response_time=0,
                response_length=0,
                exception=e
            )
    
    @task(30)
    def write_session(self):
        user_id = random.choice(self.user_ids)
        session_data = {
            "id": f"session:{uuid.uuid4()}",
            "user_id": user_id,
            "data": {"cart": [], "timestamp": "2026-01-29T00:00:00Z"},
            "ttl": 900
        }
        
        try:
            response = self.container.upsert_item(session_data)
            ru_charge = response.headers.get('x-ms-request-charge')
            self.environment.events.request.fire(
                request_type="cosmos_write",
                name="write_session",
                response_time=response.headers.get('x-ms-elapsed-time-ms'),
                response_length=len(str(response)),
                exception=None,
                context={"ru": ru_charge}
            )
        except Exception as e:
            self.environment.events.request.fire(
                request_type="cosmos_write",
                name="write_session",
                response_time=0,
                response_length=0,
                exception=e
            )

# Run: locust -f tests/load/cosmos_baseline.py --host=https://localhost:8081
```

**Expected Results**:
| Metric | Expected Value |
|--------|----------------|
| Average RU/read | 1-3 RU |
| Average RU/write | 5-10 RU |
| Total RU/s | < 400 RU/s |
| P95 latency (read) | < 10ms |
| P95 latency (write) | < 20ms |
| 429 responses | 0 |

---

### Scenario 2: Sustained High Load (RU Saturation)

**Objective**: Trigger autoscaling and validate 429 handling under sustained load.

**Load Profile**:
- **Duration**: 60 minutes
- **Virtual Users**: 500
- **Request Rate**: 200 req/s → 1000 req/s (ramp over 10 min)
- **Operations**: 50% reads, 50% writes
- **Expected Behavior**: Trigger autoscale from 400 → 4000 RU/s

**Test Script**:
```python
# tests/load/cosmos_high_load.py
class HighLoadCosmosUser(User):
    wait_time = between(0.001, 0.01)  # 100-1000 req/s
    
    @task(50)
    def bulk_read(self):
        """Read multiple items to increase RU consumption."""
        user_id = random.choice(self.user_ids)
        query = "SELECT * FROM c WHERE c.user_id = @user_id"
        
        try:
            items = list(self.container.query_items(
                query=query,
                parameters=[{"name": "@user_id", "value": user_id}],
                enable_cross_partition_query=True
            ))
            # Higher RU charge for queries
            ru_charge = float(self.container.client_connection \
                                  .last_response_headers.get('x-ms-request-charge', 0))
        except CosmosHttpResponseError as e:
            if e.status_code == 429:
                retry_after = int(e.headers.get('x-ms-retry-after-ms', 1000))
                time.sleep(retry_after / 1000)
                # Retry logic happens here
            raise
    
    @task(50)
    def bulk_write(self):
        """Write multiple items rapidly."""
        user_id = random.choice(self.user_ids)
        batch = [
            {
                "id": f"item:{uuid.uuid4()}",
                "user_id": user_id,
                "data": {"payload": "x" * 1000},  # 1KB payload
                "ttl": 3600
            }
            for _ in range(10)
        ]
        
        for item in batch:
            try:
                self.container.upsert_item(item)
            except CosmosHttpResponseError as e:
                if e.status_code == 429:
                    # Track 429s
                    self.environment.events.request.fire(
                        request_type="cosmos_write",
                        name="write_throttled",
                        response_time=0,
                        response_length=0,
                        exception=e,
                        context={"status": 429}
                    )
                raise
```

**Expected Results**:
| Metric | Expected Value |
|--------|----------------|
| Peak RU/s | 3500-4000 RU/s |
| Autoscale activation | Within 60s |
| 429 rate at peak | 5-15% of requests |
| P95 latency under throttle | < 3s (with retries) |
| Retry success rate | > 95% |

---

### Scenario 3: Hot Partition Test

**Objective**: Simulate partition key hotspot and validate handling.

**Load Profile**:
- **Duration**: 20 minutes
- **Virtual Users**: 200
- **Request Rate**: 100 req/s
- **Data Distribution**: 80% of traffic to 10% of partition keys (Pareto)

**Test Script**:
```python
# tests/load/cosmos_hot_partition.py
class HotPartitionUser(User):
    def on_start(self):
        super().on_start()
        # 80% traffic to "hot" users
        self.hot_users = [f"vip-user-{i:03d}" for i in range(100)]
        self.cold_users = [f"user-{i:04d}" for i in range(100, 1000)]
    
    @task
    def access_data(self):
        # 80% probability of hitting hot partition
        if random.random() < 0.8:
            user_id = random.choice(self.hot_users)
        else:
            user_id = random.choice(self.cold_users)
        
        # Read + write to same partition
        self.read_profile(user_id)
        self.write_session(user_id)
```

**Expected Results**:
| Metric | Expected Value |
|--------|----------------|
| Hot partition RU/s | > 80% of total |
| 429 rate on hot partition | 15-30% |
| 429 rate on cold partition | < 1% |
| Circuit breaker activation | Yes (for hot keys) |

**Validation**:
```python
# Check partition metrics
az cosmosdb sql container throughput show \
    --account-name holidaypeakhub-cosmos-test \
    --database-name retail_test \
    --name agent_memory \
    --query "resource.{minThroughput:minimumThroughput, throughput:throughput}"

# Check diagnostics
query = """
SELECT 
    c.partition_key, 
    COUNT(1) as request_count,
    SUM(c.request_charge) as total_ru
FROM c
WHERE c.timestamp > DateTimeAdd('minute', -10, GetCurrentDateTime())
GROUP BY c.partition_key
ORDER BY total_ru DESC
"""
```

---

### Scenario 4: Circuit Breaker and Fallback

**Objective**: Validate adapter circuit breaker opens after repeated 429s.

**Load Profile**:
- **Duration**: 15 minutes
- **Provisioned RU/s**: 400 (fixed, no autoscale)
- **Request Rate**: 500 req/s (5x over capacity)

**Test Script**:
```python
# tests/integration/test_circuit_breaker.py
import pytest
from holiday_peak_lib.adapters.base import BaseAdapter
from azure.cosmos.exceptions import CosmosHttpResponseError

@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_repeated_429():
    """Circuit breaker should open after 5 consecutive 429s."""
    
    adapter = BaseAdapter(
        circuit_breaker_threshold=5,
        circuit_breaker_timeout=30
    )
    
    # Simulate 6 consecutive 429s
    for i in range(6):
        with pytest.raises(CosmosHttpResponseError) as exc:
            await adapter.fetch("query")
        
        if i < 5:
            assert exc.value.status_code == 429
        else:
            # 6th call should trigger circuit breaker
            assert adapter.circuit_breaker.is_open()
    
    # Subsequent calls should fail fast
    with pytest.raises(CircuitBreakerOpenError):
        await adapter.fetch("query")
    
    # Wait for timeout
    await asyncio.sleep(30)
    
    # Circuit breaker should be half-open
    assert adapter.circuit_breaker.is_half_open()

@pytest.mark.asyncio
async def test_fallback_to_cache_on_throttle():
    """Adapter should return cached data when Cosmos is throttled."""
    
    adapter = BaseAdapter(cache_enabled=True, cache_ttl=300)
    
    # First call populates cache
    result = await adapter.fetch("profile:user-123")
    
    # Simulate Cosmos throttling
    adapter._simulate_throttle = True
    
    # Should return cached result
    cached_result = await adapter.fetch("profile:user-123")
    assert cached_result == result
    assert cached_result.get("_from_cache") is True
```

**Expected Results**:
- Circuit breaker opens after 5 consecutive 429s
- Half-open state allows test requests after timeout
- Cached data returned when circuit is open
- Fail-fast prevents cascading failures

---

### Scenario 5: Burst Traffic (Black Friday Simulation)

**Objective**: Test behavior under sudden traffic spikes.

**Load Profile**:
- **Duration**: 10 minutes
- **Pattern**: Burst from 50 → 2000 req/s over 30 seconds, then sustain
- **Operations**: Simulate checkout flow (read profile, write cart, update inventory)

**Test Script**:
```python
# tests/load/cosmos_burst.py
class BurstTrafficUser(User):
    @task
    def checkout_flow(self):
        """Simulate multi-step checkout."""
        user_id = random.choice(self.user_ids)
        
        # Step 1: Read profile (2-3 RU)
        profile = self.container.read_item(
            item=f"profile:{user_id}",
            partition_key=user_id
        )
        
        # Step 2: Write cart (10-15 RU)
        cart = {
            "id": f"cart:{user_id}",
            "user_id": user_id,
            "items": [{"sku": f"PROD-{random.randint(1, 1000)}", "qty": 1}],
            "ttl": 86400
        }
        self.container.upsert_item(cart)
        
        # Step 3: Query orders (20-30 RU for cross-partition)
        orders = list(self.container.query_items(
            query="SELECT * FROM c WHERE c.user_id = @user_id AND c.type = 'order'",
            parameters=[{"name": "@user_id", "value": user_id}],
            enable_cross_partition_query=True
        ))

# Locust configuration for burst
locust -f tests/load/cosmos_burst.py \
    --host=https://localhost:8081 \
    --users=2000 \
    --spawn-rate=66 \  # 2000 users in 30s
    --run-time=10m
```

**Expected Results**:
| Phase | Duration | Expected RU/s | Expected 429 Rate |
|-------|----------|---------------|-------------------|
| Baseline | 0-5s | 400 | 0% |
| Ramp | 5-35s | 400 → 3500 | 10-20% |
| Peak | 35s-5min | 3500-4000 | 5-10% |
| Steady | 5-10min | 3000 | < 5% |

---

## Monitoring and Metrics

### Application Insights Queries

**429 Rate Over Time**:
```kusto
requests
| where timestamp > ago(1h)
| where customDimensions.status_code == 429
| summarize count() by bin(timestamp, 1m)
| render timechart
```

**RU Consumption by Operation**:
```kusto
traces
| where message contains "x-ms-request-charge"
| extend ru = todouble(customDimensions.request_charge)
| summarize avg(ru), max(ru), sum(ru) by operation_Name
| order by sum_ru desc
```

**Retry Success Rate**:
```kusto
dependencies
| where type == "Azure.Cosmos"
| extend retry_count = todouble(customDimensions.retry_count)
| summarize 
    total = count(),
    retried = countif(retry_count > 0),
    success_after_retry = countif(retry_count > 0 and success == true)
| extend retry_success_rate = (success_after_retry * 100.0) / retried
```

### Cosmos DB Metrics (Azure Monitor)

**Key Metrics to Track**:
```python
cosmos_metrics = [
    "TotalRequests",           # Total request count
    "TotalRequestUnits",       # RU consumption
    "ProvisionedThroughput",   # Current RU/s (autoscale)
    "ServerSideLatency",       # Backend latency
    "ServiceAvailability",     # Uptime %
]

# Query via Azure Monitor
from azure.monitor.query import MetricsQueryClient

metrics_client = MetricsQueryClient(credential)
response = metrics_client.query_resource(
    resource_uri=cosmos_resource_id,
    metric_names=cosmos_metrics,
    timespan=timedelta(hours=1),
    granularity=timedelta(minutes=1)
)
```

---

## Remediation Strategies

### Automatic Remediation

**1. Exponential Backoff (Already Implemented)**:
```python
# lib/src/holiday_peak_lib/adapters/base.py
@retry_async(
    retries=5,
    backoff_factor=2,
    retry_on=[CosmosHttpResponseError],
    retry_condition=lambda e: e.status_code == 429
)
async def _fetch_impl(self, query):
    # Cosmos SDK automatically respects retry-after header
    response = await self.container.read_item(...)
    return response
```

**2. Circuit Breaker**:
```python
if self.circuit_breaker.failure_count > 5:
    self.circuit_breaker.open()
    # Return cached data or fail fast
    if self.cache:
        return self.cache.get(query)
    raise CircuitBreakerOpenError("Cosmos DB unavailable")
```

**3. Request Throttling (Rate Limiter)**:
```python
# Implement token bucket to prevent overwhelming Cosmos
from aiolimiter import AsyncLimiter

limiter = AsyncLimiter(max_rate=100, time_period=1)  # 100 req/s max

async def fetch_with_rate_limit(query):
    async with limiter:
        return await adapter.fetch(query)
```

### Manual Remediation

**1. Scale Up RU/s**:
```bash
az cosmosdb sql container throughput update \
    --account-name holidaypeakhub-cosmos \
    --database-name retail_db \
    --name agent_memory \
    --max-throughput 10000
```

**2. Add Read Regions**:
```bash
az cosmosdb create \
    --name holidaypeakhub-cosmos \
    --resource-group holidaypeakhub-rg \
    --locations regionName=eastus2 failoverPriority=0 isZoneRedundant=False \
    --locations regionName=westus2 failoverPriority=1 isZoneRedundant=False
```

**3. Optimize Queries**:
```python
# Before: Cross-partition query (expensive)
items = container.query_items(
    query="SELECT * FROM c WHERE c.status = 'active'",
    enable_cross_partition_query=True
)

# After: Partition-scoped query (cheap)
items = container.query_items(
    query="SELECT * FROM c WHERE c.user_id = @user_id AND c.status = 'active'",
    parameters=[{"name": "@user_id", "value": user_id}],
    partition_key=user_id
)
```

---

## Chaos Engineering Tests

### Cosmos DB Unavailability

**Objective**: Validate graceful degradation when Cosmos is completely unavailable.

**Test Procedure**:
1. Apply network fault injection (block Cosmos DB endpoint)
2. Send normal traffic (100 req/s)
3. Validate circuit breaker activates
4. Validate fallback to cache or error responses
5. Restore connectivity
6. Validate recovery within 60s

**Fault Injection** (Azure Chaos Studio):
```json
{
  "name": "cosmos-outage-experiment",
  "description": "Simulate Cosmos DB unavailability",
  "selectors": [
    {
      "type": "List",
      "id": "cosmos-selector",
      "targets": [
        {
          "type": "ChaosTarget",
          "id": "/subscriptions/.../providers/Microsoft.DocumentDB/databaseAccounts/holidaypeakhub-cosmos"
        }
      ]
    }
  ],
  "steps": [
    {
      "name": "Block Cosmos Access",
      "branches": [
        {
          "name": "Network Fault",
          "actions": [
            {
              "type": "continuous",
              "name": "urn:csci:microsoft:networkSecurityGroup:blockTraffic/1.0",
              "duration": "PT5M",
              "parameters": [
                {"key": "destinationFilters", "value": "[\"cosmos.azure.com\"]"}
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## Test Execution Schedule

| Test | Frequency | Duration | Environment |
|------|-----------|----------|-------------|
| Baseline Load | Weekly | 30 min | Test |
| High Load | Weekly | 60 min | Test |
| Hot Partition | Bi-weekly | 20 min | Test |
| Circuit Breaker | Daily (CI) | 5 min | Test |
| Burst Traffic | Before releases | 10 min | Staging |
| Chaos (Outage) | Monthly | 15 min | Staging |

---

## Success Criteria Summary

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| 429 Recovery Rate | > 95% | Retry success after throttle |
| P95 Latency (Normal) | < 1s | Application Insights |
| P95 Latency (Throttled) | < 3s | Application Insights |
| Circuit Breaker Activation | Yes | When 5 consecutive failures |
| Autoscale Response | < 60s | Cosmos DB metrics |
| Zero Data Loss | 100% | No write failures logged |
| Diagnostic Coverage | 100% | All 429s logged with diagnostic strings |

---

## Related Documentation
- [ADR-014: Memory Partitioning](../adrs/adr-014-memory-partitioning.md)
- [ADR-008: Three-Tier Memory Architecture](../adrs/adr-008-memory-tiers.md)
- [Playbook: Cosmos High RU](../playbooks/playbook-cosmos-high-ru.md)
- [Azure Cosmos DB Best Practices](https://learn.microsoft.com/azure/cosmos-db/nosql/best-practice-dotnet)
