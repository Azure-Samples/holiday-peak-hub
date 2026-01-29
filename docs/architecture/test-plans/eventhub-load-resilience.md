# Load and Resilience Test Plan: Azure Event Hubs

**Version**: 1.0  
**Last Updated**: 2026-01  
**Owner**: Architecture Team

## Executive Summary

This test plan validates the Holiday Peak Hub accelerator's resilience to Azure Event Hubs backpressure, partition throttling, and message delivery guarantees under high load. Tests ensure proper SAGA choreography, dead-letter handling, and graceful degradation when Event Hubs reaches capacity.

---

## Test Objectives

### Primary Goals
1. **Validate Backpressure Handling**: Confirm application slows publishing when Event Hubs is saturated
2. **Test Partition Distribution**: Ensure even load across partitions
3. **Verify Message Ordering**: Maintain order guarantees within partitions
4. **Test Dead-Letter Queue**: Validate poison message handling
5. **Measure Throughput Limits**: Identify max sustainable throughput
6. **Test SAGA Resilience**: Ensure choreography survives failures

### Success Criteria
- **Throughput**: Handle 10,000 msg/s across all services
- **Latency**: P95 end-to-end latency < 5s under normal load
- **No Message Loss**: 100% delivery or explicit failure
- **Backpressure**: Producer slows down when Event Hubs throttles
- **Partition Balance**: No partition exceeds 150% of average load
- **DLQ Processing**: Poison messages move to dead-letter within 3 retries

---

## Test Environment

### Event Hub Configuration
```json
{
  "namespace": "holidaypeakhub-eventhubs-test",
  "event_hubs": {
    "inventory-events": {
      "partition_count": 16,
      "message_retention_days": 7,
      "throughput_units": 10,
      "auto_inflate": true,
      "max_throughput_units": 20,
      "consumer_groups": ["inventory-service", "analytics"]
    },
    "returns-events": {
      "partition_count": 8,
      "message_retention_days": 3,
      "throughput_units": 5,
      "auto_inflate": true,
      "max_throughput_units": 10
    },
    "order-events": {
      "partition_count": 32,
      "message_retention_days": 7,
      "throughput_units": 20,
      "auto_inflate": true,
      "max_throughput_units": 40
    }
  }
}
```

### Application Configuration
```python
# apps/*/src/config.py
EVENT_HUB_CONFIG = {
    "connection_string": os.getenv("EVENT_HUB_CONNECTION_STRING"),
    "event_hub_name": "inventory-events",
    "consumer_group": "$Default",
    "checkpoint_store": {
        "account_url": os.getenv("STORAGE_ACCOUNT_URL"),
        "container_name": "checkpoints"
    },
    "max_batch_size": 300,
    "max_wait_time": 10,
    "prefetch_count": 300,
    "retry_options": {
        "mode": "exponential",
        "delay": 1.0,
        "max_delay": 60.0,
        "max_retries": 5
    }
}
```

---

## Test Scenarios

### Scenario 1: Baseline Throughput Test

**Objective**: Establish baseline throughput and latency characteristics.

**Load Profile**:
- **Duration**: 30 minutes
- **Producers**: 10 services
- **Message Rate**: 1,000 msg/s (100 msg/s per producer)
- **Message Size**: 1KB average
- **Partition Strategy**: Round-robin

**Test Script** (Python):
```python
# tests/load/eventhub_baseline.py
import asyncio
from azure.eventhub.aio import EventHubProducerClient
from azure.eventhub import EventData
import time
import random
import json

class EventHubLoadTest:
    def __init__(self, connection_string: str, event_hub_name: str):
        self.producer = EventHubProducerClient.from_connection_string(
            conn_str=connection_string,
            eventhub_name=event_hub_name
        )
    
    async def send_events(self, count: int, rate: int):
        """Send events at specified rate (msg/s)."""
        interval = 1.0 / rate
        
        for i in range(count):
            start = time.time()
            
            event_data = EventData(json.dumps({
                "event_type": "inventory.updated",
                "sku": f"PROD-{random.randint(1, 10000)}",
                "available": random.randint(0, 100),
                "warehouse": f"WH-{random.randint(1, 10)}",
                "timestamp": time.time()
            }))
            
            try:
                await self.producer.send_event(event_data)
                
                # Track metrics
                latency = (time.time() - start) * 1000
                print(f"Sent event {i}, latency: {latency:.2f}ms")
                
            except Exception as e:
                print(f"Failed to send event {i}: {e}")
            
            # Rate limiting
            elapsed = time.time() - start
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)
    
    async def run_baseline(self):
        """Run 30-minute baseline test."""
        messages_per_second = 100
        duration_seconds = 1800
        total_messages = messages_per_second * duration_seconds
        
        await self.send_events(total_messages, messages_per_second)

# Run test
async def main():
    test = EventHubLoadTest(
        connection_string=os.getenv("EVENT_HUB_CONNECTION_STRING"),
        event_hub_name="inventory-events"
    )
    await test.run_baseline()

asyncio.run(main())
```

**Consumer Script**:
```python
# tests/load/eventhub_consumer.py
from azure.eventhub.aio import EventHubConsumerClient
from azure.eventhub.extensions.checkpointstoreblobaio import BlobCheckpointStore

class EventHubConsumer:
    def __init__(self, connection_string: str, event_hub_name: str):
        checkpoint_store = BlobCheckpointStore.from_connection_string(
            conn_str=os.getenv("STORAGE_CONNECTION_STRING"),
            container_name="checkpoints"
        )
        
        self.consumer = EventHubConsumerClient.from_connection_string(
            conn_str=connection_string,
            consumer_group="$Default",
            eventhub_name=event_hub_name,
            checkpoint_store=checkpoint_store
        )
        self.message_count = 0
        self.start_time = time.time()
    
    async def on_event(self, partition_context, event):
        """Process event and checkpoint."""
        self.message_count += 1
        
        # Track end-to-end latency
        event_data = json.loads(event.body_as_str())
        latency = (time.time() - event_data["timestamp"]) * 1000
        
        print(f"Received event {self.message_count}, "
              f"partition: {partition_context.partition_id}, "
              f"e2e_latency: {latency:.2f}ms")
        
        # Checkpoint every 100 messages
        if self.message_count % 100 == 0:
            await partition_context.update_checkpoint(event)
    
    async def consume(self):
        """Start consuming events."""
        async with self.consumer:
            await self.consumer.receive(
                on_event=self.on_event,
                starting_position="-1"  # From beginning
            )

# Run consumer
asyncio.run(EventHubConsumer(
    connection_string=os.getenv("EVENT_HUB_CONNECTION_STRING"),
    event_hub_name="inventory-events"
).consume())
```

**Expected Results**:
| Metric | Expected Value |
|--------|----------------|
| Throughput | 1,000 msg/s |
| P95 publish latency | < 50ms |
| P95 e2e latency | < 500ms |
| Partition distribution variance | < 10% |
| Message loss | 0 |

---

### Scenario 2: High Load with Auto-Inflate

**Objective**: Trigger auto-inflate and validate throughput scaling.

**Load Profile**:
- **Duration**: 60 minutes
- **Producers**: 50 services
- **Message Rate**: 500 → 5,000 msg/s (ramp over 10 min)
- **Throughput Units**: Start at 10, auto-inflate to 20

**Test Script**:
```python
# tests/load/eventhub_high_load.py
class HighLoadTest:
    async def ramp_load(self):
        """Ramp from 500 to 5000 msg/s over 10 minutes."""
        ramp_duration = 600  # 10 minutes
        start_rate = 500
        end_rate = 5000
        
        for elapsed in range(0, ramp_duration, 60):  # Every minute
            current_rate = start_rate + (end_rate - start_rate) * (elapsed / ramp_duration)
            
            print(f"Minute {elapsed // 60}: {int(current_rate)} msg/s")
            
            # Send for 1 minute at current rate
            await self.send_events(int(current_rate * 60), int(current_rate))
        
        # Sustain at peak for 50 minutes
        await self.send_events(end_rate * 3000, end_rate)

# Monitor throughput units during test
az eventhubs namespace show \
    --name holidaypeakhub-eventhubs-test \
    --resource-group holidaypeakhub-rg \
    --query "{currentTU:sku.capacity, autoInflate:isAutoInflateEnabled, maxTU:maximumThroughputUnits}"
```

**Expected Results**:
| Phase | Duration | Expected TU | Expected Throttle Rate |
|-------|----------|-------------|------------------------|
| Baseline | 0-5min | 10 | 0% |
| Ramp | 5-15min | 10 → 18 | 5-15% during scale |
| Peak | 15-60min | 18-20 | < 5% |

---

### Scenario 3: Partition Key Hotspot

**Objective**: Test behavior when one partition is overloaded.

**Load Profile**:
- **Duration**: 20 minutes
- **Message Rate**: 2,000 msg/s
- **Partition Strategy**: 80% to single partition key (warehouse-01)

**Test Script**:
```python
# tests/load/eventhub_hot_partition.py
class HotPartitionTest:
    async def send_skewed_events(self):
        """Send 80% of messages to same partition key."""
        
        for i in range(120000):  # 2000/s * 60s * 20min
            # 80% to hot partition
            if random.random() < 0.8:
                partition_key = "warehouse-01"
            else:
                partition_key = f"warehouse-{random.randint(2, 10):02d}"
            
            event = EventData(json.dumps({
                "warehouse": partition_key,
                "data": "payload"
            }))
            event.partition_key = partition_key
            
            await self.producer.send_event(event)

# Monitor partition metrics
async def monitor_partitions(consumer_client):
    """Track message count per partition."""
    partition_counts = {}
    
    async def on_event(partition_context, event):
        partition_id = partition_context.partition_id
        partition_counts[partition_id] = partition_counts.get(partition_id, 0) + 1
        
        if sum(partition_counts.values()) % 1000 == 0:
            print(f"Partition distribution: {partition_counts}")
    
    await consumer_client.receive(on_event=on_event)
```

**Expected Results**:
- **Hot partition**: 80% of messages (1,600 msg/s)
- **Cold partitions**: 20% distributed (25 msg/s each)
- **Throttling**: Hot partition may hit per-partition limit (1 MB/s or ~1000 msg/s for 1KB messages)
- **Recommendation**: Use better partition key strategy

---

### Scenario 4: Backpressure and Producer Throttling

**Objective**: Validate producer slows down when Event Hubs throttles.

**Load Profile**:
- **Duration**: 15 minutes
- **Throughput Units**: 5 (fixed, no auto-inflate)
- **Message Rate**: 10,000 msg/s (2x over capacity)

**Test Script**:
```python
# tests/load/eventhub_backpressure.py
from azure.eventhub import EventHubProducerClient, EventData
from azure.eventhub.exceptions import EventHubError
import time

class BackpressureTest:
    def __init__(self):
        self.producer = EventHubProducerClient.from_connection_string(
            conn_str=os.getenv("EVENT_HUB_CONNECTION_STRING"),
            eventhub_name="inventory-events"
        )
        self.throttle_count = 0
        self.retry_delays = []
    
    async def send_with_backpressure(self):
        """Send messages and handle throttling."""
        
        for i in range(900000):  # 10k/s * 60s * 15min
            event = EventData(f"message-{i}")
            
            retry_count = 0
            while retry_count < 5:
                try:
                    start = time.time()
                    await self.producer.send_event(event)
                    break
                    
                except EventHubError as e:
                    if "throttled" in str(e).lower():
                        self.throttle_count += 1
                        
                        # Exponential backoff
                        delay = min(2 ** retry_count, 60)
                        self.retry_delays.append(delay)
                        
                        print(f"Throttled, backing off {delay}s")
                        await asyncio.sleep(delay)
                        retry_count += 1
                    else:
                        raise
            
            # Report metrics every 1000 messages
            if i % 1000 == 0:
                avg_delay = sum(self.retry_delays) / len(self.retry_delays) if self.retry_delays else 0
                print(f"Messages sent: {i}, "
                      f"throttled: {self.throttle_count}, "
                      f"avg_retry_delay: {avg_delay:.2f}s")

# Expected behavior: Producer automatically slows down
# Effective throughput should stabilize around capacity (5 TU = ~5 MB/s = ~5000 msg/s for 1KB messages)
```

**Expected Results**:
- Initial rate: 10,000 msg/s
- Throttle rate: 50-60% of requests
- Effective rate after backoff: ~5,000 msg/s
- P95 retry delay: < 16s (2^4)

---

### Scenario 5: Dead-Letter Queue (Poison Messages)

**Objective**: Test poison message handling and DLQ processing.

**Load Profile**:
- **Duration**: 10 minutes
- **Message Rate**: 1,000 msg/s
- **Poison Rate**: 5% (50 msg/s are malformed)

**Test Script**:
```python
# tests/load/eventhub_dlq.py
class DLQTest:
    async def send_with_poison_messages(self):
        """Send mix of valid and malformed messages."""
        
        for i in range(60000):
            # 5% poison messages
            if random.random() < 0.05:
                # Send invalid JSON
                event = EventData(b"<invalid-json>")
            else:
                event = EventData(json.dumps({
                    "event_type": "inventory.updated",
                    "data": {"sku": f"PROD-{i}"}
                }))
            
            await self.producer.send_event(event)

class DLQConsumer:
    def __init__(self):
        self.dlq_messages = []
        self.max_retries = 3
    
    async def on_event(self, partition_context, event):
        """Process event with retry and DLQ logic."""
        
        retry_count = int(event.properties.get("retry_count", 0))
        
        try:
            # Try to parse JSON
            data = json.loads(event.body_as_str())
            
            # Process event
            await self.process_event(data)
            
            # Success - checkpoint
            await partition_context.update_checkpoint(event)
            
        except json.JSONDecodeError as e:
            if retry_count < self.max_retries:
                # Retry: Send back to Event Hub with incremented counter
                retry_event = EventData(event.body)
                retry_event.properties = {
                    **event.properties,
                    "retry_count": retry_count + 1,
                    "error": str(e)
                }
                
                await self.retry_producer.send_event(retry_event)
                await partition_context.update_checkpoint(event)
                
            else:
                # Max retries exceeded - send to DLQ
                dlq_event = {
                    "original_event": event.body_as_str(),
                    "error": str(e),
                    "retry_count": retry_count,
                    "timestamp": time.time(),
                    "partition": partition_context.partition_id
                }
                
                await self.send_to_dlq(dlq_event)
                self.dlq_messages.append(dlq_event)
                
                # Checkpoint to skip poison message
                await partition_context.update_checkpoint(event)
    
    async def send_to_dlq(self, event: dict):
        """Send to dead-letter storage (Blob or separate Event Hub)."""
        blob_client = BlobClient.from_connection_string(
            conn_str=os.getenv("STORAGE_CONNECTION_STRING"),
            container_name="dead-letter-queue",
            blob_name=f"dlq-{uuid.uuid4()}.json"
        )
        
        await blob_client.upload_blob(json.dumps(event))
```

**Expected Results**:
- **Poison messages**: 3,000 (5% of 60,000)
- **Retry attempts**: 9,000 (3 retries per poison message)
- **DLQ entries**: 3,000 (after max retries)
- **Processing continues**: Non-poison messages unaffected

---

### Scenario 6: SAGA Choreography Under Load

**Objective**: Test multi-service SAGA workflow under high load.

**Load Profile**:
- **Duration**: 30 minutes
- **Order Rate**: 500 orders/s
- **SAGA Steps**: 5 services (order → payment → inventory → fulfillment → notification)

**Test Script**:
```python
# tests/load/eventhub_saga.py
class SAGALoadTest:
    async def trigger_order_saga(self, order_id: str):
        """Initiate order SAGA."""
        
        # Step 1: Publish order.created
        await self.publisher.publish_event(
            event_hub="order-events",
            event={
                "event_type": "order.created",
                "order_id": order_id,
                "items": [{"sku": "PROD-123", "qty": 1}],
                "total": 99.99,
                "saga_id": order_id,
                "timestamp": time.time()
            }
        )
    
    async def run_saga_load_test(self):
        """Create 500 orders/s for 30 minutes."""
        
        for i in range(900000):  # 500/s * 60s * 30min
            order_id = f"ORD-{i:08d}"
            await self.trigger_order_saga(order_id)
            
            # Rate limit
            await asyncio.sleep(0.002)  # 500/s

# Monitor SAGA completion
class SAGAMonitor:
    def __init__(self):
        self.saga_states = {}  # saga_id -> {step: timestamp}
    
    async def on_event(self, partition_context, event):
        """Track SAGA progress."""
        data = json.loads(event.body_as_str())
        saga_id = data.get("saga_id")
        event_type = data["event_type"]
        
        if saga_id not in self.saga_states:
            self.saga_states[saga_id] = {}
        
        self.saga_states[saga_id][event_type] = time.time()
        
        # Check if SAGA completed
        expected_steps = [
            "order.created",
            "payment.completed",
            "inventory.reserved",
            "fulfillment.scheduled",
            "notification.sent"
        ]
        
        if all(step in self.saga_states[saga_id] for step in expected_steps):
            start = self.saga_states[saga_id]["order.created"]
            end = self.saga_states[saga_id]["notification.sent"]
            duration = (end - start) * 1000
            
            print(f"SAGA {saga_id} completed in {duration:.2f}ms")

# Compensating transaction on failure
async def handle_saga_failure(saga_id: str, failed_step: str):
    """Rollback SAGA on failure."""
    
    compensation_events = {
        "payment.failed": "payment.refund",
        "inventory.failed": "inventory.release",
        "fulfillment.failed": "order.cancel"
    }
    
    compensation_event = compensation_events.get(failed_step)
    if compensation_event:
        await publisher.publish_event(
            event_hub="order-events",
            event={
                "event_type": compensation_event,
                "saga_id": saga_id,
                "reason": f"Compensating for {failed_step}"
            }
        )
```

**Expected Results**:
| Metric | Target |
|--------|--------|
| SAGA completion rate | > 99% |
| P95 SAGA duration | < 5s |
| Compensation rate | < 1% |
| Message ordering (per partition) | 100% |

---

## Monitoring and Metrics

### Event Hubs Metrics (Azure Monitor)

**Key Metrics**:
```python
eventhub_metrics = [
    "IncomingMessages",        # Messages published
    "OutgoingMessages",        # Messages consumed
    "IncomingBytes",           # Data ingress
    "OutgoingBytes",           # Data egress
    "ThrottledRequests",       # Throttle count
    "ServerErrors",            # 5xx errors
    "UserErrors",              # 4xx errors
    "CaptureBacklog",          # Capture lag
    "ActiveConnections"        # Current connections
]

# Query metrics
from azure.monitor.query import MetricsQueryClient

metrics_response = metrics_client.query_resource(
    resource_uri=eventhub_resource_id,
    metric_names=eventhub_metrics,
    timespan=timedelta(hours=1),
    granularity=timedelta(minutes=1),
    aggregations=["Average", "Maximum", "Total"]
)
```

### Application Insights Queries

**End-to-End Latency**:
```kusto
traces
| where message contains "saga_completed"
| extend duration_ms = todouble(customDimensions.duration_ms)
| summarize 
    avg(duration_ms),
    percentile(duration_ms, 95),
    percentile(duration_ms, 99)
| render timechart
```

**Throttle Rate**:
```kusto
exceptions
| where type contains "EventHubError"
| where message contains "throttled"
| summarize throttle_count = count() by bin(timestamp, 1m)
| join kind=inner (
    requests
    | summarize total_count = count() by bin(timestamp, 1m)
) on timestamp
| extend throttle_rate = (throttle_count * 100.0) / total_count
| render timechart
```

**Partition Distribution**:
```kusto
traces
| where message contains "partition_id"
| extend partition = tostring(customDimensions.partition_id)
| summarize message_count = count() by partition
| render barchart
```

---

## Remediation Strategies

### Automatic Remediation

**1. Exponential Backoff (Implemented)**:
```python
# Already in SDK
producer_client = EventHubProducerClient.from_connection_string(
    conn_str=connection_string,
    eventhub_name=event_hub_name,
    retry_total=5,
    retry_backoff_factor=2,
    retry_backoff_max=60
)
```

**2. Circuit Breaker for Publishers**:
```python
from circuitbreaker import circuit

@circuit(failure_threshold=10, recovery_timeout=30)
async def publish_event(event: EventData):
    await producer.send_event(event)
```

**3. Checkpoint Management**:
```python
# Checkpoint frequently to prevent reprocessing
if message_count % 10 == 0:
    await partition_context.update_checkpoint(event)
```

### Manual Remediation

**1. Scale Throughput Units**:
```bash
az eventhubs namespace update \
    --name holidaypeakhub-eventhubs \
    --resource-group holidaypeakhub-rg \
    --capacity 20  # Increase TUs
```

**2. Add Partitions** (requires new Event Hub):
```bash
az eventhubs eventhub create \
    --name inventory-events-v2 \
    --namespace-name holidaypeakhub-eventhubs \
    --resource-group holidaypeakhub-rg \
    --partition-count 32  # Double partitions
```

**3. Optimize Partition Key**:
```python
# Before: Hot partition
event.partition_key = warehouse_id  # Few unique values

# After: Better distribution
event.partition_key = f"{warehouse_id}:{timestamp % 10}"  # More distribution
```

---

## Chaos Engineering Tests

### Event Hub Unavailability

**Objective**: Validate behavior when Event Hubs is unavailable.

**Test Procedure**:
1. Block Event Hub namespace endpoint
2. Send events (should queue locally or fail fast)
3. Restore connectivity
4. Validate events are delivered or explicitly failed

**Fault Injection**:
```json
{
  "name": "eventhub-outage-experiment",
  "steps": [
    {
      "name": "Block Event Hub",
      "actions": [
        {
          "type": "continuous",
          "name": "urn:csci:microsoft:networkSecurityGroup:blockTraffic/1.0",
          "duration": "PT5M",
          "parameters": [
            {"key": "destinationFilters", "value": "[\"servicebus.windows.net\"]"}
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
| Baseline | Weekly | 30 min | Test |
| High Load | Weekly | 60 min | Test |
| Hot Partition | Bi-weekly | 20 min | Test |
| Backpressure | Weekly | 15 min | Test |
| DLQ | Daily (CI) | 10 min | Test |
| SAGA | Before releases | 30 min | Staging |
| Chaos (Outage) | Monthly | 15 min | Staging |

---

## Success Criteria Summary

| Criterion | Target | Measurement |
|-----------|--------|-------------|
| Throughput | 10,000 msg/s | Event Hub metrics |
| P95 E2E Latency (Normal) | < 5s | Application Insights |
| Backpressure Activation | Yes | When throttled |
| Partition Balance | < 150% variance | Partition metrics |
| Message Loss | 0% | Consumer checkpoints |
| DLQ Processing | < 3 retries | Poison message tests |
| SAGA Completion | > 99% | SAGA monitor |

---

## Related Documentation
- [ADR-007: SAGA Choreography with Event Hubs](../adrs/adr-007-saga-choreography.md)
- [Sequence: Returns Support](../diagrams/sequence-returns-support.md)
- [Sequence: Inventory Health](../diagrams/sequence-inventory-health.md)
- [Azure Event Hubs Best Practices](https://learn.microsoft.com/azure/event-hubs/event-hubs-resource-manager-namespace-event-hub)
