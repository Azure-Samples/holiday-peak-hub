# Solution Architecture Overview

<!-- Last Updated: 2026-04-30 -->

This diagram presents the full Holiday Peak Hub architecture — a reference implementation for **Agentic Microservices** on Azure.

## System Context (C4 Level 1)

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
graph TB
    Customer["🛒 Customer<br/>(Browser/Mobile)"]
    Staff["👤 Staff<br/>(Admin Console)"]

    subgraph "Holiday Peak Hub"
        UI["Next.js 15 UI<br/>Azure Static Web Apps"]
        APIM["Azure API Management<br/>Gateway + AI Policies"]
        CRUD["CRUD Service<br/>FastAPI + PostgreSQL"]

        subgraph "Agent Mesh (26 Agents on AKS)"
            EC["eCommerce Agents (5)"]
            CRM["CRM Agents (4)"]
            INV["Inventory Agents (4)"]
            LOG["Logistics Agents (4)"]
            PM["Product Mgmt Agents (4)"]
            SE["Search Agent (1)"]
            TL["Truth Layer Agents (4)"]
        end
    end

    subgraph "Azure Platform Services"
        Foundry["Azure AI Foundry<br/>GPT-5, GPT-5-nano"]
        CosmosDB["Azure Cosmos DB<br/>Warm Memory"]
        Redis["Azure Redis<br/>Hot Memory"]
        Blob["Azure Blob Storage<br/>Cold Memory"]
        EH["Azure Event Hubs<br/>Async Messaging"]
        AIS["Azure AI Search<br/>Vector + Hybrid"]
        PG["Azure PostgreSQL<br/>CRUD Data"]
        KV["Azure Key Vault<br/>Secrets"]
        AppIns["Application Insights<br/>Telemetry"]
    end

    Customer --> UI
    Staff --> UI
    UI --> APIM
    APIM --> CRUD
    APIM --> EC & CRM & INV & LOG & PM & SE & TL
    CRUD --> PG
    CRUD --> EH
    EH --> EC & CRM & INV & LOG & PM & TL
    EC & CRM & INV & LOG & PM & SE & TL --> Foundry
    EC & CRM & INV & LOG & PM & SE & TL --> CosmosDB & Redis & Blob
    SE --> AIS
    EC & CRM & INV & LOG & PM & SE & TL --> KV
    EC & CRM & INV & LOG & PM & SE & TL --> AppIns
```

## Container View (C4 Level 2) — Agent Service Internals

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
graph LR
    subgraph "Any Agent Service"
        MAIN["main.py<br/>create_standard_app()"]
        AGENT["Domain Agent<br/>extends BaseRetailAgent"]
        HANDLER["handle()"]
        TOOLS["MCP Tools<br/>FastAPIMCPServer"]
        ADAPT["Adapters<br/>CRM, Inventory, etc."]
        EVENTS["Event Handlers<br/>EventHubSubscriber"]
    end

    subgraph "holiday-peak-lib"
        AF["AppFactory"]
        BA["BaseRetailAgent"]
        AB["AgentBuilder"]
        FAI["FoundryAgentInvoker"]
        MEM["MemoryClient<br/>Hot|Warm|Cold"]
        GR["Guardrails"]
        CB["CircuitBreaker"]
        TEL["FoundryTracer"]
    end

    subgraph "Microsoft Agent Framework"
        MAF["FoundryAgent"]
    end

    MAIN --> AF
    AF --> AB
    AB --> AGENT
    AGENT -->|extends| BA
    AGENT --> HANDLER
    HANDLER --> TOOLS & ADAPT & EVENTS
    BA --> FAI
    FAI --> MAF
    BA --> MEM & GR & CB & TEL
```

## Domain Agent Map

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
graph TB
    subgraph "eCommerce Domain"
        E1["cart-intelligence<br/>:8001"]
        E2["catalog-search<br/>:8002"]
        E3["checkout-support<br/>:8003"]
        E4["order-status<br/>:8004"]
        E5["product-detail-enrichment<br/>:8005"]
    end

    subgraph "Product Management Domain"
        P1["acp-transformation<br/>:8006"]
        P2["assortment-optimization<br/>:8007"]
        P3["consistency-validation<br/>:8008"]
        P4["normalization-classification<br/>:8009"]
    end

    subgraph "CRM Domain"
        C1["campaign-intelligence<br/>:8010"]
        C2["profile-aggregation<br/>:8011"]
        C3["segmentation-personalization<br/>:8012"]
        C4["support-assistance<br/>:8013"]
    end

    subgraph "Inventory Domain"
        I1["alerts-triggers<br/>:8014"]
        I2["health-check<br/>:8015"]
        I3["jit-replenishment<br/>:8016"]
        I4["reservation-validation<br/>:8017"]
    end

    subgraph "Logistics Domain"
        L1["carrier-selection<br/>:8018"]
        L2["eta-computation<br/>:8019"]
        L3["returns-support<br/>:8020"]
        L4["route-issue-detection<br/>:8021"]
    end

    subgraph "Search Domain"
        S1["search-enrichment-agent"]
    end

    subgraph "Truth Layer Domain"
        T1["truth-ingestion"]
        T2["truth-enrichment"]
        T3["truth-export"]
        T4["truth-hitl"]
    end
```

## Data Flow Patterns

### Pattern 1: Transactional (Frontend → CRUD → Database)
```
Customer → UI → APIM → CRUD Service → PostgreSQL
                                    ↓
                              Event Hubs (async notification)
```

### Pattern 2: Agent-Enriched (CRUD → Agent → CRUD)
```
CRUD Service → Agent REST endpoint (circuit breaker, <200ms)
            → Agent invokes Foundry model
            → Agent reads memory context
            → Enriched response returned to CRUD
```

### Pattern 3: Async Processing (Event → Agent)
```
CRUD publishes event → Event Hubs
                    → Agent consumer group processes
                    → Agent writes to memory tiers
                    → Agent calls MCP tools on other agents
```

### Pattern 4: Agent-to-Agent (MCP Protocol)
```
Agent A → POST /mcp/tool_name on Agent B
       → Agent B processes with its domain context
       → Structured dict response returned
```

## Deployment Topology

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
graph TB
    subgraph "Azure Subscription"
        subgraph "AKS Cluster"
            SYS["system pool<br/>K8s components"]
            subgraph "crud namespace"
                CRUD_POD["crud-service pods<br/>(1-10 replicas)"]
            end
            subgraph "holiday-peak-agents"
                subgraph "eCommerce"
                    ECOM_PODS["5 agent deployments"]
                end
                subgraph "CRM"
                    CRM_PODS["4 agent deployments"]
                end
                subgraph "Inventory"
                    INV_PODS["4 agent deployments"]
                end
                subgraph "Logistics"
                    LOG_PODS["4 agent deployments"]
                end
                subgraph "Product Mgmt"
                    PM_PODS["4 agent deployments"]
                end
                subgraph "Search"
                    SEARCH_PODS["1 agent deployment"]
                end
                subgraph "Truth Layer"
                    TRUTH_PODS["4 agent deployments"]
                end
            end
        end

        SWA["Azure Static Web Apps<br/>Next.js 15 UI"]
        APIM_GW["API Management"]
        FLUX["Flux CD<br/>GitOps Controller"]
    end

    FLUX -->|reconcile| ECOM_PODS & CRM_PODS & INV_PODS & LOG_PODS & PM_PODS & SEARCH_PODS & TRUTH_PODS & CRUD_POD
    SWA --> APIM_GW --> CRUD_POD & ECOM_PODS
```

## Related Documents

- [MAF Integration Rationale](maf-integration-rationale.md) — Why Microsoft Agent Framework lives in the lib
- [ADRs Index](ADRs.md) — All 27 Architecture Decision Records
- [Components Overview](components.md) — Detailed component responsibility matrix
- [Standalone Deployment Guide](standalone-deployment-guide.md) — How to deploy individual services
- [Infrastructure README](../../.infra/README.md) — Bicep and AKS provisioning
