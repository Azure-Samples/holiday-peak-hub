# Inventory Reservation Validation Service

**Path**: `apps/inventory-reservation-validation/`  
**Domain**: Inventory  
**Purpose**: Validate reservation quantities against stock

## Overview

Approves or rejects reservation requests based on effective availability and backorder impact.

## Architecture

```mermaid
graph LR
    Client[Reservation Request] -->|POST /invoke| API[FastAPI App]
    API --> Agent[Reservation Validation Agent]
    Agent --> Inventory[Inventory Adapter]
    Agent --> Validator[Reservation Rules]
```

## Components

### 1. FastAPI Application (`main.py`)

**REST Endpoints**:
- `POST /invoke`
- `GET /health`

**MCP Tools**:
- `/inventory/reservations/context`
- `/inventory/reservations/validate`

### 2. Reservation Validation Agent (`agents.py`)

Orchestrates:
- Inventory context
- Reservation validation logic

**Current Status**: ✅ **IMPLEMENTED (mock adapters)**

### 3. Adapters

**Inventory Adapter**: SKU availability + warehouse stock  
**Validator**: Reservation rules

**Current Status**: ⚠️ **PARTIAL** — Mock adapters return deterministic data

## What's Implemented

✅ MCP tool registration  
✅ Reservation validation agent orchestration  
✅ Dockerfile + Bicep module

## What's NOT Implemented

❌ Real inventory integration  
❌ Foundry model integration for narratives  
❌ Observability dashboards for reservation failures

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
