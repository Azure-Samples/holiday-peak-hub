# Solution Architecture Diagrams

**Last Updated**: 2026-04-30

This document contains the system-level and per-domain Mermaid diagrams for the Holiday Peak Hub agentic microservices platform.

---

## 1. System Context (C4 Level 1)

External actors, channels, and the system boundary.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#FFB3BA','primaryTextColor':'#000','primaryBorderColor':'#FF8B94','lineColor':'#BAE1FF','secondaryColor':'#BAE1FF','tertiaryColor':'#FFFFFF'}}}%%
graph TB
    Customer["👤 Customer<br/>(Browser / Mobile)"]
    Staff["👤 Staff<br/>(Admin Dashboard)"]
    PIM["📦 External PIM<br/>(Akeneo / Salsify)"]
    DAM["🖼️ External DAM<br/>(Cloudinary)"]
    Carrier["🚛 Carrier APIs<br/>(FedEx / UPS / DHL)"]
    Payment["💳 Payment Gateway<br/>(Stripe)"]

    subgraph HPH["Holiday Peak Hub Platform"]
        UI["Next.js Frontend"]
        APIM["Azure API Management"]
        CRUD["CRUD Service"]
        Agents["26 Agent Services<br/>(7 Domains)"]
        EH["Azure Event Hubs"]
        Memory["Three-Tier Memory<br/>(Redis / Cosmos / Blob)"]
        Foundry["Azure AI Foundry<br/>(GPT-5 / GPT-5-nano)"]
        Search["Azure AI Search"]
    end

    Customer --> UI
    Staff --> UI
    UI --> APIM --> CRUD
    APIM --> Agents
    CRUD --> EH --> Agents
    Agents --> Memory
    Agents --> Foundry
    Agents --> Search
    CRUD --> Payment
    Agents --> PIM
    Agents --> DAM
    Agents --> Carrier
```

---

## 2. Container View (C4 Level 2)

Azure runtime composition across AKS, platform services, and external integrations.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#FFB3BA','primaryTextColor':'#000','primaryBorderColor':'#FF8B94','lineColor':'#BAE1FF','secondaryColor':'#BAE1FF','tertiaryColor':'#FFFFFF'}}}%%
graph TB
    subgraph SWA["Azure Static Web Apps"]
        UI["Next.js 15 UI<br/><i>TypeScript / Tailwind</i>"]
    end

    subgraph APIM["Azure API Management"]
        GW["API Gateway<br/><i>JWT auth, rate limiting,<br/>AI policies</i>"]
    end

    subgraph AKS["Azure Kubernetes Service"]
        subgraph CrudNS["namespace: holiday-peak-crud"]
            CRUD["crud-service<br/><i>FastAPI / PostgreSQL</i>"]
        end

        subgraph AgentsNS["namespace: holiday-peak-agents"]
            subgraph EcomGrp["eCommerce Domain"]
                CS["catalog-search"]
                PDE["product-detail-enrichment"]
                CI["cart-intelligence"]
                CKS["checkout-support"]
                OS["order-status"]
            end

            subgraph CrmGrp["CRM Domain"]
                PA["profile-aggregation"]
                SP["segmentation-personalization"]
                CAM["campaign-intelligence"]
                SA["support-assistance"]
            end

            subgraph InvGrp["Inventory Domain"]
                AT["alerts-triggers"]
                HC["health-check"]
                JIT["jit-replenishment"]
                RV["reservation-validation"]
            end

            subgraph LogGrp["Logistics Domain"]
                CSel["carrier-selection"]
                ETA["eta-computation"]
                RS["returns-support"]
                RID["route-issue-detection"]
            end

            subgraph PmGrp["Product Management Domain"]
                ACP["acp-transformation"]
                ASO["assortment-optimization"]
                CSV["consistency-validation"]
                NC["normalization-classification"]
            end

            subgraph SearchGrp["Search Domain"]
                SEA["search-enrichment"]
            end

            subgraph TruthGrp["Truth Layer Domain"]
                TI["truth-ingestion"]
                TE["truth-enrichment"]
                TH["truth-hitl"]
                TX["truth-export"]
            end
        end
    end

    subgraph Data["Data & Messaging"]
        PG["PostgreSQL<br/><i>Transactional</i>"]
        Cosmos["Cosmos DB<br/><i>Warm memory</i>"]
        Redis["Redis Cache<br/><i>Hot memory</i>"]
        Blob["Blob Storage<br/><i>Cold memory</i>"]
        EH["Event Hubs<br/><i>5 topics</i>"]
    end

    subgraph AI["AI & Search"]
        Foundry["Azure AI Foundry<br/><i>SLM + LLM</i>"]
        AIS["Azure AI Search<br/><i>Vector + hybrid</i>"]
    end

    UI --> GW
    GW --> CRUD
    GW --> CS
    CRUD --> PG
    CRUD --> EH
    EH --> EcomNS & CrmNS & InvNS & LogNS & PmNS & SearchNS & TruthNS
    EcomNS & CrmNS & InvNS & LogNS & PmNS & SearchNS & TruthNS --> Redis & Cosmos & Blob
    EcomNS & CrmNS & InvNS & LogNS & PmNS & SearchNS & TruthNS --> Foundry
    CS & SEA --> AIS
```

---

## 3. eCommerce Domain

Five agents handling search, browsing, cart, checkout, and order tracking.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#FFB3BA','primaryTextColor':'#000','primaryBorderColor':'#FF8B94','lineColor':'#BAE1FF','secondaryColor':'#BAE1FF','tertiaryColor':'#FFFFFF'}}}%%
graph LR
    CRUD["CRUD Service"]
    EH["Event Hubs"]

    subgraph ECOM["eCommerce Domain (holiday-peak-agents)"]
        CS["🔍 Catalog Search<br/><i>Vector + hybrid search<br/>SLM intent detection</i>"]
        PDE["📝 Product Detail Enrichment<br/><i>AI-generated descriptions<br/>SEO optimization</i>"]
        CI["🛒 Cart Intelligence<br/><i>Cross-sell, upsell<br/>Abandonment prevention</i>"]
        CKS["✅ Checkout Support<br/><i>Validation, fraud signals<br/>Inventory hold</i>"]
        OS["📦 Order Status<br/><i>Tracking enrichment<br/>Proactive notifications</i>"]
    end

    CRUD -->|product.created<br/>product.updated| EH
    EH --> PDE
    EH --> CS
    CRUD -->|order.created| EH --> OS
    CRUD -->|cart.updated| EH --> CI
    CRUD <-->|sync + circuit breaker| CS & CKS
    CS -->|MCP: get_enrichment| PDE
    CKS -->|MCP: validate_stock| INV["Inventory Domain"]
    CS --> AIS["Azure AI Search"]
```

**Key Interactions:**
- `catalog-search` provides real-time search with SLM-first intent detection and vector search fallback
- `product-detail-enrichment` generates AI descriptions, triggered by product events
- `cart-intelligence` monitors cart state for cross-sell/upsell opportunities
- `checkout-support` orchestrates inventory holds and fraud signal checks
- `order-status` enriches tracking data with carrier intelligence

---

## 4. CRM Domain

Four agents handling customer profiles, segmentation, campaigns, and support.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#FFB3BA','primaryTextColor':'#000','primaryBorderColor':'#FF8B94','lineColor':'#BAE1FF','secondaryColor':'#BAE1FF','tertiaryColor':'#FFFFFF'}}}%%
graph LR
    CRUD["CRUD Service"]
    EH["Event Hubs"]

    subgraph CRM["CRM Domain (holiday-peak-agents)"]
        PA["👤 Profile Aggregation<br/><i>360° customer view<br/>Purchase history synthesis</i>"]
        SP["🎯 Segmentation &<br/>Personalization<br/><i>Dynamic cohorts<br/>Behavioral clustering</i>"]
        CAM["📣 Campaign Intelligence<br/><i>Channel optimization<br/>ROI prediction</i>"]
        SA["🎧 Support Assistance<br/><i>Ticket classification<br/>Resolution suggestions</i>"]
    end

    CRUD -->|user.updated<br/>order.completed| EH
    EH --> PA & SP
    PA -->|MCP: get_profile| SP
    SP -->|MCP: get_segments| CAM
    CRUD <-->|sync| SA
    SA -->|MCP: get_profile_context| PA
```

---

## 5. Inventory Domain

Four agents handling stock monitoring, replenishment, reservations, and alerts.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#FFB3BA','primaryTextColor':'#000','primaryBorderColor':'#FF8B94','lineColor':'#BAE1FF','secondaryColor':'#BAE1FF','tertiaryColor':'#FFFFFF'}}}%%
graph LR
    CRUD["CRUD Service"]
    EH["Event Hubs"]

    subgraph INV["Inventory Domain (holiday-peak-agents)"]
        AT["🚨 Alerts & Triggers<br/><i>Stock threshold alerts<br/>Anomaly detection</i>"]
        HC["📊 Health Check<br/><i>Inventory accuracy<br/>Cycle count scheduling</i>"]
        JIT["📦 JIT Replenishment<br/><i>Demand forecasting<br/>Automated reorder</i>"]
        RV["🔒 Reservation Validation<br/><i>Hold management<br/>Conflict resolution</i>"]
    end

    CRUD -->|inventory.updated<br/>reservation.created| EH
    EH --> AT & HC & JIT & RV
    AT -->|MCP: get_stock_level| HC
    JIT -->|MCP: check_thresholds| AT
    CRUD <-->|sync| RV
```

---

## 6. Logistics Domain

Four agents handling carrier selection, ETA computation, returns, and route monitoring.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#FFB3BA','primaryTextColor':'#000','primaryBorderColor':'#FF8B94','lineColor':'#BAE1FF','secondaryColor':'#BAE1FF','tertiaryColor':'#FFFFFF'}}}%%
graph LR
    CRUD["CRUD Service"]
    EH["Event Hubs"]

    subgraph LOG["Logistics Domain (holiday-peak-agents)"]
        CSel["🚛 Carrier Selection<br/><i>Rate comparison<br/>SLA matching</i>"]
        ETA["⏱️ ETA Computation<br/><i>Multi-carrier tracking<br/>Delay prediction</i>"]
        RS["↩️ Returns Support<br/><i>Return eligibility<br/>Label generation</i>"]
        RID["🗺️ Route Issue Detection<br/><i>Delay alerts<br/>Rerouting suggestions</i>"]
    end

    CRUD -->|shipment.created<br/>return.requested| EH
    EH --> CSel & ETA & RS & RID
    CSel -->|MCP: get_delivery_estimate| ETA
    RID -->|MCP: get_carrier_status| ETA
    CRUD <-->|sync| RS
    CSel --> Carrier["External Carrier APIs"]
```

---

## 7. Product Management Domain

Four agents handling product data transformation, assortment, validation, and classification.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#FFB3BA','primaryTextColor':'#000','primaryBorderColor':'#FF8B94','lineColor':'#BAE1FF','secondaryColor':'#BAE1FF','tertiaryColor':'#FFFFFF'}}}%%
graph LR
    CRUD["CRUD Service"]
    EH["Event Hubs"]

    subgraph PM["Product Management Domain (holiday-peak-agents)"]
        ACP["🔄 ACP Transformation<br/><i>Canonical product format<br/>Attribute mapping</i>"]
        ASO["📈 Assortment Optimization<br/><i>Category performance<br/>Gap analysis</i>"]
        CSV["✓ Consistency Validation<br/><i>Cross-channel parity<br/>Data quality scoring</i>"]
        NC["🏷️ Normalization &<br/>Classification<br/><i>Taxonomy mapping<br/>Attribute normalization</i>"]
    end

    CRUD -->|product.created<br/>product.updated| EH
    EH --> ACP & ASO & CSV & NC
    ACP -->|MCP: validate_consistency| CSV
    NC -->|MCP: get_taxonomy| ACP
    ACP --> PIM["External PIM<br/>(Akeneo / Salsify)"]
```

---

## 8. Search & Truth Layer Domains

Five agents handling search enrichment and the Product Truth Layer pipeline.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#FFB3BA','primaryTextColor':'#000','primaryBorderColor':'#FF8B94','lineColor':'#BAE1FF','secondaryColor':'#BAE1FF','tertiaryColor':'#FFFFFF'}}}%%
graph LR
    CRUD["CRUD Service"]
    EH["Event Hubs"]

    subgraph SRCH["Search Domain (holiday-peak-agents)"]
        SEA["🔍 Search Enrichment<br/><i>Index augmentation<br/>Embedding generation</i>"]
    end

    subgraph TRUTH["Truth Layer Domain (holiday-peak-agents)"]
        TI["📥 Truth Ingestion<br/><i>Multi-source intake<br/>Schema validation</i>"]
        TE["🧠 Truth Enrichment<br/><i>AI attribute generation<br/>Guardrail validation</i>"]
        TH["👁️ Truth HITL<br/><i>Human review queue<br/>Approve / Reject / Edit</i>"]
        TX["📤 Truth Export<br/><i>PIM writeback<br/>Channel distribution</i>"]
    end

    CRUD -->|product.updated| EH
    EH --> SEA
    SEA --> AIS["Azure AI Search"]

    TI -->|MCP: enrich_product| TE
    TE -->|MCP: submit_review| TH
    TH -->|MCP: export_approved| TX
    TX --> PIM["External PIM"]
    TI --> EH2["Platform Jobs<br/>Event Hub"]
```

**Truth Layer Pipeline:**
1. **Ingestion** — Receives product data from external PIM systems, validates schema, creates truth candidates
2. **Enrichment** — AI generates missing attributes with guardrail validation (confidence thresholds, content policy)
3. **HITL** — Human reviewers approve, reject, or edit enriched products with audit trail
4. **Export** — Approved products written back to PIM and distributed to channels

---

## 9. Data Flow Overview

Complete request lifecycle showing sync and async paths.

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'primaryColor':'#FFB3BA','primaryTextColor':'#000','primaryBorderColor':'#FF8B94','lineColor':'#BAE1FF','secondaryColor':'#BAE1FF','tertiaryColor':'#FFFFFF'}}}%%
sequenceDiagram
    actor User
    participant UI as Next.js Frontend
    participant APIM as API Management
    participant CRUD as CRUD Service
    participant PG as PostgreSQL
    participant EH as Event Hubs
    participant Agent as Agent Service
    participant Foundry as AI Foundry
    participant Memory as Memory Stack

    Note over User,Memory: Sync Path (< 200ms) — Transactional + Enrichment

    User->>UI: Browse / Search / Checkout
    UI->>APIM: REST request (JWT)
    APIM->>CRUD: Validated request

    alt Transactional (CRUD)
        CRUD->>PG: SQL query / mutation
        PG-->>CRUD: Result
        CRUD-->>APIM: JSON response
    else Enrichment (Agent sync)
        CRUD->>Agent: REST call (circuit breaker)
        Agent->>Memory: parallel get (Redis + Cosmos)
        Agent->>Foundry: SLM invoke
        Foundry-->>Agent: Response
        Agent-->>CRUD: Enriched result
        CRUD-->>APIM: JSON response
    end

    APIM-->>UI: Response
    UI-->>User: Rendered page

    Note over CRUD,Memory: Async Path — Event-Driven Processing

    CRUD->>EH: Publish domain event
    EH->>Agent: Consume event
    Agent->>Foundry: LLM invoke (complex)
    Agent->>Memory: Write results
    Agent->>CRUD: Callback (if needed)
```

---

## Related

- [Architecture Overview](architecture.md)
- [ADR Index](ADRs.md) — 35 architecture decision records
- [Agentic Microservices Reference](../agentic-microservices-reference.md) — Positioning document
- [MAF Integration Rationale](maf-integration-rationale.md) — Why MAF is wrapped in the lib
- [Standalone Deployment Guide](standalone-deployment-guide.md)
- [Diagrams Index](diagrams/README.md) — C4 draw.io and sequence diagrams
