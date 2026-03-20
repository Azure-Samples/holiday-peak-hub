# ADR-007: SAGA Choreography with Event Hubs

**Status**: Accepted  
**Date**: 2024-12

## Context

Services must coordinate across domains (e.g., order placement → inventory reservation → payment → shipping) without tight coupling.

## Decision

**Use SAGA choreography pattern with Azure Event Hubs** for async service coordination.

## Implementation Status (2026-03-19)

- **Implemented in part**: Event-driven pub/sub is active across CRUD and agent services through Azure Event Hubs producers, subscriptions, and lifespan wiring.
- **Coverage is mixed by topic**: Some topics are fully aligned publisher/subscriber paths, while others remain partially wired or intentionally pending.
- **Canonical coverage contract**: Topic-level topology status and wiring gaps are maintained in [Event Hub topology matrix](../eventhub-topology-matrix.md) and governed by issue #299.
- **Deferred/diverged**: Full end-to-end business sagas with uniform compensating transactions are not consistently implemented across domains; compensation remains service-specific.

### Pattern
Each service:
1. Publishes domain events to Event Hubs topic
2. Subscribes to events from other services
3. Implements compensating transactions for rollback

Example: Order placement saga
```
Order Service → OrderCreated event
  ↓
Inventory Service → InventoryReserved event
  ↓
Payment Service → PaymentProcessed event
  ↓
Logistics Service → ShipmentScheduled event
```

## Implementation

```python
# Publish event
await event_hub_producer.send_batch([
    EventData(json.dumps({"order_id": "123", "status": "created"}))
])

# Subscribe
async with event_hub_consumer:
    async for event in event_hub_consumer:
        await handle_order_created(event)
```

## Consequences

**Positive**: Decoupling, independent deployment, fault tolerance  
**Negative**: Eventual consistency, complex debugging, duplicate handling required

## Related ADRs
- [ADR-002: Azure Services](adr-002-azure-services.md)
