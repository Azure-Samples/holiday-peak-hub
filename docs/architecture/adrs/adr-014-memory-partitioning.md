# ADR-014: Memory Partitioning and Data Placement Strategy

**Status**: Accepted  
**Date**: 2026-01  
**Deciders**: Architecture Team

## Context

The three-tier memory architecture (Redis, Cosmos DB, Blob Storage) requires clear rules for data placement. Without guidelines, teams will inconsistently use tiers, leading to:
- **Over-provisioning**: Storing cold data in expensive Redis
- **Under-performance**: Hot data in Blob Storage causing latency spikes
- **Cost overruns**: Not leveraging tier economics
- **Compliance gaps**: PII in wrong tier with inadequate retention

**Key Questions**:
- What data belongs in each tier?
- When should data be promoted/demoted?
- How do we handle PII and compliance?
- What are the eviction and TTL policies?

## Decision

**Define clear partitioning rules based on access patterns, data lifecycle, and compliance requirements.**

### Tier Selection Matrix

| Data Type | Access Frequency | Latency SLA | Retention | Tier | TTL/Eviction |
|-----------|------------------|-------------|-----------|------|--------------|
| Session state | Per-request | < 50ms | 15min | **Hot** | 15min TTL |
| Cart contents | Multiple per session | < 100ms | 24h | **Hot** | 24h TTL |
| Recent search queries | Multiple per session | < 100ms | 5min | **Hot** | 5min TTL |
| User preferences | Once per session | < 500ms | 90 days | **Warm** | No TTL |
| Conversation history | 1-2x per session | < 500ms | 30 days | **Warm** | 30d TTL |
| Order history | Rare | < 2s | 7 years | **Cold** | Lifecycle policy |
| Product images | Rare | < 5s | Indefinite | **Cold** | No expiration |
| System logs | Rare | < 10s | 90 days | **Cold** | 90d lifecycle |
| Analytics snapshots | Batch only | < 30s | 1 year | **Cold** | 1y lifecycle |

### Hot Memory (Redis)

**Purpose**: Sub-50ms access for active sessions and real-time state.

**Use Cases**:
```python
# Session state
redis.set(f"session:{session_id}", json.dumps(session_data), ex=900)  # 15min TTL

# Active cart
redis.set(f"cart:{user_id}", json.dumps(cart), ex=86400)  # 24h TTL

# Rate limiting
redis.incr(f"ratelimit:{user_id}:{endpoint}", ex=60)

# Recent queries (autocomplete)
redis.lpush(f"queries:{user_id}", query)
redis.ltrim(f"queries:{user_id}", 0, 9)  # Keep last 10
redis.expire(f"queries:{user_id}", 300)  # 5min TTL
```

**Configuration**:
```python
from holiday_peak_lib.agents.memory import HotMemory

hot = HotMemory(
    redis_url=os.getenv("REDIS_URL"),
    default_ttl=900,  # 15min default
    max_connections=50,
    socket_timeout=1.0,
    retry_on_timeout=True
)
```

**Eviction Policy**: Volatile LRU (evict keys with TTL, least recently used)

**Size Limits**: 
- **Max key size**: 1MB (enforce at application level)
- **Max memory**: 4GB per instance (Redis maxmemory)
- **Eviction**: 10% of data when memory > 90%

### Warm Memory (Cosmos DB)

**Purpose**: 100-500ms access for structured data with queries.

**Use Cases**:
```python
# User profile
await cosmos.upsert({
    "id": f"profile:{user_id}",
    "partition_key": user_id,
    "preferences": {...},
    "segments": ["vip", "frequent_buyer"],
    "created_at": "2026-01-29T00:00:00Z",
    "ttl": 7776000  # 90 days
})

# Conversation history
await cosmos.upsert({
    "id": f"conversation:{conversation_id}",
    "partition_key": user_id,
    "turns": [...],
    "metadata": {...},
    "ttl": 2592000  # 30 days
})

# Agent state (cross-request)
await cosmos.upsert({
    "id": f"agent_state:{agent_id}:{session_id}",
    "partition_key": agent_id,
    "state": {...},
    "ttl": 3600  # 1 hour
})
```

**Partition Key Strategy**:
- **User-scoped data**: `user_id` (profiles, conversations)
- **Agent-scoped data**: `agent_id` (agent state)
- **Order-scoped data**: `order_id` (order details)
- **Hierarchical Partition Keys**: For data > 20GB per logical partition

**TTL Configuration**:
```python
from holiday_peak_lib.agents.memory import WarmMemory

warm = WarmMemory(
    cosmos_account_uri=os.getenv("COSMOS_ACCOUNT_URI"),
    database_name=os.getenv("COSMOS_DATABASE"),
    container_name=os.getenv("COSMOS_CONTAINER"),
    enable_ttl=True,  # Container-level TTL
    default_ttl=2592000  # 30 days
)
```

**Indexing Policy**:
```json
{
  "indexingMode": "consistent",
  "includedPaths": [
    {"path": "/user_id/?"},
    {"path": "/created_at/?"},
    {"path": "/segments/*"}
  ],
  "excludedPaths": [
    {"path": "/state/*"},
    {"path": "/metadata/*"}
  ]
}
```

### Cold Memory (Blob Storage)

**Purpose**: Seconds-latency access for large, infrequently accessed data.

**Use Cases**:
```python
# Uploaded files (CSV, images)
await blob.upload(
    container="uploads",
    blob_name=f"{user_id}/{upload_id}.csv",
    data=file_bytes,
    metadata={"user_id": user_id, "upload_date": "2026-01-29"}
)

# Order archives (compliance)
await blob.upload(
    container="orders-archive",
    blob_name=f"{year}/{month}/{order_id}.json",
    data=json.dumps(order),
    tier="Cool"  # Cool tier for 7-year retention
)

# System logs (observability)
await blob.append(
    container="logs",
    blob_name=f"{service}/{date}/app.log",
    data=log_entry
)

# Model artifacts (agent snapshots)
await blob.upload(
    container="models",
    blob_name=f"agents/{agent_id}/snapshot-{version}.pkl",
    data=pickle.dumps(agent_state)
)
```

**Lifecycle Policy**:
```json
{
  "rules": [
    {
      "name": "move-to-cool-after-30d",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "tierToCool": {"daysAfterModificationGreaterThan": 30}
          }
        },
        "filters": {"blobTypes": ["blockBlob"], "prefixMatch": ["uploads/"]}
      }
    },
    {
      "name": "archive-orders-after-1y",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "tierToArchive": {"daysAfterModificationGreaterThan": 365}
          }
        },
        "filters": {"prefixMatch": ["orders-archive/"]}
      }
    },
    {
      "name": "delete-logs-after-90d",
      "type": "Lifecycle",
      "definition": {
        "actions": {
          "baseBlob": {
            "delete": {"daysAfterModificationGreaterThan": 90}
          }
        },
        "filters": {"prefixMatch": ["logs/"]}
      }
    }
  ]
}
```

### Promotion and Demotion Rules

**Automatic Promotion** (Cold → Warm → Hot):
```python
async def get_with_promotion(key: str) -> dict:
    """Fetch data and promote if access frequency warrants it."""
    
    # Try hot first
    if data := await hot.get(key):
        return data
    
    # Try warm
    if data := await warm.read(key):
        access_count = await increment_access_counter(key)
        
        # Promote to hot if accessed > 10x in 5min
        if access_count > 10:
            await hot.set(key, data, ttl=300)
        
        return data
    
    # Fallback to cold
    data = await cold.download(key)
    return data
```

**Automatic Demotion** (Hot → Warm → Cold):
```python
# Hot → Warm: TTL expiration (Redis automatically evicts)
# Warm → Cold: Application-level archival
async def archive_old_conversations():
    """Move conversations older than 30 days to blob storage."""
    old_conversations = await warm.query(
        "SELECT * FROM c WHERE c.created_at < @cutoff",
        parameters=[("@cutoff", (datetime.now() - timedelta(days=30)).isoformat())]
    )
    
    for conv in old_conversations:
        # Upload to cold
        await cold.upload(
            container="conversations-archive",
            blob_name=f"{conv['user_id']}/{conv['id']}.json",
            data=json.dumps(conv)
        )
        
        # Delete from warm
        await warm.delete(conv["id"])
```

### PII and Compliance

**Data Classification**:
- **PII (Personally Identifiable Information)**: User name, email, address
- **Sensitive PII**: Payment info, SSN, health data
- **Non-PII**: Product catalog, system metrics

**Storage Rules**:
```python
# Encrypt PII at rest and in transit
PII_FIELDS = ["email", "phone", "address", "payment_method"]

async def store_user_profile(profile: dict):
    """Store profile with PII encryption."""
    
    # Encrypt PII fields
    for field in PII_FIELDS:
        if field in profile:
            profile[field] = encrypt(profile[field], key=os.getenv("ENCRYPTION_KEY"))
    
    # Store in warm (not hot, due to compliance)
    await warm.upsert({
        "id": f"profile:{profile['user_id']}",
        "partition_key": profile["user_id"],
        **profile,
        "ttl": 7776000,  # 90 days
        "_encrypted": True
    })
```

**Right to Deletion (GDPR, CCPA)**:
```python
async def delete_user_data(user_id: str):
    """Delete all user data across all tiers."""
    
    # Hot
    await hot.delete_pattern(f"*:{user_id}:*")
    
    # Warm
    await warm.delete_by_partition_key(user_id)
    
    # Cold
    blobs = await cold.list(prefix=f"{user_id}/")
    for blob in blobs:
        await cold.delete(blob)
```

## Consequences

### Positive
- **Cost optimization**: 70% savings by using appropriate tiers
- **Performance**: Sub-50ms for hot, < 500ms for warm
- **Compliance**: Clear PII handling and retention
- **Scalability**: Automatic eviction prevents memory exhaustion
- **Observability**: Access patterns inform tier assignment

### Negative
- **Complexity**: Three tiers to manage vs one database
- **Promotion overhead**: Access counting adds latency
- **Data movement**: Promotion/demotion requires background jobs
- **Consistency**: Data may exist in multiple tiers temporarily

### Risk Mitigation
- **Idempotent operations**: Retry-safe promotion/demotion
- **Monitoring**: Track tier distribution and access patterns
- **Fallback**: If hot/warm unavailable, degrade gracefully to cold
- **Testing**: Chaos engineering to simulate tier failures

## Implementation Guidelines

### Memory Builder
```python
from holiday_peak_lib.agents import AgentBuilder
from holiday_peak_lib.agents.memory import HotMemory, WarmMemory, ColdMemory

agent = (AgentBuilder()
    .with_memory(
        hot=HotMemory(redis_url=os.getenv("REDIS_URL"), default_ttl=900),
        warm=WarmMemory(
            cosmos_account_uri=os.getenv("COSMOS_ACCOUNT_URI"),
            database_name="retail_db",
            container_name="agent_memory",
            enable_ttl=True
        ),
        cold=ColdMemory(
            blob_account_url=os.getenv("BLOB_ACCOUNT_URL"),
            container_name="cold-storage"
        )
    )
    .with_promotion_rules(access_threshold=10, window_seconds=300)
    .build())
```

### Observability
```python
# Track tier utilization
metrics.gauge("memory.hot.size_mb", redis.info()["used_memory_human"])
metrics.gauge("memory.warm.ru_per_sec", cosmos.get_metrics()["request_units"])
metrics.gauge("memory.cold.gb_stored", blob.get_account_info()["total_gb"])

# Track data movement
metrics.counter("memory.promotion", {"from": "warm", "to": "hot"})
metrics.counter("memory.demotion", {"from": "hot", "to": "warm"})
```

## Alternatives Considered

### Single-Tier (Cosmos DB Only)
**Pros**: Simple, single query interface  
**Cons**: 10x cost vs tiered, no sub-50ms guarantees  
**Decision**: Cost prohibitive at scale.

### Two-Tier (Redis + Blob)
**Pros**: Simpler than three tiers  
**Cons**: No structured queries, Blob too slow for warm data  
**Decision**: Warm tier essential for conversation history and profiles.

### Application-Managed Promotion
**Pros**: Full control over data movement  
**Cons**: Complex, error-prone, requires custom scheduler  
**Decision**: Automatic promotion via access patterns is more maintainable.

## Related ADRs
- [ADR-008: Three-Tier Memory Architecture](adr-008-memory-tiers.md)
- [ADR-004: Builder Pattern for Agent Memory Configuration](adr-004-builder-pattern-memory.md)
- [ADR-002: Azure Service Stack Selection](adr-002-azure-services.md)

## References
- [Azure Cosmos DB TTL](https://learn.microsoft.com/azure/cosmos-db/nosql/time-to-live)
- [Azure Blob Storage Lifecycle Management](https://learn.microsoft.com/azure/storage/blobs/lifecycle-management-overview)
- [Redis Eviction Policies](https://redis.io/docs/manual/eviction/)
- [GDPR Right to Erasure](https://gdpr-info.eu/art-17-gdpr/)
