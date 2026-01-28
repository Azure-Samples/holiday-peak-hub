# Inventory JIT Replenishment Service

**Path**: `apps/inventory-jit-replenishment/`  
**Domain**: Inventory  
**Purpose**: Recommend just-in-time replenishment quantities

## Overview

Computes reorder quantities based on availability, reserved stock, and target inventory levels.

## Architecture

```mermaid
graph LR
    Client[Replenishment Request] -->|POST /invoke| API[FastAPI App]
    API --> Agent[Replenishment Agent]
    Agent --> Inventory[Inventory Adapter]
    Agent --> Planner[Replenishment Planner]
```

## Components

### 1. FastAPI Application (`main.py`)

**REST Endpoints**:
- `POST /invoke`
- `GET /health`

**MCP Tools**:
- `/inventory/replenishment/context`
- `/inventory/replenishment/plan`

### 2. Replenishment Agent (`agents.py`)

Orchestrates:
- Inventory context
- Replenishment planning

**Current Status**: ✅ **IMPLEMENTED (mock adapters)**

### 3. Adapters

**Inventory Adapter**: SKU availability + warehouse stock  
**Planner**: Reorder recommendation rules

**Current Status**: ⚠️ **PARTIAL** — Mock adapters return deterministic data

## What's Implemented

✅ MCP tool registration  
✅ Replenishment agent orchestration  
✅ Dockerfile + Bicep module

## What's NOT Implemented

❌ Real inventory integration  
❌ Foundry model integration for narratives  
❌ Observability dashboards for replenishment accuracy

## Operational Playbooks

- [Agent latency spikes](../../playbooks/playbook-agent-latency-spikes.md)
- [Tool call failures](../../playbooks/playbook-tool-call-failures.md)
- [Adapter latency spikes](../../playbooks/playbook-adapter-latency-spikes.md)
- [Adapter failure](../../playbooks/playbook-adapter-failure.md)

## Sample Implementation

Use a real inventory API adapter:

```python
from holiday_peak_lib.adapters.base import BaseAdapter
from holiday_peak_lib.adapters.inventory_adapter import InventoryConnector

class InventoryApiAdapter(BaseAdapter):
    async def _connect_impl(self, **kwargs):
        return None

    async def _fetch_impl(self, query):
        # Fetch inventory by SKU
        ...

    async def _upsert_impl(self, payload):
        return payload

    async def _delete_impl(self, identifier):
        return True

inventory = InventoryConnector(adapter=InventoryApiAdapter())
```
