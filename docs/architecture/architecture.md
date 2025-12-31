# Architecture Overview

This document provides the overall system architecture for Holiday Peak Hub, including context diagrams, use case models, component interactions, and deployment topology.

## System Context

```mermaid
C4Context
    title System Context - Holiday Peak Hub

    Person(customer, "Customer", "Shopper using<br/>e-commerce site")
    Person(agent, "Service Agent", "Customer support<br/>representative")
    Person(manager, "Operations Manager", "Inventory/logistics<br/>planner")
    
    System_Boundary(hub, "Holiday Peak Hub") {
        System(ecommerce, "E-commerce Services", "Catalog search, cart,<br/>checkout, order tracking")
        System(product, "Product Mgmt Services", "Normalization, ACP,<br/>assortment optimization")
        System(crm, "CRM Services", "Profile aggregation,<br/>segmentation, campaigns")
        System(inventory, "Inventory Services", "Health check, JIT<br/>replenishment, alerts")
        System(logistics, "Logistics Services", "ETA, carrier selection,<br/>returns, route detection")
    }
    
    System_Ext(retailSystems, "Retailer Legacy Systems", "Inventory, pricing,<br/>CRM, ERP APIs")
    System_Ext(foundry, "Microsoft Foundry", "GPT-4 models,<br/>embedding services")
    System_Ext(external, "External Partners", "Carriers, payment<br/>gateways, analytics")
    
    Rel(customer, ecommerce, "Browses, orders")
    Rel(agent, crm, "Views profiles, campaigns")
    Rel(manager, inventory, "Monitors stock, triggers")
    
    Rel(ecommerce, retailSystems, "Fetches inventory,<br/>pricing")
    Rel(product, retailSystems, "Reads catalog")
    Rel(crm, retailSystems, "Queries customer data")
    Rel(inventory, retailSystems, "Checks stock levels")
    Rel(logistics, external, "Gets shipping rates")
    
    Rel(ecommerce, foundry, "Model inference")
    Rel(crm, foundry, "Segmentation models")
```

## Use Case Diagrams

### E-commerce Domain

```mermaid
graph TB
    subgraph Actors
        Customer((Customer))
        Agent((Service Agent))
    end
    
    subgraph "E-commerce Use Cases"
        UC1[Search Product Catalog]
        UC2[View Product Details]
        UC3[Add to Cart]
        UC4[Checkout]
        UC5[Track Order Status]
    end
    
    Customer -->|performs| UC1
    Customer -->|performs| UC2
    Customer -->|performs| UC3
    Customer -->|performs| UC4
    Customer -->|performs| UC5
    Agent -->|assists with| UC5
    
    UC1 -.->|includes| SearchIndex[Query AI Search]
    UC2 -.->|includes| Enrich[Fetch ACP Metadata]
    UC3 -.->|includes| CartLogic[Apply Personalization]
    UC4 -.->|includes| ValidateAllocation[Check Inventory]
    UC5 -.->|includes| QueryLogistics[Get Shipment ETA]
```

### Product Management Domain

```mermaid
graph TB
    subgraph Actors
        DataEng((Data Engineer))
        ProductMgr((Product Manager))
    end
    
    subgraph "Product Management Use Cases"
        UC1[Normalize Product Data]
        UC2[Transform to ACP]
        UC3[Validate Consistency]
        UC4[Optimize Assortment]
    end
    
    DataEng -->|executes| UC1
    DataEng -->|executes| UC2
    DataEng -->|monitors| UC3
    ProductMgr -->|runs| UC4
    
    UC1 -.->|includes| Classify[Auto-classify Categories]
    UC2 -.->|includes| Map[Map to ACP Schema]
    UC3 -.->|includes| CheckRules[Apply Business Rules]
    UC4 -.->|includes| MLModel[Run Assortment Model]
```

### CRM Domain

```mermaid
graph TB
    subgraph Actors
        Marketer((Marketing Manager))
        Agent((Service Agent))
    end
    
    subgraph "CRM Use Cases"
        UC1[Aggregate Customer Profiles]
        UC2[Segment Customers]
        UC3[Generate Campaign Intelligence]
        UC4[Provide Support Assistance]
    end
    
    Marketer -->|requests| UC1
    Marketer -->|creates| UC2
    Marketer -->|reviews| UC3
    Agent -->|uses| UC4
    
    UC1 -.->|includes| FetchHistory[Pull Order History]
    UC2 -.->|includes| RunMLModel[Apply Clustering]
    UC3 -.->|includes| Forecast[Predict Campaign ROI]
    UC4 -.->|includes| SearchKB[Query Knowledge Base]
```

### Inventory Domain

```mermaid
graph TB
    subgraph Actors
        OpsMgr((Operations Manager))
        System((Automated System))
    end
    
    subgraph "Inventory Use Cases"
        UC1[Health Check]
        UC2[JIT Replenishment]
        UC3[Reservation Validation]
        UC4[Generate Alerts]
    end
    
    OpsMgr -->|monitors| UC1
    System -->|triggers| UC2
    System -->|executes| UC3
    OpsMgr -->|receives| UC4
    
    UC1 -.->|includes| PredictStockout[Forecast Demand]
    UC2 -.->|includes| CreatePO[Generate Purchase Order]
    UC3 -.->|includes| LockStock[Reserve Inventory]
    UC4 -.->|includes| NotifyTeam[Send Notifications]
```

### Logistics Domain

```mermaid
graph TB
    subgraph Actors
        Customer((Customer))
        LogisticsMgr((Logistics Manager))
    end
    
    subgraph "Logistics Use Cases"
        UC1[Compute ETA]
        UC2[Select Carrier]
        UC3[Process Returns]
        UC4[Detect Route Issues]
    end
    
    Customer -->|requests| UC1
    LogisticsMgr -->|configures| UC2
    Customer -->|initiates| UC3
    LogisticsMgr -->|monitors| UC4
    
    UC1 -.->|includes| QueryCarrier[Call Carrier API]
    UC2 -.->|includes| OptimizeCost[Cost vs Speed Trade-off]
    UC3 -.->|includes| GenerateLabel[Create Return Label]
    UC4 -.->|includes| AlertDelay[Proactive Notification]
```

## Component Interaction

### Memory Tier Access Pattern

```mermaid
sequenceDiagram
    participant Agent
    participant Memory
    participant Redis
    participant Cosmos
    participant Blob
    
    Agent->>Memory: get("session_123")
    Memory->>Redis: check hot tier
    alt Found in Redis
        Redis-->>Memory: value
        Memory-->>Agent: value
    else Not in Redis
        Memory->>Cosmos: check warm tier
        alt Found in Cosmos
            Cosmos-->>Memory: value
            Memory->>Redis: promote to hot
            Redis-->>Memory: ok
            Memory-->>Agent: value
        else Not in Cosmos
            Memory->>Blob: check cold tier
            alt Found in Blob
                Blob-->>Memory: value
                Memory->>Cosmos: promote to warm
                Memory->>Redis: promote to hot
                Memory-->>Agent: value
            else Not found
                Memory-->>Agent: null
            end
        end
    end
```

### SAGA Choreography: Order Placement

```mermaid
sequenceDiagram
    participant Customer
    participant OrderSvc as Order Service
    participant InventorySvc as Inventory Service
    participant PaymentSvc as Payment Service
    participant LogisticsSvc as Logistics Service
    participant EventHub as Event Hubs
    
    Customer->>OrderSvc: POST /orders
    OrderSvc->>EventHub: OrderCreated event
    OrderSvc-->>Customer: 202 Accepted
    
    EventHub->>InventorySvc: OrderCreated
    InventorySvc->>InventorySvc: Reserve stock
    InventorySvc->>EventHub: InventoryReserved event
    
    EventHub->>PaymentSvc: InventoryReserved
    PaymentSvc->>PaymentSvc: Process payment
    PaymentSvc->>EventHub: PaymentProcessed event
    
    EventHub->>LogisticsSvc: PaymentProcessed
    LogisticsSvc->>LogisticsSvc: Schedule shipment
    LogisticsSvc->>EventHub: ShipmentScheduled event
    
    EventHub->>OrderSvc: ShipmentScheduled
    OrderSvc->>OrderSvc: Update order status
    OrderSvc->>Customer: Email confirmation
```

### Agent Tool Calling Flow

```mermaid
sequenceDiagram
    participant Client
    participant App as FastAPI App
    participant Agent as Agent Framework
    participant MCP as MCP Server
    participant Adapter as Retail Adapter
    participant Memory
    
    Client->>App: POST /chat {"query": "Check inventory"}
    App->>Agent: run(query, tools)
    Agent->>Agent: Parse query, select tools
    Agent->>MCP: call_tool("check_inventory", {"sku": "SKU-123"})
    MCP->>Adapter: fetch_inventory("SKU-123")
    Adapter->>Adapter: Call retailer API
    Adapter-->>MCP: InventoryStatus
    MCP-->>Agent: Tool result
    Agent->>Memory: Store conversation
    Agent-->>App: Response
    App-->>Client: 200 OK {"message": "In stock: 42 units"}
```

## Deployment Topology

```mermaid
graph TB
    subgraph "Azure Kubernetes Service"
        subgraph "Namespace: ecommerce"
            EC1[catalog-search pod]
            EC2[product-detail pod]
            EC3[cart-intelligence pod]
            EC4[checkout-support pod]
            EC5[order-status pod]
        end
        
        subgraph "Namespace: product-mgmt"
            PM1[normalization pod]
            PM2[acp-transformation pod]
            PM3[consistency-validation pod]
            PM4[assortment-optimization pod]
        end
        
        subgraph "Namespace: crm"
            CR1[profile-aggregation pod]
            CR2[segmentation pod]
            CR3[campaign-intelligence pod]
            CR4[support-assistance pod]
        end
        
        subgraph "Namespace: inventory"
            IN1[health-check pod]
            IN2[jit-replenishment pod]
            IN3[reservation-validation pod]
            IN4[alerts-triggers pod]
        end
        
        subgraph "Namespace: logistics"
            LO1[eta-computation pod]
            LO2[carrier-selection pod]
            LO3[returns-support pod]
            LO4[route-issue-detection pod]
        end
    end
    
    subgraph "Azure Services"
        Redis[Azure Cache<br/>for Redis]
        Cosmos[Azure Cosmos DB]
        Blob[Azure Blob Storage]
        Search[Azure AI Search]
        EventHub[Azure Event Hubs]
        Monitor[Azure Monitor]
        APIM[API Management]
    end
    
    Client[Clients]
    
    Client -->|HTTPS| APIM
    APIM --> EC1 & EC2 & EC3 & EC4 & EC5
    
    EC1 & PM1 & CR1 --> Redis
    EC1 & PM1 & CR1 --> Cosmos
    EC1 & PM1 & CR1 --> Blob
    EC1 --> Search
    
    EC3 & IN2 --> EventHub
    
    EC1 & PM1 & CR1 & IN1 & LO1 --> Monitor
```

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Language** | Python 3.13 | All services and lib |
| **API Framework** | FastAPI + FastAPI-MCP | REST + MCP exposition |
| **Agent Framework** | Microsoft Agent Framework | Orchestration logic |
| **Memory - Hot** | Azure Cache for Redis | <50ms session state |
| **Memory - Warm** | Azure Cosmos DB | Conversation history |
| **Memory - Cold** | Azure Blob Storage | Archival storage |
| **Search** | Azure AI Search | Vector+hybrid search |
| **Messaging** | Azure Event Hubs | SAGA choreography |
| **Compute** | Azure Kubernetes Service | Container orchestration |
| **Scaling** | KEDA | Event-driven auto-scale |
| **Deployment** | Helm + Flagger | Canary deployments |
| **Observability** | Azure Monitor | Logs, metrics, traces |
| **API Gateway** | Azure API Management | Rate limiting, auth |

## Next Steps

- [Review ADRs](ADRs.md) for detailed decision rationale
- [Explore Components](components.md) for implementation details
- [Read Business Summary](business-summary.md) for value proposition
