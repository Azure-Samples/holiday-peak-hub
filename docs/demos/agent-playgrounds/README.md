# Agent Playgrounds

**Status**: Phase 2 - In Progress  
**Recommended Approach**: Use [Interactive Scenarios](../interactive-scenarios/) for hands-on demos

---

## Overview

Interactive Jupyter notebooks for exploring agent capabilities with rich visualizations, step-by-step narratives, and performance metrics.

> **Note**: Notebooks are planned but not yet available. In the meantime, use the **Interactive Scenarios** below as the recommended approach for hands-on exploration of agent capabilities. Each scenario includes step-by-step curl commands and expected responses.

---

## Recommended: Interactive Scenarios

While notebooks are being developed, use these detailed scenario guides:

| Scenario | Agents | Guide |
| --- | --- | --- |
| Customer Journey | 8 agents (search → order → delivery) | [customer-journey.md](../interactive-scenarios/customer-journey.md) |
| Order Fulfillment | 8 agents (SAGA choreography) | [order-fulfillment.md](../interactive-scenarios/order-fulfillment.md) |
| CRM Campaigns | 5 agents (profile → segment → campaign) | [crm-campaigns.md](../interactive-scenarios/crm-campaigns.md) |
| Product Lifecycle | 5 agents (ingest → normalize → optimize) | [product-lifecycle.md](../interactive-scenarios/product-lifecycle.md) |

Each scenario includes:

- Actual API calls with request/response payloads
- Event Hub message examples
- Memory tier usage
- Performance metrics
- Error handling demonstrations

---

## Notebooks

### Retailer IQ / RecommenderIQ Live Demo

**Executive notebook**: [retailer_iq_recommender_system_demo.ipynb](retailer_iq_recommender_system_demo.ipynb)  
**Notebook**: [retailer_iq_recommender_system_live.ipynb](retailer_iq_recommender_system_live.ipynb)  
**Services**: All deployed agent services + CRUD + UI endpoint discovery for `holidaypeakhub405` dev

**Sections**:

1. Executive thesis for Retailer IQ and the Azure operating fabric
2. Traditional retail flows versus Retailer IQ signal coverage
3. Agentic microservice map across every deployed agent
4. Business KPI model for conversion, NPS/CSAT, margin, revenue, and revenue per platform dollar
5. Live APIM/UI endpoint discovery and service health sweep
6. Recommendation-agent candidate, rank, compose, explain, feedback, and model-status probes
7. Customer-experience readiness gates and executive close

**Visualizations**:

- Azure operating-fabric cards
- Traditional versus Retailer IQ comparison table
- Retailer IQ capability graph
- Service inventory cards grouped by domain
- Business impact KPI scorecard
- Live health/status grid
- Recommendation ranking table and UI card preview
- Readiness-gate scorecard

### E-Commerce Domain

**Notebook**: [ecommerce-agents.ipynb](ecommerce-agents.ipynb)  
**Agents**: Catalog Search, Product Detail Enrichment, Cart Intelligence, Checkout Support, Order Status

**Sections**:

1. Product Discovery with AI Search
2. PDP Enrichment with ACP Content
3. Smart Cart Recommendations
4. Checkout Validation and Pricing
5. Order Tracking and ETA

**Visualizations**:

- Search relevance scoring
- Enrichment before/after comparison
- Cart bundle suggestions
- Inventory allocation flow
- Delivery timeline

---

### Product Management Domain

**Notebook**: [product-mgmt-agents.ipynb](product-mgmt-agents.ipynb)  
**Agents**: Normalization/Classification, ACP Transformation, Consistency Validation, Assortment Optimization

**Sections**:

1. Taxonomy Normalization
2. ACP Content Generation
3. Data Quality Validation
4. Category Optimization

**Visualizations**:

- Category mapping flow
- Completeness score improvement
- Validation report dashboard
- Assortment performance heatmap

---

### CRM Domain

**Notebook**: [crm-agents.ipynb](crm-agents.ipynb)  
**Agents**: Profile Aggregation, Segmentation/Personalization, Campaign Intelligence, Support Assistance

**Sections**:

1. Unified Customer View
2. Dynamic Segmentation
3. Campaign ROI Prediction
4. Support Ticket Intelligence

**Visualizations**:

- Customer journey timeline
- Segment distribution
- Campaign performance forecast
- Ticket sentiment analysis

---

### Inventory Domain

**Notebook**: [inventory-agents.ipynb](inventory-agents.ipynb)  
**Agents**: Health Check, JIT Replenishment, Reservation Validation, Alerts/Triggers

**Sections**:

1. Stock Health Monitoring
2. Demand-Sensing Reorder
3. Real-Time Allocation
4. Exception Alerts

**Visualizations**:

- Stock level trends
- Reorder trigger timeline
- Reservation flow diagram
- Alert frequency heatmap

---

### Logistics Domain

**Notebook**: [logistics-agents.ipynb](logistics-agents.ipynb)  
**Agents**: ETA Computation, Carrier Selection, Returns Support, Route Issue Detection

**Sections**:

1. Delivery Time Prediction
2. Carrier Cost/Speed Trade-off
3. Reverse Logistics Automation
4. Proactive Delay Detection

**Visualizations**:

- ETA confidence intervals
- Carrier comparison table
- Returns processing funnel
- Route issue map

---

## Prerequisites

### Install Jupyter

```bash
pip install jupyter pandas plotly matplotlib seaborn requests python-dotenv
```

### Start Notebook Server

```bash
jupyter notebook docs/demos/agent-playgrounds/
```

### Environment Setup

Create `.env` file:

```bash
CRUD_URL=http://localhost:8000
AGENT_BASE_URL=http://localhost:8001
REDIS_URL=redis://localhost:6379/0
```

---

## Features

### Interactive Code Cells

- Live agent API calls
- Real-time response inspection
- Memory tier queries
- Performance metrics

### Rich Visualizations

- **Pandas DataFrames** for tabular data
- **Plotly** for interactive charts
- **Matplotlib/Seaborn** for statistical plots
- **Rich** library for formatted CLI output

### Memory Inspection

- Redis cache hit/miss rates
- Cosmos DB query performance
- Blob Storage access patterns
- TTL and eviction monitoring

### Performance Analysis

- SLM vs LLM routing decisions
- Response time breakdown
- Token usage per request
- Cost estimation

---

## Running Notebooks

### Option 1: Jupyter Classic

```bash
jupyter notebook ecommerce-agents.ipynb
```

### Option 2: JupyterLab

```bash
jupyter lab
```

### Option 3: VS Code

Install Jupyter extension and open `.ipynb` files directly in VS Code

---

## Coming Soon — Notebooks

- [x] Retailer IQ / RecommenderIQ live demo
- [ ] E-Commerce notebook
- [ ] Product Management notebook
- [ ] CRM notebook
- [ ] Inventory notebook
- [ ] Logistics notebook

---

## Next Steps

1. Start with [Interactive Scenarios](../interactive-scenarios/) for immediate exploration
2. Load [Sample Data](../sample-data/) to populate the CRUD service
3. Use [API Examples](../api-examples/) for quick curl/PowerShell reference
