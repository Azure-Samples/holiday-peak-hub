# Infrastructure Summary

Architecture decisions, deployment relationships, and implementation details for Holiday Peak Hub.

---

## Deployment Architecture

### High-Level Overview

```mermaid
graph TB
    subgraph "Azure Subscription"
        subgraph RG["Resource Group: holidaypeakhub-{env}-rg"]
            subgraph Network["Network Layer"]
                VNet["VNet<br/>10.0.0.0/16"]
                NSG1["NSG: aks-system"]
                NSG2["NSG: aks-agents"]
                NSG3["NSG: aks-crud"]
                NSG4["NSG: apim"]
                NSG5["NSG: private-endpoints"]
            end

            subgraph DNS["Private DNS Zones (7)"]
                DNS1["privatelink.documents.azure.com"]
                DNS2["privatelink.redis.cache.windows.net"]
                DNS3["privatelink.blob.core.windows.net"]
                DNS4["privatelink.servicebus.windows.net"]
                DNS5["privatelink.vaultcore.azure.net"]
                DNS6["privatelink.azurecr.io"]
                DNS7["privatelink.cognitiveservices.azure.com"]
            end

            subgraph Compute["Compute Layer"]
                AKS["AKS Cluster<br/>3 Node Pools"]
                APIM["API Management"]
                SWA["Static Web App<br/>(Next.js UI)"]
            end

            subgraph Data["Data Layer"]
                Cosmos["Cosmos DB<br/>12 Containers"]
                Redis["Redis Cache<br/>Premium P1"]
                Storage["Storage Account<br/>Blob"]
                EH["Event Hubs<br/>5 Topics"]
            end

            subgraph Security["Security & Identity"]
                KV["Key Vault<br/>Premium"]
                RBAC["6 RBAC<br/>Assignments"]
            end

            subgraph AI["AI Layer"]
                Foundry["AI Foundry<br/>Project"]
            end

            subgraph Observability["Observability"]
                LA["Log Analytics"]
                AI_I["App Insights"]
                ACR["Container Registry<br/>Premium"]
            end
        end
    end

    VNet --> AKS
    VNet --> APIM
    DNS --> Data
    DNS --> KV
    DNS --> ACR
    DNS --> Foundry
    AKS --> RBAC
    RBAC --> Cosmos
    RBAC --> Redis
    RBAC --> Storage
    RBAC --> EH
    RBAC --> KV
    RBAC --> ACR
    AKS --> LA
    AKS --> AI_I
```

---

## Deployment Strategies

### Strategy Comparison

```mermaid
graph LR
    subgraph "Strategy 1: Shared Infrastructure (Production)"
        SI[Shared Infra<br/>1 deployment] --> AKS1[Shared AKS]
        AKS1 --> S1[CRUD Service]
        AKS1 --> S2[Agent 1..21]
        SI --> CosmosS[Shared Cosmos DB<br/>12 containers]
        SI --> RedisS[Shared Redis<br/>DB 0-21]
        SI --> StorageS[Shared Storage<br/>21 blob containers]
    end
```

```mermaid
graph LR
    subgraph "Strategy 2: Per-Service Standalone (Demo)"
        A1[Agent Module 1] --> C1[Own Cosmos DB]
        A1 --> R1[Own Redis]
        A1 --> S1a[Own Storage]
        A1 --> AI1[Own OpenAI]
        A1 --> AKS1[Own AKS]

        A2[Agent Module 2] --> C2[Own Cosmos DB]
        A2 --> R2[Own Redis]
        A2 --> S2a[Own Storage]
        A2 --> AI2[Own OpenAI]
        A2 --> AKS2[Own AKS]

        AN[Agent Module N] --> CN[Own Cosmos DB]
        AN --> RN[Own Redis]
        AN --> SN[Own Storage]
        AN --> AIN[Own OpenAI]
        AN --> AKSN[Own AKS]
    end
```

---

## Shared Infrastructure Module

### Resource Dependency Graph

```mermaid
graph TD
    NSGs["5 × NSGs"] --> VNet
    VNet --> PESubnet["PE Subnet"]
    VNet --> AKSSubnets["AKS Subnets (3)"]
    VNet --> APIMSubnet["APIM Subnet"]

    PESubnet --> PrivateDNS["7 × Private DNS Zones"]
    PrivateDNS --> VNetLinks["VNet Links"]

    LogAnalytics["Log Analytics"] --> AppInsights["App Insights"]

    PESubnet --> ACR_PE["ACR Private Endpoint"]
    PESubnet --> Cosmos_PE["Cosmos DB Private Endpoint"]
    PESubnet --> Redis_PE["Redis Private Endpoint"]
    PESubnet --> Storage_PE["Storage Private Endpoint"]
    PESubnet --> EH_PE["Event Hubs Private Endpoint"]
    PESubnet --> KV_PE["Key Vault Private Endpoint"]

    ACR["ACR (Premium)"] --> ACR_PE
    Cosmos["Cosmos DB"] --> Cosmos_PE
    Redis["Redis Cache"] --> Redis_PE
    Storage["Storage Account"] --> Storage_PE
    EventHubs["Event Hubs"] --> EH_PE
    KeyVault["Key Vault"] --> KV_PE

    KeyVault --> AIFoundry["AI Foundry Project"]
    Storage --> AIFoundry
    Cosmos --> AIFoundry

    AKSSubnets --> AKS["AKS Cluster"]
    LogAnalytics --> AKS
    APIMSubnet --> APIM["API Management"]

    AKS --> RBAC_ACR["RBAC: AcrPull"]
    AKS --> RBAC_Cosmos["RBAC: Cosmos Data Contributor"]
    AKS --> RBAC_EH_S["RBAC: EventHub Sender"]
    AKS --> RBAC_EH_R["RBAC: EventHub Receiver"]
    AKS --> RBAC_KV["RBAC: KeyVault Secrets User"]
    AKS --> RBAC_Storage["RBAC: Blob Data Contributor"]

    RBAC_ACR --> ACR
    RBAC_Cosmos --> Cosmos
    RBAC_EH_S --> EventHubs
    RBAC_EH_R --> EventHubs
    RBAC_KV --> KeyVault
    RBAC_Storage --> Storage
```

---

## AKS Cluster Architecture

```mermaid
graph TB
    subgraph AKS["AKS Cluster (holidaypeakhub-{env}-aks)"]
        subgraph SystemPool["System Pool<br/>Standard_D8ds_v5<br/>Subnet: aks-system (10.0.0.0/22)"]
            CoreDNS["CoreDNS"]
            Metrics["Metrics Server"]
            CSI["CSI Drivers"]
        end

        subgraph AgentsPool["Agents Pool<br/>Standard_D8ds_v5<br/>Subnet: aks-agents (10.0.4.0/22)<br/>Taint: workload=agents:NoSchedule"]
            CRM["CRM Agents (4)"]
            ECOM["eCommerce Agents (5)"]
            INV["Inventory Agents (4)"]
            LOG["Logistics Agents (4)"]
            PM["Product Mgmt Agents (4)"]
        end

        subgraph CrudPool["CRUD Pool<br/>Standard_D8ds_v5<br/>Subnet: aks-crud (10.0.8.0/24)<br/>Taint: workload=crud:NoSchedule"]
            CRUD["CRUD Service"]
        end
    end

    APIM["APIM Gateway"] --> CrudPool
    APIM --> AgentsPool
    SWA["Static Web App (UI)"] --> APIM
```

---

## Three-Tier Memory Architecture

```mermaid
graph LR
    subgraph Agent["Agent Service"]
        Handler["Request Handler"]
    end

    subgraph Hot["Hot Tier (Redis)"]
        R["Redis Premium<br/>DB 0: CRUD<br/>DB 1-21: Agents<br/>TTL: minutes"]
    end

    subgraph Warm["Warm Tier (Cosmos DB)"]
        C["Cosmos DB<br/>Container: warm-{agent}-chat-memory<br/>Partition: /session_id<br/>TTL: hours-days"]
    end

    subgraph Cold["Cold Tier (Blob Storage)"]
        B["Blob Storage<br/>Container: cold-{agent}-chat-memory<br/>Retention: permanent"]
    end

    Handler -->|"Read/Write<br/>< 1ms"| R
    Handler -->|"Read/Write<br/>< 10ms"| C
    Handler -->|"Archive<br/>async"| B

    R -->|"Eviction"| C
    C -->|"Archive"| B
```

---

## Event-Driven Communication

```mermaid
graph LR
    subgraph Producers
        CRUD["CRUD Service"]
        Agents["Agent Services"]
    end

    subgraph EH["Event Hubs Namespace"]
        OE["order-events<br/>(4 partitions)"]
        IE["inventory-events<br/>(4 partitions)"]
        SE["shipment-events<br/>(4 partitions)"]
        PE["payment-events<br/>(4 partitions)"]
        UE["user-events<br/>(2 partitions)"]
    end

    subgraph Consumers
        OrdStatus["ecommerce-order-status"]
        InvAlert["inventory-alerts-triggers"]
        InvJIT["inventory-jit-replenishment"]
        LogETA["logistics-eta-computation"]
        LogRoute["logistics-route-issue-detection"]
        CRMCamp["crm-campaign-intelligence"]
        CRMSeg["crm-segmentation-personalization"]
    end

    CRUD --> OE
    CRUD --> IE
    CRUD --> PE
    Agents --> SE
    Agents --> UE

    OE --> OrdStatus
    IE --> InvAlert
    IE --> InvJIT
    SE --> LogETA
    SE --> LogRoute
    UE --> CRMCamp
    UE --> CRMSeg
```

---

## Private Endpoint Topology

```mermaid
graph TB
    subgraph VNet["VNet: 10.0.0.0/16"]
        subgraph PESubnet["Private Endpoints Subnet<br/>10.0.10.0/24"]
            PE_ACR["PE: ACR"]
            PE_Cosmos["PE: Cosmos DB"]
            PE_Redis["PE: Redis"]
            PE_Storage["PE: Storage (Blob)"]
            PE_EH["PE: Event Hubs"]
            PE_KV["PE: Key Vault"]
            PE_AI["PE: AI Services"]
        end

        subgraph AKSSubnets["AKS Subnets"]
            AKS_Sys["aks-system<br/>10.0.0.0/22"]
            AKS_Agents["aks-agents<br/>10.0.4.0/22"]
            AKS_CRUD["aks-crud<br/>10.0.8.0/24"]
        end
    end

    subgraph DNSZones["Private DNS Zones"]
        Z1["privatelink.azurecr.io"]
        Z2["privatelink.documents.azure.com"]
        Z3["privatelink.redis.cache.windows.net"]
        Z4["privatelink.blob.core.windows.net"]
        Z5["privatelink.servicebus.windows.net"]
        Z6["privatelink.vaultcore.azure.net"]
        Z7["privatelink.cognitiveservices.azure.com"]
    end

    PE_ACR -.->|"DNS"| Z1
    PE_Cosmos -.->|"DNS"| Z2
    PE_Redis -.->|"DNS"| Z3
    PE_Storage -.->|"DNS"| Z4
    PE_EH -.->|"DNS"| Z5
    PE_KV -.->|"DNS"| Z6
    PE_AI -.->|"DNS"| Z7

    AKSSubnets -->|"Resolved via<br/>DNS Zones"| PESubnet

    DNSZones -.->|"VNet Link"| VNet
```

---

## AVM Module Inventory

All infrastructure uses [Azure Verified Modules](https://azure.github.io/Azure-Verified-Modules/).

| Module | Version | Resource Type |
|--------|---------|---------------|
| `avm/res/network/network-security-group` | 0.5.2 | `Microsoft.Network/networkSecurityGroups` |
| `avm/res/network/virtual-network` | 0.7.2 | `Microsoft.Network/virtualNetworks` |
| `avm/res/network/private-dns-zone` | 0.8.0 | `Microsoft.Network/privateDnsZones` |
| `avm/res/operational-insights/workspace` | 0.15.0 | `Microsoft.OperationalInsights/workspaces` |
| `avm/res/insights/component` | 0.7.1 | `Microsoft.Insights/components` |
| `avm/res/container-registry/registry` | 0.9.3 | `Microsoft.ContainerRegistry/registries` |
| `avm/res/document-db/database-account` | 0.18.0 | `Microsoft.DocumentDB/databaseAccounts` |
| `avm/res/cache/redis` | 0.16.4 | `Microsoft.Cache/Redis` |
| `avm/res/storage/storage-account` | 0.31.0 | `Microsoft.Storage/storageAccounts` |
| `avm/res/event-hub/namespace` | 0.14.0 | `Microsoft.EventHub/namespaces` |
| `avm/res/key-vault/vault` | 0.13.3 | `Microsoft.KeyVault/vaults` |
| `avm/ptn/ai-ml/ai-foundry` | 0.6.0 | `Microsoft.CognitiveServices/accounts` + ML workspace |
| `avm/res/container-service/managed-cluster` | 0.12.0 | `Microsoft.ContainerService/managedClusters` |
| `avm/res/api-management/service` | 0.14.0 | `Microsoft.ApiManagement/service` |

**Total**: 14 AVM modules — zero raw resource declarations in shared infrastructure.

---

## Architecture Decisions

### ADR-1: Hybrid Provisioning Strategy

**Context**: 26 agent services + 1 CRUD service + 1 UI need infrastructure. Per-service isolation maximizes independence but is cost-prohibitive.

**Decision**: Shared infrastructure for production, per-service standalone for demos.

**Consequences**: ~85% cost reduction. Services share Cosmos, Redis, Storage, Event Hubs but maintain logical isolation via distinct containers, databases, and blob containers.

### ADR-2: AVM-Only Policy

**Context**: Raw Bicep resources are error-prone and lack security defaults.

**Decision**: All resources use Azure Verified Modules (AVM). No raw `resource` declarations in shared infrastructure.

**Consequences**: Consistent security posture, automatic best-practice enforcement, reduced maintenance.

### ADR-3: Private Endpoints Everywhere

**Context**: Data services (`publicNetworkAccess: 'Disabled'`) are unreachable without private endpoints.

**Decision**: Deploy private endpoints + Private DNS zones for all data services (Cosmos DB, Redis, Storage, Event Hubs, Key Vault, ACR, AI Services).

**Consequences**: Full network isolation. AKS pods resolve service endpoints to private IPs via VNet-linked Private DNS zones.

### ADR-4: AI Foundry as Project Instance

**Context**: The AI Foundry AVM pattern module creates both a hub and a project. The deployment creates a project instance for model management, not a standalone hub.

**Decision**: Name and document the resource as a "Foundry Project" to reflect the actual deployment topology.

**Consequences**: Clearer documentation. The project inherits from the hub created by the pattern module internally.

### ADR-5: eastus2 as Default Region

**Context**: Multiple modules previously defaulted to different regions (eastus, eastus2).

**Decision**: Standardize all deployments to `eastus2`.

**Consequences**: Simplified deployment commands. No cross-region latency between shared resources and Static Web Apps.

### ADR-6: Three-Tier Memory

**Context**: Agents need fast context retrieval (recent conversations) and long-term storage (historical interactions).

**Decision**: Hot (Redis) → Warm (Cosmos DB) → Cold (Blob Storage) memory tiers, isolated per agent.

**Consequences**: Sub-millisecond hot reads, consistent warm reads, cost-effective cold archival. Each agent gets its own Redis DB, Cosmos container, and blob container.
