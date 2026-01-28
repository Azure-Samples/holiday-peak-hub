# Product Management Normalization & Classification Service

**Path**: `apps/product-management-normalization-classification/`  
**Domain**: Product Management  
**Purpose**: Normalize product data and assign classifications

## Overview

Normalizes names, categories, and tags, then assigns a product classification.

## Architecture

```mermaid
graph LR
    Client[Normalization Request] -->|POST /invoke| API[FastAPI App]
    API --> Agent[Normalization Agent]
    Agent --> Products[Product Adapter]
    Agent --> Normalizer[Normalization Rules]
```

## Components

### 1. FastAPI Application (`main.py`)

**REST Endpoints**:
- `POST /invoke`
- `GET /health`

**MCP Tools**:
- `/product/normalize`
- `/product/classify`

### 2. Normalization Agent (`agents.py`)

Orchestrates:
- Product retrieval
- Normalization + classification

**Current Status**: ✅ **IMPLEMENTED (mock adapters)**

### 3. Adapters

**Product Adapter**: Catalog product retrieval  
**Normalizer**: Normalization heuristics

**Current Status**: ⚠️ **PARTIAL** — Mock adapters return deterministic data

## What's Implemented

✅ MCP tool registration  
✅ Normalization agent orchestration  
✅ Dockerfile + Bicep module

## What's NOT Implemented

❌ Real product integrations  
❌ Foundry model integration for taxonomy curation  
❌ Observability dashboards for taxonomy drift

## Operational Playbooks

- [Tool call failures](../../playbooks/playbook-tool-call-failures.md)
- [Adapter failure](../../playbooks/playbook-adapter-failure.md)
- [Adapter latency spikes](../../playbooks/playbook-adapter-latency-spikes.md)
- [Agent latency spikes](../../playbooks/playbook-agent-latency-spikes.md)

## Sample Implementation

Use a real product catalog adapter:

```python
from holiday_peak_lib.adapters.base import BaseAdapter
from holiday_peak_lib.adapters.product_adapter import ProductConnector

class CatalogApiAdapter(BaseAdapter):
    async def _connect_impl(self, **kwargs):
        return None

    async def _fetch_impl(self, query):
        # Fetch product by SKU
        ...

    async def _upsert_impl(self, payload):
        return payload

    async def _delete_impl(self, identifier):
        return True

products = ProductConnector(adapter=CatalogApiAdapter())
```
