# ADR-004: Builder Pattern for Agent Memory Configuration

**Status**: Accepted  
**Date**: 2024-12  
**Deciders**: Architecture Team, Ricardo Cataldi

## Context

Agents require flexible memory configuration:
- **Hot memory** (Redis): Recent user queries, session state
- **Warm memory** (Cosmos DB): Conversation history, user preferences
- **Cold memory** (Blob Storage): Uploaded files, archival logs

Different apps need different tier configurations:
- Cart Intelligence: Heavy hot memory (real-time updates)
- Profile Aggregation: Heavy warm memory (long-term history)
- Order Status: Heavy cold memory (historical orders)

Memory setup involves:
- Connection pooling
- Retry policies
- Serialization strategies
- TTL/eviction rules

## Decision

**Implement Builder Pattern for memory tier assembly.**

### Structure
```python
# lib/src/holiday_peak_lib/memory/builder.py
class MemoryBuilder:
    def with_hot_tier(self, redis_config: RedisConfig) -> Self:
        self._hot = HotMemory(redis_config)
        return self
    
    def with_warm_tier(self, cosmos_config: CosmosConfig) -> Self:
        self._warm = WarmMemory(cosmos_config)
        return self
    
    def with_cold_tier(self, blob_config: BlobConfig) -> Self:
        self._cold = ColdMemory(blob_config)
        return self
    
    def build(self) -> AgentMemory:
        return AgentMemory(self._hot, self._warm, self._cold)

# Usage in app
memory = (MemoryBuilder()
    .with_hot_tier(RedisConfig(host=..., ttl=300))
    .with_warm_tier(CosmosConfig(account=..., database=...))
    .with_cold_tier(BlobConfig(account=..., container=...))
    .build())
```

## Consequences

### Positive
- **Flexibility**: Apps configure only needed tiers
- **Readability**: Fluent API makes memory setup explicit
- **Testability**: Mock tiers injected via builder
- **Validation**: Builder enforces required configs before `build()`

### Negative
- **Verbosity**: More code than direct constructor
- **Immutability**: Builder state must be protected (mitigated by returning `Self`)
- **Discovery**: New developers may not find builder (mitigated by docs)

## Alternatives Considered

### Direct Constructor
```python
memory = AgentMemory(
    hot=HotMemory(...),
    warm=WarmMemory(...),
    cold=ColdMemory(...)
)
```
- **Pros**: Simpler, less code
- **Cons**: No step-by-step validation, harder to test partial configs

### Factory Method
```python
memory = MemoryFactory.create_for_app("cart-intelligence")
```
- **Pros**: One-liner per app
- **Cons**: Hardcodes configs in library; loses retailer customization

### Dependency Injection Container
- **Pros**: Centralized config
- **Cons**: Heavy dependency (FastAPI Depends); harder to debug

## Implementation Guidelines

### Builder Location
- **Library**: `lib/src/holiday_peak_lib/memory/builder.py`

### Tier Interfaces
Each tier implements:
```python
class MemoryTier(ABC):
    @abstractmethod
    async def get(self, key: str) -> Optional[dict]: ...
    
    @abstractmethod
    async def set(self, key: str, value: dict, ttl: Optional[int]) -> None: ...
    
    @abstractmethod
    async def delete(self, key: str) -> None: ...
```

### Auto-Promotion Logic
`AgentMemory` checks tiers in order (hot → warm → cold) and promotes frequently accessed keys:
```python
async def get(self, key: str) -> Optional[dict]:
    # Check hot
    value = await self._hot.get(key)
    if value:
        return value
    
    # Check warm, promote to hot
    value = await self._warm.get(key)
    if value:
        await self._hot.set(key, value, ttl=300)
        return value
    
    # Check cold, promote to warm
    value = await self._cold.get(key)
    if value:
        await self._warm.set(key, value)
        await self._hot.set(key, value, ttl=300)
        return value
    
    return None
```

### Testing
- Unit tests: Mock each tier, verify builder assembly
- Integration tests: Real Redis/Cosmos/Blob, verify promotion logic

## Related ADRs

- [ADR-008: Three-Tier Memory](adr-008-memory-tiers.md) — Memory architecture rationale
- [ADR-006: Agent Framework](adr-006-agent-framework.md) — Agent memory consumption
