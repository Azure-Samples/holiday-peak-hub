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
- Connection pooling (Redis/Cosmos/Blob)
- Cascading read/write rules
- Serialization strategies
- TTL/eviction rules

## Decision

**Implement Builder Pattern for memory tier assembly.**

### Structure
```python
# lib/src/holiday_peak_lib/agents/memory/builder.py
class MemoryBuilder:
    def with_hot(self, hot: HotMemory) -> "MemoryBuilder":
        self._hot = hot
        return self

    def with_warm(self, warm: WarmMemory) -> "MemoryBuilder":
        self._warm = warm
        return self

    def with_cold(self, cold: ColdMemory) -> "MemoryBuilder":
        self._cold = cold
        return self

    def with_rules(self, **kwargs) -> "MemoryBuilder":
        self._rules = MemoryRules(**kwargs)
        return self

    def build(self) -> MemoryClient:
        return MemoryClient(hot=self._hot, warm=self._warm, cold=self._cold, rules=self._rules)

# Usage in app
memory = (
    MemoryBuilder()
    .with_hot(HotMemory(redis_url))
    .with_warm(WarmMemory(cosmos_uri, database, container))
    .with_cold(ColdMemory(blob_account_url, container))
    .with_rules(read_fallback=True, promote_on_read=True, write_through=True)
    .build()
)
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
Each tier implements its own storage contract:
```python
class HotMemory(Protocol):
    async def get(self, key: str) -> Optional[str]: ...
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None: ...
    async def delete(self, key: str) -> None: ...

class WarmMemory(Protocol):
    async def read(self, key: str) -> Optional[str]: ...
    async def upsert(self, key: str, value: str) -> None: ...
    async def delete(self, key: str) -> None: ...

class ColdMemory(Protocol):
    async def download_text(self, key: str) -> Optional[str]: ...
    async def upload_text(self, key: str, value: str) -> None: ...
    async def delete(self, key: str) -> None: ...
```

### Cascading Rules (Promotion)
`MemoryClient` checks tiers in order (hot → warm → cold) and optionally promotes on read:
```python
async def get(self, key: str) -> Optional[str]:
    value = await self._hot.get(key)
    if value is not None:
        return value

    value = await self._warm.read(key)
    if value is not None and self._rules.promote_on_read:
        await self._hot.set(key, value, ttl=self._rules.hot_ttl)
        return value

    value = await self._cold.download_text(key)
    if value is not None and self._rules.promote_on_read:
        await self._warm.upsert(key, value)
        await self._hot.set(key, value, ttl=self._rules.hot_ttl)
        return value

    return value
```

### Tiered Eviction (Demotion Extension Point)
Eviction is not built-in, but the builder supports injecting policy logic on top of `MemoryClient`.
Implement a policy that evaluates per-key metadata (last access, size, compliance) and demotes:

- Hot → Warm for cold keys or large payloads
- Warm → Cold for archival keys or stale data

### Testing
- Unit tests: Mock each tier, verify builder assembly
- Integration tests: Real Redis/Cosmos/Blob, verify promotion and pooling settings

## Related ADRs

- [ADR-008: Three-Tier Memory](adr-008-memory-tiers.md) — Memory architecture rationale
- [ADR-006: Agent Framework](adr-006-agent-framework.md) — Agent memory consumption
