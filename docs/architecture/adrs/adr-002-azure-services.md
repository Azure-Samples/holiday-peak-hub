# ADR-002: Azure Service Stack Selection

**Status**: Accepted  
**Date**: 2024-12  
**Deciders**: Architecture Team, Ricardo Cataldi

## Context

The accelerator requires cloud services for:
- **Memory**: Hot (ms latency), warm (session continuity), cold (archival)
- **Data**: Transactional OLTP, vector+hybrid search
- **Integration**: Async messaging, API gateway
- **Compute**: Container orchestration with auto-scaling
- **Observability**: Logging, metrics, tracing

Requirements:
- Enterprise SLAs and compliance (ISO, SOC2)
- Global distribution for multi-region retailers
- Managed services to minimize ops overhead
- Native Python SDK support

## Decision

**Adopt Azure-native services for all infrastructure:**

| Capability | Service | Justification |
|------------|---------|---------------|
| Hot Memory | Azure Cache for Redis | Sub-50ms P99, native Python SDK, clustering support |
| Warm Memory | Azure Cosmos DB | Global distribution, session consistency, hierarchical partition keys |
| Cold Memory | Azure Blob Storage | Lowest cost/GB, lifecycle policies, soft delete |
| Transactional DB | Azure Database for PostgreSQL | ACID guarantees, vector extension for hybrid scenarios |
| Vector Search | Azure AI Search | Vector+hybrid, semantic ranking, built-in chunking |
| Async Messaging | Azure Event Hubs | High throughput, Kafka-compatible, retention policies |
| API Gateway | Azure API Management | Rate limiting, OAuth, developer portal |
| Container Orchestration | Azure Kubernetes Service | Managed control plane, KEDA integration, canary deployments |
| Observability | Azure Monitor | Application Insights, Log Analytics, distributed tracing |

## Consequences

### Positive
- **Unified Ecosystem**: Single vendor for support, billing, IAM
- **Python SDKs**: First-class support for all services
- **Compliance**: Built-in certifications reduce audit burden
- **Networking**: Private endpoints, VNet integration out-of-box
- **Cost Management**: Azure Cost Management + Advisor for optimization

### Negative
- **Vendor Lock-in**: Migration to other clouds requires adapter rewrites
- **Cost**: Premium SKUs required for production SLAs (mitigated by dev/test pricing)
- **Learning Curve**: Teams unfamiliar with Azure require training

## Alternatives Considered

### AWS
- **Pros**: Market leader, mature services
- **Cons**: Agent Framework not AWS-optimized; weaker Foundry integration

### GCP
- **Pros**: Vertex AI for ML
- **Cons**: Smaller Azure AI ecosystem; no Foundry integration

### Multi-Cloud
- **Pros**: Avoid lock-in
- **Cons**: 3x ops complexity; SDK/IAM fragmentation; no cross-cloud orchestration

## Service-Specific Decisions

### Azure Cosmos DB
- **Mode**: NoSQL (Core SQL API)
- **Consistency**: Session (balance latency + consistency)
- **Partition Strategy**: Hierarchical partition keys for multi-tenant isolation
- **Rationale**: [Cosmos DB best practices](https://learn.microsoft.com/azure/cosmos-db/best-practices) for agent memory

### Azure Cache for Redis
- **Tier**: Standard (clustering for prod)
- **Eviction**: LRU for hot memory auto-pruning
- **Rationale**: Sub-10ms P99 latency, native Python SDK

### Azure AI Search
- **SKU**: Standard (semantic ranking + vector)
- **Index Strategy**: One index per app (e.g., `agent-catalog-search-retrieval`)
- **Rationale**: Vector+hybrid search for RAG, chunking built-in

### Azure Event Hubs
- **Tier**: Standard (1 MB/s throughput)
- **Partitions**: 32 (balance parallelism + cost)
- **Rationale**: SAGA choreography, outbox pattern support

## Implementation Notes

- Bicep templates provision all services with naming convention: `<app>-<service>-<version>`
- Managed identities for service-to-service auth (no connection strings in code)
- Private endpoints for production environments
- Cost alerts configured at 80% budget threshold

## Related ADRs

- [ADR-008: Three-Tier Memory](adr-008-memory-tiers.md) — Redis + Cosmos + Blob rationale
- [ADR-009: AKS Deployment](adr-009-aks-deployment.md) — Kubernetes choice
