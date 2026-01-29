# Test Plans

This directory contains comprehensive load and resilience test plans for critical infrastructure components.

## Available Test Plans

### 1. [Cosmos DB Load and Resilience](cosmos-db-load-resilience.md)
**Component**: Azure Cosmos DB (Warm Memory Tier)  
**Focus**: 429 handling, RU consumption, hot partitions, circuit breaker

**Key Test Scenarios**:
- ✅ Baseline load test (RU consumption patterns)
- ✅ Sustained high load (autoscaling validation)
- ✅ Hot partition simulation (skewed partition keys)
- ✅ Circuit breaker and fallback
- ✅ Burst traffic (Black Friday simulation)
- ✅ Chaos engineering (Cosmos unavailability)

**Success Criteria**:
- 429 recovery rate > 95%
- P95 latency < 1s normal, < 3s throttled
- Autoscale response < 60s
- Zero data loss

---

### 2. [Event Hubs Load and Resilience](eventhub-load-resilience.md)
**Component**: Azure Event Hubs (SAGA Choreography)  
**Focus**: Backpressure, partition distribution, dead-letter queue, SAGA resilience

**Key Test Scenarios**:
- ✅ Baseline throughput test (1,000 msg/s)
- ✅ High load with auto-inflate (5,000 msg/s)
- ✅ Partition key hotspot (80/20 distribution)
- ✅ Backpressure and producer throttling
- ✅ Dead-letter queue (poison messages)
- ✅ SAGA choreography under load (500 orders/s)
- ✅ Chaos engineering (Event Hub unavailability)

**Success Criteria**:
- Throughput 10,000 msg/s
- P95 e2e latency < 5s
- Partition balance < 150% variance
- SAGA completion > 99%
- Zero message loss

---

## Test Plan Structure

Each test plan follows a consistent structure:

### 1. Executive Summary
- Test objectives
- Success criteria
- Key risks

### 2. Test Environment
- Infrastructure configuration
- Application settings
- Network topology

### 3. Test Scenarios
- Scenario description
- Load profile
- Test scripts (Python/Locust)
- Expected results

### 4. Monitoring and Metrics
- Azure Monitor queries
- Application Insights KQL
- Custom metrics

### 5. Remediation Strategies
- Automatic (retry, circuit breaker, backpressure)
- Manual (scaling, optimization)

### 6. Chaos Engineering
- Fault injection tests
- Recovery validation

---

## Running Tests

### Prerequisites
```bash
# Install test dependencies
pip install locust azure-eventhub azure-cosmos azure-storage-blob pytest pytest-asyncio

# Set environment variables
export COSMOS_ACCOUNT_URI="https://..."
export COSMOS_KEY="..."
export EVENT_HUB_CONNECTION_STRING="Endpoint=sb://..."
export STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=https..."
```

### Cosmos DB Tests
```bash
# Baseline load test
locust -f tests/load/cosmos_baseline.py --host=https://localhost:8081 --users=100 --spawn-rate=10 --run-time=30m

# High load test
locust -f tests/load/cosmos_high_load.py --users=500 --spawn-rate=50 --run-time=60m

# Hot partition test
locust -f tests/load/cosmos_hot_partition.py --users=200 --spawn-rate=20 --run-time=20m

# Circuit breaker test
pytest tests/integration/test_circuit_breaker.py -v
```

### Event Hubs Tests
```bash
# Baseline throughput
python tests/load/eventhub_baseline.py

# High load with auto-inflate
python tests/load/eventhub_high_load.py

# Backpressure test
python tests/load/eventhub_backpressure.py

# SAGA load test
python tests/load/eventhub_saga.py
```

---

## Monitoring During Tests

### Azure Monitor Dashboards

**Cosmos DB Dashboard**:
```bash
# Create dashboard
az portal dashboard create \
    --name "Cosmos DB Load Test" \
    --resource-group holidaypeakhub-rg \
    --input-path ./dashboards/cosmos-load-test.json
```

**Event Hubs Dashboard**:
```bash
# Create dashboard
az portal dashboard create \
    --name "Event Hub Load Test" \
    --resource-group holidaypeakhub-rg \
    --input-path ./dashboards/eventhub-load-test.json
```

### Live Monitoring Commands

**Cosmos DB**:
```bash
# Watch RU consumption
watch -n 5 'az cosmosdb sql container throughput show \
    --account-name holidaypeakhub-cosmos \
    --database-name retail_db \
    --name agent_memory \
    --query "resource.throughput"'

# Watch 429 rate
watch -n 5 'az monitor metrics list \
    --resource /subscriptions/.../Microsoft.DocumentDB/databaseAccounts/holidaypeakhub-cosmos \
    --metric TotalRequests \
    --filter "StatusCode eq 429" \
    --aggregation Count \
    --interval PT1M'
```

**Event Hubs**:
```bash
# Watch throughput
watch -n 5 'az monitor metrics list \
    --resource /subscriptions/.../Microsoft.EventHub/namespaces/holidaypeakhub-eventhubs \
    --metric IncomingMessages \
    --aggregation Total \
    --interval PT1M'

# Watch throttling
watch -n 5 'az monitor metrics list \
    --resource /subscriptions/.../Microsoft.EventHub/namespaces/holidaypeakhub-eventhubs \
    --metric ThrottledRequests \
    --aggregation Total \
    --interval PT1M'
```

---

## Test Execution Schedule

| Test | Frequency | Owner | Environment |
|------|-----------|-------|-------------|
| Cosmos Baseline | Weekly | SRE Team | Test |
| Cosmos High Load | Weekly | SRE Team | Test |
| Cosmos Hot Partition | Bi-weekly | Dev Team | Test |
| Cosmos Circuit Breaker | Daily (CI) | CI/CD | Test |
| Event Hub Baseline | Weekly | SRE Team | Test |
| Event Hub High Load | Weekly | SRE Team | Test |
| Event Hub Backpressure | Weekly | SRE Team | Test |
| Event Hub SAGA | Before releases | QA Team | Staging |
| Chaos Tests | Monthly | SRE Team | Staging |

---

## Reporting

### Test Report Template

```markdown
# Load Test Report: {Component} - {Date}

## Summary
- **Test**: {Test Name}
- **Duration**: {Minutes}
- **Load**: {Requests/Messages per second}
- **Result**: ✅ Pass / ❌ Fail

## Metrics
| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Throughput | X req/s | Y req/s | ✅/❌ |
| P95 Latency | Xms | Yms | ✅/❌ |
| Error Rate | <X% | Y% | ✅/❌ |

## Issues Identified
1. {Issue description}
   - **Severity**: Critical/High/Medium/Low
   - **Action**: {Remediation steps}

## Recommendations
- {Recommendation 1}
- {Recommendation 2}

## Artifacts
- Locust report: {URL}
- App Insights: {URL}
- Dashboards: {URL}
```

---

## Related Documentation
- [ADR-008: Three-Tier Memory Architecture](../adrs/adr-008-memory-tiers.md)
- [ADR-007: SAGA Choreography](../adrs/adr-007-saga-choreography.md)
- [ADR-014: Memory Partitioning](../adrs/adr-014-memory-partitioning.md)
- [Playbook: Cosmos High RU](../playbooks/playbook-cosmos-high-ru.md)
- [Playbook: Blob Throttling](../playbooks/playbook-blob-throttling.md)

---

## Contributing

When adding new test plans:

1. **Follow the template structure**
2. **Include runnable test scripts**
3. **Document expected results**
4. **Add monitoring queries**
5. **Link to relevant ADRs and playbooks**
6. **Update this README**

---

## Continuous Improvement

Test plans should be updated:
- **Quarterly**: Review success criteria
- **After incidents**: Add regression tests
- **New features**: Add coverage for new flows
- **Performance changes**: Adjust baselines
