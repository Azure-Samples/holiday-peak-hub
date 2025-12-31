# ADR-008: Three-Tier Memory Architecture

**Status**: Accepted  
**Date**: 2024-12

## Context

Agents require memory with different latency/cost trade-offs:
- **Session state**: Sub-50ms access (current cart, user context)
- **Conversation history**: 100-500ms acceptable (past 30 days)
- **Archival**: Seconds acceptable (orders, uploads beyond 30 days)

## Decision

**Implement three-tier memory**: Redis (hot), Cosmos DB (warm), Blob Storage (cold).

| Tier | Service | Latency | Cost/GB | Use Case |
|------|---------|---------|---------|----------|
| Hot | Redis | <50ms | $$$$ | Session state, recent queries |
| Warm | Cosmos | 100-500ms | $$ | Conversation history, preferences |
| Cold | Blob | Seconds | $ | Uploaded files, archival logs |

## Auto-Promotion

Frequently accessed data promoted hot ← warm ← cold.

## Implementation

Via Builder pattern (see ADR-004):
```python
memory = (MemoryBuilder()
    .with_hot_tier(RedisConfig(...))
    .with_warm_tier(CosmosConfig(...))
    .with_cold_tier(BlobConfig(...))
    .build())
```

## Consequences

**Positive**: 70% cost reduction vs all-Redis, optimized latency  
**Negative**: Complexity in tier management, cold start delays

## Related ADRs
- [ADR-004: Builder Pattern](adr-004-builder-pattern-memory.md)
- [ADR-002: Azure Services](adr-002-azure-services.md)
