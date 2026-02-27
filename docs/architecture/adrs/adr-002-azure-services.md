# ADR-002: Azure Service Stack Selection

**Status**: Accepted  
**Date**: 2024-12  
**Updated**: 2026-02  
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
| Transactional DB | Azure Database for PostgreSQL Flexible Server | ACID transactions, relational constraints, joins for CRUD workflows |
| Vector Search | Azure AI Search | Vector+hybrid, semantic ranking, built-in chunking |
| Async Messaging | Azure Event Hubs | High throughput, Kafka-compatible, retention policies |
| API Gateway | Azure API Management | Rate limiting, OAuth, developer portal |
| Container Orchestration | Azure Kubernetes Service | Managed control plane, KEDA integration, 3 dedicated node pools |
| Container Registry | Azure Container Registry (Premium) | Private endpoints, zone-redundant, AcrPull via Managed Identity |
| AI/ML Platform | Azure AI Foundry | Foundry project, model management, agent orchestration |
| Secrets Management | Azure Key Vault (Premium) | HSM-backed secrets, certificates, purge protection |
| Observability | Azure Monitor | Application Insights, Log Analytics, distributed tracing |
| Networking | Azure Virtual Network | 5 subnets, 5 NSGs, 8 Private DNS Zones, Private Endpoints |

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
- **Agent memory containers**: `warm-{agent}-chat-memory` per agent service
- **Rationale**: Optimized for warm memory state and session history in agent workflows. See [Cosmos DB best practices](https://learn.microsoft.com/azure/cosmos-db/best-practices).

### Azure Database for PostgreSQL Flexible Server
- **Mode**: Managed PostgreSQL 16 (Flexible Server)
- **Connectivity**: Private Endpoint + private DNS in shared VNet
- **Database**: `holiday_peak_crud`
- **Rationale**: CRUD service requires transactional consistency, relational querying, and ACID semantics.

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

- All infrastructure provisioned via Bicep using [Azure Verified Modules (AVM)](https://azure.github.io/Azure-Verified-Modules/)
- Naming convention: `{projectName}-{environment}-{service}` (e.g., `holidaypeakhub-dev-aks`)
- Managed identities for service-to-service auth (no connection strings in code)
- Private endpoints for all data services in production (8 Private DNS Zones)
- Cost alerts configured at 80% budget threshold
- Two provisioning strategies: demo (per-service standalone) and production (shared infrastructure)

## Related ADRs

- [ADR-008: Three-Tier Memory](adr-008-memory-tiers.md) — Redis + Cosmos + Blob rationale
- [ADR-009: AKS Deployment](adr-009-aks-deployment.md) — Kubernetes choice and node pool strategy
- [ADR-014: Memory Partitioning](adr-014-memory-partitioning.md) — Data placement rules
- [ADR-021: azd-First Deployment](adr-021-azd-first-deployment.md) — Provisioning and CI/CD strategy
