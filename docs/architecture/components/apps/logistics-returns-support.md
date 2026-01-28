# Logistics Returns Support Service

**Path**: `apps/logistics-returns-support/`  
**Domain**: Logistics  
**Purpose**: Guide returns based on shipment context

## Overview

Builds a returns plan based on shipment status and policy signals.

## Architecture

```mermaid
graph LR
    Client[Returns Request] -->|POST /invoke| API[FastAPI App]
    API --> Agent[Returns Support Agent]
    Agent --> Logistics[Logistics Adapter]
    Agent --> Assistant[Returns Guidance]
```

## Components

### 1. FastAPI Application (`main.py`)

**REST Endpoints**:
- `POST /invoke`
- `GET /health`

**MCP Tools**:
- `/logistics/returns/context`
- `/logistics/returns/plan`

### 2. Returns Support Agent (`agents.py`)

Orchestrates:
- Logistics context
- Returns guidance

**Current Status**: ✅ **IMPLEMENTED (mock adapters)**

### 3. Adapters

**Logistics Adapter**: Shipment + events  
**Assistant**: Returns plan heuristics

**Current Status**: ⚠️ **PARTIAL** — Mock adapters return deterministic data

## What's Implemented

✅ MCP tool registration  
✅ Returns support agent orchestration  
✅ Dockerfile + Bicep module

## What's NOT Implemented

❌ Real carrier/returns integrations  
❌ Foundry model integration for narratives  
❌ Observability dashboards for returns SLA

## Operational Playbooks

- [Tool call failures](../../playbooks/playbook-tool-call-failures.md)
- [Adapter failure](../../playbooks/playbook-adapter-failure.md)
- [Adapter latency spikes](../../playbooks/playbook-adapter-latency-spikes.md)
- [Adapter schema changes](../../playbooks/playbook-adapter-schema-changes.md)

## Sample Implementation

Replace mock logistics adapter with a real carrier/returns API:

```python
from holiday_peak_lib.adapters.base import BaseAdapter
from holiday_peak_lib.adapters.logistics_adapter import LogisticsConnector

class CarrierApiAdapter(BaseAdapter):
    async def _connect_impl(self, **kwargs):
        return None

    async def _fetch_impl(self, query):
        # Query shipment status by tracking_id
        ...

    async def _upsert_impl(self, payload):
        return payload

    async def _delete_impl(self, identifier):
        return True

logistics = LogisticsConnector(adapter=CarrierApiAdapter())
```
