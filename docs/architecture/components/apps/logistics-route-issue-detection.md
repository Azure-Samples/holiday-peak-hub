# Logistics Route Issue Detection Service

**Path**: `apps/logistics-route-issue-detection/`  
**Domain**: Logistics  
**Purpose**: Detect shipment delays and route exceptions

## Overview

Flags shipments with delays or exception states and recommends escalation steps.

## Architecture

```mermaid
graph LR
    Client[Issue Request] -->|POST /invoke| API[FastAPI App]
    API --> Agent[Route Issue Agent]
    Agent --> Logistics[Logistics Adapter]
    Agent --> Detector[Issue Rules]
```

## Components

### 1. FastAPI Application (`main.py`)

**REST Endpoints**:
- `POST /invoke`
- `GET /health`

**MCP Tools**:
- `/logistics/route/context`
- `/logistics/route/issues`

### 2. Route Issue Detection Agent (`agents.py`)

Orchestrates:
- Logistics context
- Issue detection rules

**Current Status**: ✅ **IMPLEMENTED (mock adapters)**

### 3. Adapters

**Logistics Adapter**: Shipment + events  
**Detector**: Issue rules

**Current Status**: ⚠️ **PARTIAL** — Mock adapters return deterministic data

## What's Implemented

✅ MCP tool registration  
✅ Route issue detection agent orchestration  
✅ Dockerfile + Bicep module

## What's NOT Implemented

❌ Real carrier integrations  
❌ Foundry model integration for narratives  
❌ Observability dashboards for route risk

## Operational Playbooks

- [Tool call failures](../../playbooks/playbook-tool-call-failures.md)
- [Adapter failure](../../playbooks/playbook-adapter-failure.md)
- [Adapter latency spikes](../../playbooks/playbook-adapter-latency-spikes.md)
- [Adapter schema changes](../../playbooks/playbook-adapter-schema-changes.md)

## Sample Implementation

Use a real logistics adapter:

```python
from holiday_peak_lib.adapters.base import BaseAdapter
from holiday_peak_lib.adapters.logistics_adapter import LogisticsConnector

class CarrierApiAdapter(BaseAdapter):
    async def _connect_impl(self, **kwargs):
        return None

    async def _fetch_impl(self, query):
        # Query shipment events by tracking_id
        ...

    async def _upsert_impl(self, payload):
        return payload

    async def _delete_impl(self, identifier):
        return True

logistics = LogisticsConnector(adapter=CarrierApiAdapter())
```
