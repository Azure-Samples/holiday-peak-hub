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

## Cascading Rules

Frequently accessed data can be promoted hot ← warm ← cold via `MemoryClient` rules.

## Implementation

Via Builder pattern (see ADR-004):
```python
memory = (MemoryBuilder()
    .with_hot(HotMemory(redis_url))
    .with_warm(WarmMemory(cosmos_uri, database, container))
    .with_cold(ColdMemory(blob_account_url, container))
    .with_rules(read_fallback=True, promote_on_read=True, write_through=True)
    .build())
```

## Pooling and Transport

Each tier supports connection pooling/transport tuning:
- **Hot**: Redis connection pool and socket timeouts
- **Warm**: Cosmos client connection limits and client kwargs
- **Cold**: Blob transport pooling and timeouts

## Tiered Eviction (Extension)

Demotion hot → warm → cold is an extension point. Business rules should consider:
- Access frequency and recency
- Payload size
- Compliance/retention requirements
- SLA or latency constraints

## Consequences

**Positive**: 70% cost reduction vs all-Redis, optimized latency  
**Negative**: Complexity in tier management, cold start delays, policy tuning for promotion/demotion

## Related ADRs
- [ADR-004: Builder Pattern](adr-004-builder-pattern-memory.md)
- [ADR-002: Azure Services](adr-002-azure-services.md)
