# Agent Playgrounds

**Status**: Phase 2 - In Progress  
**Target Completion**: February 10, 2026

---

## Overview

Interactive Jupyter notebooks for exploring agent capabilities with rich visualizations, step-by-step narratives, and performance metrics.

---

## Notebooks

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

## Coming Soon

- [ ] E-Commerce notebook (February 5, 2026)
- [ ] Product Management notebook (February 7, 2026)
- [ ] CRM notebook (February 8, 2026)
- [ ] Inventory notebook (February 9, 2026)
- [ ] Logistics notebook (February 10, 2026)

---

## Next Steps

1. Load [Sample Data](../sample-data/)
2. Start with [E-Commerce notebook](ecommerce-agents.ipynb)
3. Try [Interactive Scenarios](../interactive-scenarios/)
