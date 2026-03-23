# Agent Demonstration Guide

**Last Updated**: February 3, 2026  
**Status**: Phase 1 Complete | Phases 2-4 In Progress

---

## Overview

This directory contains comprehensive demonstrations for all 21 agent services in Holiday Peak Hub. Each demo is designed to showcase agent capabilities through realistic retail scenarios, from quick API calls to complex multi-agent workflows.

### Live Operator Runbook

- [Search + Enrichment + HITL Live Demo](live-demo-search-enrichment-hitl.md)

---

## Demo Structure

### Three-Tier Demonstration Approach

#### **Tier 1: Quick Start** (5 minutes per agent)
- Single API call with sample request/response
- Clear annotation of inputs and outputs
- Command-line ready (curl/PowerShell)

#### **Tier 2: Interactive Scenarios** (15-20 minutes)
- Business-driven multi-step workflows
- Agent collaboration via MCP tools
- Visual outputs and metrics

#### **Tier 3: Deep Dive** (30-45 minutes)
- Architecture exploration
- Memory tier inspection (hot/warm/cold)
- Event-driven flows and observability

---

## Implementation Phases

### ✅ Phase 1: Foundation (Complete)
**Duration**: 2-3 days  
**Status**: Complete

#### Deliverables
- [x] Demo directory structure
- [x] Demo index (this file)
- [x] Postman collection with all 21 agents ([postman-collection.json](api-examples/postman-collection.json))
- [x] Sample data generators ([sample-data/](sample-data/))
- [x] Quick start CLI examples ([api-examples/curl-examples.sh](api-examples/curl-examples.sh))

#### Sample Data Sets
- **Products**: 500 SKUs across 8 categories (Electronics, Apparel, Toys, Home, Beauty, Sports, Books, Groceries)
- **Users**: 100 customer profiles with purchase history
- **Orders**: 200 historical orders with varying statuses
- **Reviews**: 300 product reviews with ratings
- **Inventory**: Stock levels across 5 warehouses

---

### 🚧 Phase 2: Interactive Notebooks (In Progress)
**Duration**: 1 week  
**Status**: In Progress  
**Target Completion**: February 10, 2026

#### Deliverables
- [ ] E-Commerce Domain Notebook ([agent-playgrounds/ecommerce-agents.ipynb](agent-playgrounds/ecommerce-agents.ipynb))
  - Catalog Search Agent
  - Product Detail Enrichment Agent
  - Cart Intelligence Agent
  - Checkout Support Agent
  - Order Status Agent

- [ ] Product Management Domain Notebook ([agent-playgrounds/product-mgmt-agents.ipynb](agent-playgrounds/product-mgmt-agents.ipynb))
  - Normalization/Classification Agent
  - ACP Transformation Agent
  - Consistency Validation Agent
  - Assortment Optimization Agent

- [ ] CRM Domain Notebook ([agent-playgrounds/crm-agents.ipynb](agent-playgrounds/crm-agents.ipynb))
  - Profile Aggregation Agent
  - Segmentation/Personalization Agent
  - Campaign Intelligence Agent
  - Support Assistance Agent

- [ ] Inventory Domain Notebook ([agent-playgrounds/inventory-agents.ipynb](agent-playgrounds/inventory-agents.ipynb))
  - Health Check Agent
  - JIT Replenishment Agent
  - Reservation Validation Agent
  - Alerts/Triggers Agent

- [ ] Logistics Domain Notebook ([agent-playgrounds/logistics-agents.ipynb](agent-playgrounds/logistics-agents.ipynb))
  - ETA Computation Agent
  - Carrier Selection Agent
  - Returns Support Agent
  - Route Issue Detection Agent

#### Features
- Rich visualizations (pandas, plotly, matplotlib)
- Step-by-step narratives with business context
- Memory tier inspection (Redis cache hits, Cosmos queries)
- Performance metrics (SLM vs LLM routing, response times)
- Error handling and fallback demonstrations

---

### 📋 Phase 3: End-to-End Scenarios (Planned)
**Duration**: 1 week  
**Status**: Planned  
**Target Completion**: February 17, 2026

#### Deliverables

##### Scenario 1: Customer Journey
**File**: [interactive-scenarios/customer-journey.md](interactive-scenarios/customer-journey.md)

**Flow**: Anonymous Visitor → Product Discovery → Cart → Checkout → Order Tracking

**Agents Involved**:
1. **Catalog Search Agent** - Product discovery with AI-powered search
2. **Product Detail Enrichment Agent** - Enriched product page with ACP content
3. **Cart Intelligence Agent** - Smart bundle recommendations
4. **Inventory Reservation Validation Agent** - Real-time stock allocation
5. **Checkout Support Agent** - Dynamic pricing and shipping options
6. **Carrier Selection Agent** - Optimal carrier based on cost/speed
7. **ETA Computation Agent** - Delivery date prediction
8. **Order Status Agent** - Proactive tracking updates

**Outputs**:
- Complete trace of agent interactions
- MCP tool calls between agents
- Event Hub message flow
- Frontend integration examples

---

##### Scenario 2: Product Lifecycle
**File**: [interactive-scenarios/product-lifecycle.md](interactive-scenarios/product-lifecycle.md)

**Flow**: Product Ingestion → Normalization → Enrichment → Quality Check → Optimization

**Agents Involved**:
1. **Normalization/Classification Agent** - Taxonomy alignment and categorization
2. **ACP Transformation Agent** - Standards-compliant catalog export
3. **Product Detail Enrichment Agent** - ACP content integration
4. **Consistency Validation Agent** - Data quality checks and scoring
5. **Assortment Optimization Agent** - SKU mix recommendations

**Outputs**:
- Before/after data quality comparison
- Completeness scores and validation reports
- Event-driven enrichment flow
- Batch processing metrics

---

##### Scenario 3: Order Fulfillment
**File**: [interactive-scenarios/order-fulfillment.md](interactive-scenarios/order-fulfillment.md)

**Flow**: Order Placed → Inventory Allocation → Carrier Selection → Shipment → Delivery → Returns (if needed)

**Agents Involved**:
1. **Checkout Support Agent** - Order validation and finalization
2. **Inventory Reservation Validation Agent** - Stock allocation locking
3. **JIT Replenishment Agent** - Trigger reorder if needed
4. **Carrier Selection Agent** - Optimal shipping method
5. **ETA Computation Agent** - Delivery estimation
6. **Route Issue Detection Agent** - Proactive delay detection
7. **Order Status Agent** - Customer notifications
8. **Returns Support Agent** - Reverse logistics (if needed)

**Outputs**:
- Real-time event choreography
- Inventory state transitions
- SAGA compensation patterns
- Customer notification timeline

---

##### Scenario 4: CRM Campaign Creation
**File**: [interactive-scenarios/crm-campaigns.md](interactive-scenarios/crm-campaigns.md)

**Flow**: Customer Data → Segmentation → Campaign Design → Personalization → ROI Analysis

**Agents Involved**:
1. **Profile Aggregation Agent** - Unified customer view
2. **Segmentation/Personalization Agent** - Dynamic cohort building
3. **Assortment Optimization Agent** - Product recommendations per segment
4. **Campaign Intelligence Agent** - ROI-optimized campaign generation
5. **Support Assistance Agent** - Post-campaign customer service

**Outputs**:
- Customer segment definitions
- Personalized product recommendations
- Campaign performance predictions
- A/B test suggestions

---

### 📹 Phase 4: Video & Documentation (Planned)
**Duration**: 3-4 days  
**Status**: Planned  
**Target Completion**: February 21, 2026

#### Deliverables
- [ ] Screen recordings for each end-to-end scenario
- [ ] Agent architecture walkthrough videos
- [ ] YouTube playlist creation
- [ ] Update all agent READMEs with demo links
- [ ] Create interactive docs site (optional: Docusaurus/MkDocs)

#### Video Content
1. **Quick Start Series** (5 videos, 5-10 mins each)
   - E-Commerce Agents Overview
   - Product Management Agents Overview
   - CRM Agents Overview
   - Inventory Agents Overview
   - Logistics Agents Overview

2. **Deep Dive Series** (4 videos, 20-30 mins each)
   - Customer Journey End-to-End
   - Product Lifecycle Management
   - Order Fulfillment Choreography
   - CRM Campaign Intelligence

3. **Architecture Series** (3 videos, 15-20 mins each)
   - Agent Framework Deep Dive
   - Three-Tier Memory Architecture
   - MCP Tool Exposition and Inter-Agent Communication

---

## Quick Start Guide

### Prerequisites
```bash
# Ensure all services are running
cd apps/crud-service/src && uvicorn crud_service.main:app --reload --port 8000

# Start an agent (example: Product Detail Enrichment)
cd apps/ecommerce-product-detail-enrichment/src && uvicorn main:app --reload --port 8001
```

### Run a Quick Demo

#### Option 1: Using curl (Linux/macOS/WSL)
```bash
# Load sample data
bash docs/demos/sample-data/load-sample-data.sh

# Run product enrichment demo
bash docs/demos/api-examples/curl-examples.sh enrichment
```

#### Option 2: Using PowerShell (Windows)
```powershell
# Load sample data
.\docs\demos\sample-data\load-sample-data.ps1

# Run product enrichment demo
.\docs\demos\api-examples\demo-enrichment.ps1
```

#### Option 3: Using Postman
1. Import `docs/demos/api-examples/postman-collection.json`
2. Set environment variables (CRUD_URL, AGENT_URL)
3. Run collection with sample data

#### Option 4: Using Jupyter Notebooks
```bash
# Install Jupyter
pip install jupyter pandas plotly matplotlib

# Launch notebook
jupyter notebook docs/demos/agent-playgrounds/ecommerce-agents.ipynb
```

---

## Agent Quick Reference

### E-Commerce Domain

| Agent | Port | Quick Demo | Notebook Section |
|-------|------|------------|------------------|
| [Catalog Search](../architecture/components/apps/ecommerce-catalog-search.md) | 8001 | `curl -X POST http://localhost:8001/invoke -d '{"query": "wireless headphones"}'` | [ecommerce-agents.ipynb](agent-playgrounds/ecommerce-agents.ipynb#catalog-search) |
| [Product Detail Enrichment](../architecture/components/apps/ecommerce-product-detail-enrichment.md) | 8002 | `curl -X POST http://localhost:8002/invoke -d '{"sku": "PROD-12345"}'` | [ecommerce-agents.ipynb](agent-playgrounds/ecommerce-agents.ipynb#enrichment) |
| [Cart Intelligence](../architecture/components/apps/ecommerce-cart-intelligence.md) | 8003 | `curl -X POST http://localhost:8003/invoke -d '{"user_id": "user-123"}'` | [ecommerce-agents.ipynb](agent-playgrounds/ecommerce-agents.ipynb#cart) |
| [Checkout Support](../architecture/components/apps/ecommerce-checkout-support.md) | 8004 | `curl -X POST http://localhost:8004/invoke -d '{"cart_id": "cart-123"}'` | [ecommerce-agents.ipynb](agent-playgrounds/ecommerce-agents.ipynb#checkout) |
| [Order Status](../architecture/components/apps/ecommerce-order-status.md) | 8005 | `curl -X POST http://localhost:8005/invoke -d '{"order_id": "ORD-123"}'` | [ecommerce-agents.ipynb](agent-playgrounds/ecommerce-agents.ipynb#order-status) |

### Product Management Domain

| Agent | Port | Quick Demo | Notebook Section |
|-------|------|------------|------------------|
| [Normalization/Classification](../architecture/components/apps/product-management-normalization-classification.md) | 8006 | `curl -X POST http://localhost:8006/invoke -d '{"product_data": {...}}'` | [product-mgmt-agents.ipynb](agent-playgrounds/product-mgmt-agents.ipynb#normalization) |
| [ACP Transformation](../architecture/components/apps/product-management-acp-transformation.md) | 8007 | `curl -X POST http://localhost:8007/invoke -d '{"sku": "PROD-12345"}'` | [product-mgmt-agents.ipynb](agent-playgrounds/product-mgmt-agents.ipynb#acp) |
| [Consistency Validation](../architecture/components/apps/product-management-consistency-validation.md) | 8008 | `curl -X POST http://localhost:8008/invoke -d '{"sku": "PROD-12345"}'` | [product-mgmt-agents.ipynb](agent-playgrounds/product-mgmt-agents.ipynb#validation) |
| [Assortment Optimization](../architecture/components/apps/product-management-assortment-optimization.md) | 8009 | `curl -X POST http://localhost:8009/invoke -d '{"category": "electronics"}'` | [product-mgmt-agents.ipynb](agent-playgrounds/product-mgmt-agents.ipynb#assortment) |

### CRM Domain

| Agent | Port | Quick Demo | Notebook Section |
|-------|------|------------|------------------|
| [Profile Aggregation](../architecture/components/apps/crm-profile-aggregation.md) | 8010 | `curl -X POST http://localhost:8010/invoke -d '{"user_id": "user-123"}'` | [crm-agents.ipynb](agent-playgrounds/crm-agents.ipynb#profile) |
| [Segmentation/Personalization](../architecture/components/apps/crm-segmentation-personalization.md) | 8011 | `curl -X POST http://localhost:8011/invoke -d '{"segment_criteria": {...}}'` | [crm-agents.ipynb](agent-playgrounds/crm-agents.ipynb#segmentation) |
| [Campaign Intelligence](../architecture/components/apps/crm-campaign-intelligence.md) | 8012 | `curl -X POST http://localhost:8012/invoke -d '{"campaign_goal": "increase_aov"}'` | [crm-agents.ipynb](agent-playgrounds/crm-agents.ipynb#campaign) |
| [Support Assistance](../architecture/components/apps/crm-support-assistance.md) | 8013 | `curl -X POST http://localhost:8013/invoke -d '{"ticket_id": "TKT-123"}'` | [crm-agents.ipynb](agent-playgrounds/crm-agents.ipynb#support) |

### Inventory Domain

| Agent | Port | Quick Demo | Notebook Section |
|-------|------|------------|------------------|
| [Health Check](../architecture/components/apps/inventory-health-check.md) | 8014 | `curl -X POST http://localhost:8014/invoke -d '{"sku": "PROD-12345"}'` | [inventory-agents.ipynb](agent-playgrounds/inventory-agents.ipynb#health) |
| [JIT Replenishment](../architecture/components/apps/inventory-jit-replenishment.md) | 8015 | `curl -X POST http://localhost:8015/invoke -d '{"sku": "PROD-12345"}'` | [inventory-agents.ipynb](agent-playgrounds/inventory-agents.ipynb#jit) |
| [Reservation Validation](../architecture/components/apps/inventory-reservation-validation.md) | 8016 | `curl -X POST http://localhost:8016/invoke -d '{"sku": "PROD-12345", "quantity": 2}'` | [inventory-agents.ipynb](agent-playgrounds/inventory-agents.ipynb#reservation) |
| [Alerts/Triggers](../architecture/components/apps/inventory-alerts-triggers.md) | 8017 | `curl -X POST http://localhost:8017/invoke -d '{"alert_type": "low_stock"}'` | [inventory-agents.ipynb](agent-playgrounds/inventory-agents.ipynb#alerts) |

### Logistics Domain

| Agent | Port | Quick Demo | Notebook Section |
|-------|------|------------|------------------|
| [ETA Computation](../architecture/components/apps/logistics-eta-computation.md) | 8018 | `curl -X POST http://localhost:8018/invoke -d '{"order_id": "ORD-123"}'` | [logistics-agents.ipynb](agent-playgrounds/logistics-agents.ipynb#eta) |
| [Carrier Selection](../architecture/components/apps/logistics-carrier-selection.md) | 8019 | `curl -X POST http://localhost:8019/invoke -d '{"destination": "90210", "weight": 5}'` | [logistics-agents.ipynb](agent-playgrounds/logistics-agents.ipynb#carrier) |
| [Returns Support](../architecture/components/apps/logistics-returns-support.md) | 8020 | `curl -X POST http://localhost:8020/invoke -d '{"order_id": "ORD-123", "reason": "defective"}'` | [logistics-agents.ipynb](agent-playgrounds/logistics-agents.ipynb#returns) |
| [Route Issue Detection](../architecture/components/apps/logistics-route-issue-detection.md) | 8021 | `curl -X POST http://localhost:8021/invoke -d '{"shipment_id": "SHIP-123"}'` | [logistics-agents.ipynb](agent-playgrounds/logistics-agents.ipynb#route-issues) |

---

## Demo Features

### Memory Tier Inspection
All demos include memory tier visibility:
- **Hot Memory (Redis)**: Cache hits and TTL inspection
- **Warm Memory (Cosmos DB)**: Recent enrichments and queries
- **Cold Memory (Blob Storage)**: Historical data retrieval

### SLM vs LLM Routing
Performance comparisons demonstrating:
- SLM-first routing for simple queries (< 100ms)
- LLM escalation for complex reasoning (200-500ms)
- Cost implications (tokens used per request)

### Event-Driven Flows
Async processing demonstrations:
- Event Hub message publishing
- Consumer group processing
- SAGA choreography patterns
- Compensation flows

### Agent Collaboration
MCP tool exposition:
- Agent-to-agent communication
- Structured data exchange
- Dependency resolution
- Error handling and fallbacks

---

## Contributing Demos

When adding new demos:
1. Follow the three-tier structure (Quick Start, Interactive, Deep Dive)
2. Include realistic sample data
3. Add performance metrics and timing
4. Document agent interactions and MCP calls
5. Update this index with new content
6. Add video recordings where applicable

---

## Resources

- **Architecture Documentation**: [docs/architecture/](../architecture/)
- **Component Documentation**: [docs/architecture/components.md](../architecture/components.md)
- **CRUD Service Implementation**: [docs/architecture/crud-service-implementation.md](../architecture/crud-service-implementation.md)
- **Implementation Roadmap**: [docs/IMPLEMENTATION_ROADMAP.md](../IMPLEMENTATION_ROADMAP.md)
- **Frontend Integration**: [apps/ui/INTEGRATION.md](../../apps/ui/INTEGRATION.md)

---

## Support

For questions or issues with demos:
- **GitHub Issues**: [Azure-Samples/holiday-peak-hub/issues](https://github.com/Azure-Samples/holiday-peak-hub/issues)
- **Discussions**: [Azure-Samples/holiday-peak-hub/discussions](https://github.com/Azure-Samples/holiday-peak-hub/discussions)
- **Documentation**: [docs/README.md](../README.md)
