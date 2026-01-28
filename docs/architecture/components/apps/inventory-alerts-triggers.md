# Inventory Alerts & Triggers Service

**Path**: `apps/inventory-alerts-triggers/`  
**Domain**: Inventory  
**Purpose**: Detect low-stock and reservation pressure triggers

## Overview

Evaluates inventory context and flags alert conditions for replenishment or escalation.

## Architecture

```mermaid
graph LR
    Client[Alert Request] -->|POST /invoke| API[FastAPI App]
    API --> Agent[Inventory Alerts Agent]
    Agent --> Inventory[Inventory Adapter]
    Agent --> Analytics[Alert Rules]
```

## Components

### 1. FastAPI Application (`main.py`)

**REST Endpoints**:
- `POST /invoke`
- `GET /health`

**MCP Tools**:
- `/inventory/alerts/context`
- `/inventory/alerts`

### 2. Inventory Alerts Agent (`agents.py`)

Orchestrates:
- Inventory context
- Alert rule evaluation

**Current Status**: ✅ **IMPLEMENTED (mock adapters)**

### 3. Adapters

**Inventory Adapter**: SKU availability + warehouse stock  
**Analytics Adapter**: Alert rules

**Current Status**: ⚠️ **PARTIAL** — Mock adapters return deterministic data

## What's Implemented

✅ MCP tool registration  
✅ Alert agent orchestration  
✅ Dockerfile + Bicep module

## What's NOT Implemented

❌ Real inventory integration  
❌ Foundry model integration for recommendations  
❌ Observability dashboards for stock alerts

## Operational Playbooks

- [Agent latency spikes](../../playbooks/playbook-agent-latency-spikes.md)
- [Tool call failures](../../playbooks/playbook-tool-call-failures.md)
- [Adapter latency spikes](../../playbooks/playbook-adapter-latency-spikes.md)
- [Adapter failure](../../playbooks/playbook-adapter-failure.md)
- [Redis OOM](../../playbooks/playbook-redis-oom.md)

## Sample Implementation

Use a real inventory API adapter:

```python
from holiday_peak_lib.adapters.base import BaseAdapter
from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector

class InventoryApiAdapter(BaseAdapter):
    async def _connect_impl(self, **kwargs):
        return None

    async def _fetch_impl(self, query):
        # Call inventory API
        ...

    async def _upsert_impl(self, payload):
        return payload

    async def _delete_impl(self, identifier):
        return True

inventory = InventoryConnector(adapter=InventoryApiAdapter())
```
