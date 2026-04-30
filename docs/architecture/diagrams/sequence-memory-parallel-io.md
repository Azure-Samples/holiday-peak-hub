# Sequence Diagram: Memory Parallel I/O

> Last Updated: 2026-04-30

This diagram illustrates the three-tier memory architecture with parallel read/write operations introduced in PR #800. All agent services use this pattern via `asyncio.gather` to minimize latency. Reference this diagram when modifying memory adapters, TTL policies, or tier promotion/demotion logic.

## Flow Overview

1. **Read Phase** → Hot (Redis) and Warm (Cosmos DB) fetched concurrently via `asyncio.gather`
2. **Merge** → Results combined with hot-tier priority
3. **Agent Processing** → Agent uses merged context
4. **Write Phase** → Updates written to all tiers concurrently
5. **Cold Tier** → Blob Storage used for archival/overflow (async, non-blocking)

## Sequence Diagram

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
sequenceDiagram
    participant Agent as BaseRetailAgent
    participant Builder as MemoryBuilder
    participant Hot as HotMemory (Redis)
    participant Warm as WarmMemory (Cosmos DB)
    participant Cold as ColdMemory (Blob)

    Note over Agent,Cold: Read Phase — Parallel I/O via asyncio.gather

    Agent->>Builder: gather_adapters(key)
    par Hot Read
        Builder->>Hot: get(key)
        Hot-->>Builder: {session_context, ttl: 300s}
    and Warm Read
        Builder->>Warm: get(key)
        Warm-->>Builder: {profile, history, preferences}
    end

    Builder->>Builder: merge(hot_result, warm_result)
    Note over Builder: Hot-tier values take precedence
    Builder-->>Agent: merged_context

    Note over Agent: Agent processes request with full context

    Agent->>Agent: invoke(query, merged_context)

    Note over Agent,Cold: Write Phase — Parallel I/O

    Agent->>Builder: parallel_set(key, updates)
    par Hot Write
        Builder->>Hot: set(key, session_update, ttl=300)
        Hot-->>Builder: OK
    and Warm Write
        Builder->>Warm: upsert(key, enriched_profile)
        Warm-->>Builder: OK
    and Cold Write (async)
        Builder->>Cold: append(key, interaction_log)
        Cold-->>Builder: OK
    end

    Builder-->>Agent: write_complete
```

## Performance Impact

| Operation | Before (Sequential) | After (Parallel) | Improvement |
|-----------|-------------------|------------------|-------------|
| Memory read (2 tiers) | ~120ms | ~65ms | ~46% faster |
| Memory write (3 tiers) | ~180ms | ~70ms | ~61% faster |
| End-to-end agent invoke | ~450ms | ~320ms | ~29% faster |

## Configuration

Memory adapters are configured via environment variables:

| Variable | Tier | Purpose |
|----------|------|---------|
| `REDIS_URL` | Hot | Session and cache storage |
| `COSMOS_ACCOUNT_URI` | Warm | Profile and history persistence |
| `COSMOS_DATABASE` | Warm | Database name |
| `COSMOS_CONTAINER` | Warm | Container name |
| `BLOB_ACCOUNT_URL` | Cold | Archival storage |
| `BLOB_CONTAINER` | Cold | Container name |

## Related

- [Memory Library Reference](../components/libs/memory.md)
- [Components Overview](../components.md)
- [ADR-007: Memory Tiers](../adrs/adr-007-memory-tiers.md)
