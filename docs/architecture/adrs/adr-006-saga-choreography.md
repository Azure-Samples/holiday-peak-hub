# ADR-006: SAGA Choreography with Event Hubs

**Status**: Accepted  
**Date**: 2024-12

## Context

Services must coordinate across domains (e.g., order placement → inventory reservation → payment → shipping) without tight coupling.

## Decision

**Use SAGA choreography pattern with Azure Event Hubs** for async service coordination.

## Implementation Status (2026-04-09)

- **Implemented**: Event-driven pub/sub is active across CRUD and agent services through Azure Event Hubs producers, subscriptions, and lifespan wiring.
- **Namespace split complete**: Retail choreography topics bind to `EVENT_HUB_NAMESPACE`; platform job topics bind to `PLATFORM_JOBS_EVENT_HUB_NAMESPACE` (#735 closed).
- **Canonical coverage contract**: Topic-level topology status and wiring coverage tracked in [Event Hub topology matrix](../eventhub-topology-matrix.md).
- **Compensation framework**: Standardized in `holiday_peak_lib.utils.compensation` with `CompensationAction`, `CompensationResult`, and `execute_compensation`. Inventory reservation rollback serves as the reference integration path.
- **Event envelope versioning**: All retail and connector envelopes carry `schema_version: "1.0"` and are validated by `check_event_schema_contracts.py` in CI and pre-push.

## Compensation Semantics by Domain

| Domain | Compensation path | Status |
|--------|------------------|--------|
| Inventory | `execute_compensation` on reservation failure rolls back stock holds | Implemented (#447) |
| Checkout | Client-side cart rollback on payment/reservation failure | Implemented |
| Order | CRUD order status set to `cancelled`; no cross-service undo | Partial — manual |
| Logistics | No automated compensation; shipment cancellation is manual | Deferred |
| CRM | Stateless event consumers; no compensation needed | N/A |

## Event Topology Migration Policy

### Compatibility window

When adding, renaming, or retiring an Event Hub topic:

1. **Dual-publish phase** (minimum 1 deploy cycle): Publishers emit to both old and new topics. Consumers subscribe to both.
2. **Cutover**: Remove the old topic subscription from consumers. Confirm zero lag on the old consumer group via Azure Monitor.
3. **Cleanup**: Remove the old topic from IaC after confirming no active producers or consumers.

### Rollback steps

1. Re-add the old topic subscription to consumer `lifespan` wiring.
2. Re-enable dual-publish in the CRUD or agent publisher path.
3. Redeploy affected services. The shared `EventHubSettings` and `build_event_hub_consumer` patterns support runtime topic/consumer-group override via environment variables, enabling rollback without code changes.

### Constraints

- Never delete an Event Hub topic from IaC while there are active consumer groups with uncommitted checkpoints.
- The Standard tier 10-hub limit per namespace is enforced by the namespace split (#735). Adding new retail topics requires capacity review.
- Schema-breaking changes require a major version bump and updated contract gate fixtures under `lib/tests/fixtures/event_schema_contracts/`.

## Gap Tracking (2026-04-09)

Remaining implementation gaps tracked as separate issues:

- Product-events publisher coverage: #445
- Shipment-events subscriber wiring: #446

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
