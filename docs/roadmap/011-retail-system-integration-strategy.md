# Retail System Integration Strategy

**Type**: Feature Request (Epic)  
**Priority**: High  
**Category**: Integration / Architecture  
**Created**: February 2026

## Executive Summary

Based on the [Retail Capabilities Blueprint research](../../improvements.md), this document outlines the integration strategy for connecting Holiday Peak Hub with enterprise retail systems. The goal is to provide **adapter implementations** for major retail platforms across all capability domains while ensuring:

1. **Product enrichment uses only company-owned data** — AI agents enrich from internal systems, not external inference
2. **Connectors and contracts live in `lib/`** — shared, typed, and reusable across apps
3. **Applications consume `lib` connectors via registry wiring** — ensuring consistency
4. **CRUD service acts as the integration hub** — exposing unified REST APIs

## Design Principles

### 1. Internal Data Enrichment Only

Per project requirements, AI agent enrichment MUST source from:
- Company's existing PIM/DAM systems
- Internal CRM/CDP customer profiles
- Company's inventory systems (ERP/WMS)
- Internal analytics platforms

Agents SHALL NOT:
- Generate product descriptions from scratch without source data
- Infer customer preferences without behavioral data
- Hallucinate inventory levels or pricing

### 2. Adapter Architecture

```
holiday-peak-hub/
├── lib/                              # Framework + integration contracts/registry
│   └── src/holiday_peak_lib/
│       ├── adapters/
│       │   ├── base.py              # BaseAdapter, BaseConnector interfaces
│       │   ├── external_api_adapter.py  # Generic external API base
│       │   └── ...                  # Domain-specific base classes
│       └── integrations/
│           ├── contracts.py         # Data models + abstract connector contracts
│           └── registry.py          # Runtime connector registry
│
└── apps/crud-service/               # Integration hub
    └── src/
```

### 3. Connector Contract

Each connector MUST:
1. Extend `BaseAdapter` from `holiday_peak_lib`
2. Implement domain-specific interface (e.g., `PIMConnectorBase`)
3. Provide configuration via environment variables
4. Include comprehensive tests with mock responses
5. Document the REST API mappings

### 4. CRUD Service as Integration Hub

The CRUD service exposes unified REST APIs that:
- Route to appropriate connectors based on configuration
- Provide fallback to internal storage when external systems unavailable
- Publish events to Event Hubs for agent consumption
- Maintain data consistency through saga patterns

## Integration by Domain

### A. Inventory & Supply Chain Management

**Purpose**: Real-time inventory visibility, order fulfillment, warehouse ops

| System | API Type | Priority | Adapter Purpose |
|--------|----------|----------|-----------------|
| SAP S/4HANA | REST/OData | High | Inventory sync, PO management |
| Oracle Fusion SCM | REST/SOAP | High | WMS/OMS integration |
| Manhattan Active Omni | REST | High | Fulfillment orchestration |
| Blue Yonder Luminate | REST | Medium | Demand forecasting |
| Dynamics 365 SCM | OData/Dataverse | Medium | Inventory, warehouse |
| Infor CloudSuite WMS | API/EDI | Low | Warehouse operations |

**Key Data Flows**:
- Inventory levels → Real-time events → CRUD API → Agents
- Orders → OMS routing → Fulfillment nodes → Status updates
- Replenishment triggers → Supplier POs

### B. CRM, Loyalty & Customer Data

**Purpose**: Customer 360, loyalty programs, personalization (using owned data)

| System | API Type | Priority | Adapter Purpose |
|--------|----------|----------|-----------------|
| Salesforce CRM | REST/GraphQL | High | Customer profiles, cases |
| Dynamics 365 CE | OData | High | CRM, service tickets |
| Adobe Experience Platform | REST | High | CDP, segments |
| Braze | REST | Medium | Campaign triggers |
| Twilio Segment | REST | Medium | Event routing |
| Oracle CX | REST/SOAP | Medium | Oracle-stack customers |

**Key Data Flows**:
- Purchase history → Customer profile enrichment
- Segment membership → Personalization agents
- Support tickets → Service routing
- Consent records → Marketing compliance

### C. Product Information Management (PIM)

**Purpose**: Product data as source of truth for enrichment agents

| System | API Type | Priority | Adapter Purpose |
|--------|----------|----------|-----------------|
| Salsify PXM | REST | High | Omnichannel product content |
| inRiver PIM | REST | High | Product enrichment source |
| Akeneo PIM | REST | Medium | Open-source PIM integration |
| Pimcore | GraphQL/REST | Medium | Flexible PIM/MDM |
| SAP Commerce (Hybris) | OCC REST | Medium | SAP-stack retailers |
| Informatica Product 360 | REST | Low | MDM-based PIM |

**Key Data Flows**:
- Master product data → Normalization agent
- Product attributes → Enrichment (from THIS data, not generated)
- Category taxonomy → Classification agent
- Multilingual content → Localization

### D. Digital Asset Management (DAM)

**Purpose**: Product imagery, marketing assets for catalog

| System | API Type | Priority | Adapter Purpose |
|--------|----------|----------|-----------------|
| Cloudinary | REST | High | Image transformation, CDN |
| Adobe AEM Assets | REST | High | Enterprise DAM |
| Bynder | REST | Medium | Brand asset management |
| Sitecore Content Hub | GraphQL/REST | Low | Integrated DAM+PIM |

**Key Data Flows**:
- Asset URLs → Product catalog
- Image variants → Channel-specific formats
- Metadata → Search indexing
- Rights/expiry → Compliance checks

### E. Commerce & Order Management

**Purpose**: Order capture, fulfillment routing, payment processing

| System | API Type | Priority | Adapter Purpose |
|--------|----------|----------|-----------------|
| Shopify Plus | GraphQL/REST | High | D2C commerce |
| commercetools | GraphQL/REST | High | MACH headless commerce |
| Salesforce Commerce Cloud | REST | High | Enterprise e-commerce |
| Adobe Commerce (Magento) | GraphQL/REST | High | Flexible e-commerce |
| SAP Commerce Cloud | REST | Medium | SAP ecosystem |
| Manhattan OMNI OMS | REST | Medium | Order orchestration |
| VTEX | REST | Low | LATAM markets |

**Key Data Flows**:
- Orders → CRUD service → Event Hubs → Fulfillment agents
- Cart updates → Cart intelligence agent
- Payment events → Payment processing
- Return requests → Returns agent

### F. Data & Analytics Platforms

**Purpose**: Analytics, forecasting, personalization models

| System | API Type | Priority | Adapter Purpose |
|--------|----------|----------|-----------------|
| Azure Synapse | REST/SQL | High | Data warehouse queries |
| Snowflake | SQL/REST | Medium | Cloud data warehouse |
| Databricks | REST/Spark | Medium | ML model serving |
| Google Analytics 4 | REST | Low | Web analytics |
| Adobe Analytics | REST | Low | Digital analytics |

### G. Integration & Messaging

**Purpose**: iPaaS, event streaming, B2B integration

| System | API Type | Priority | Adapter Purpose |
|--------|----------|----------|-----------------|
| Azure Event Hubs | AMQP/HTTP | High | Already integrated |
| Confluent/Kafka | Kafka protocol | Medium | Alternative streaming |
| MuleSoft Anypoint | REST | Low | Enterprise iPaaS |
| IBM Sterling | AS2/EDI | Low | B2B/EDI trading |

## CRUD Service Compliance

The CRUD service will expose a **unified connector interface**:

```python
# lib/src/holiday_peak_lib/connectors/registry.py

class ConnectorRegistry:
    """Registry for enterprise system connectors."""
    
    def __init__(self):
        self._pim: PIMConnectorBase | None = None
        self._dam: DAMConnectorBase | None = None
        self._inventory: InventoryConnectorBase | None = None
        self._crm: CRMConnectorBase | None = None
        self._commerce: CommerceConnectorBase | None = None
    
    def register_pim(self, connector: PIMConnectorBase) -> None:
        """Register PIM connector (Salsify, inRiver, etc.)"""
        self._pim = connector
    
    async def get_product_enrichment_data(self, sku: str) -> ProductEnrichmentData:
        """Get product data from configured PIM for agent enrichment."""
        if self._pim:
            return await self._pim.get_product(sku)
        # Fallback to internal store
        return await self._internal_product_store.get(sku)
```

## Implementation Phases

### Phase 1: Foundation (Q1 2026)
- Define connector contracts in `lib/src/holiday_peak_lib/integrations/contracts.py`
- Implement connector registry in `lib/src/holiday_peak_lib/connectors/registry.py`
- Implement connector base classes
- Create mock servers for testing

### Phase 2: Priority Connectors (Q1-Q2 2026)
- Salsify PXM (PIM)
- Cloudinary (DAM)
- Shopify Plus (Commerce)
- Salesforce CRM
- Azure Synapse (Analytics)

### Phase 3: Enterprise Connectors (Q2-Q3 2026)
- SAP S/4HANA
- Oracle Fusion SCM
- Manhattan Active Omni
- Adobe Experience Platform
- commercetools

### Phase 4: Extended Ecosystem (Q3-Q4 2026)
- Remaining PIM systems (inRiver, Akeneo, Pimcore)
- Additional DAM systems (AEM, Bynder)
- Alternative commerce platforms
- Legacy B2B integration (EDI)

## Success Metrics

- **Connector Coverage**: 80%+ of listed systems have production-ready adapters
- **API Compliance**: 100% adherence to REST API documentation per vendor
- **Test Coverage**: >90% per connector
- **Data Integrity**: Zero data loss in sync operations
- **Latency**: <200ms p95 for read operations, <500ms p95 for writes

## References

- [Retail Capabilities Blueprint](../../improvements.md)
- [ADR-003: Adapter Pattern](../architecture/adrs/adr-003-adapter-pattern.md)
- [ADR-012: Adapter Boundaries](../architecture/adrs/adr-012-adapter-boundaries.md)
- [BaseAdapter Implementation](../../lib/src/holiday_peak_lib/adapters/base.py)
