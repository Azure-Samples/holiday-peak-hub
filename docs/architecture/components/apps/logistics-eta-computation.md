# Logistics ETA Computation Service

**Path**: `apps/logistics-eta-computation/`  
**Domain**: Logistics  
**Purpose**: Compute updated ETA for shipments

## Overview

Calculates ETA based on shipment status and event history.

## Architecture

```mermaid
graph LR
    Client[ETA Request] -->|POST /invoke| API[FastAPI App]
    API --> Agent[ETA Agent]
    Agent --> Logistics[Logistics Adapter]
    Agent --> Estimator[ETA Rules]
```

## Components

### 1. FastAPI Application (`main.py`)

**REST Endpoints**:
- `POST /invoke`
- `GET /health`

**MCP Tools**:
- `/logistics/eta/context`
- `/logistics/eta`

### 2. ETA Computation Agent (`agents.py`)

Orchestrates:
- Logistics context
- ETA computation rules

**Current Status**: ✅ **IMPLEMENTED (mock adapters)**

### 3. Adapters

**Logistics Adapter**: Shipment + events  
**Estimator**: ETA computation rules

**Current Status**: ⚠️ **PARTIAL** — Mock adapters return deterministic data

## What's Implemented

✅ MCP tool registration  
✅ ETA computation agent orchestration  
✅ Dockerfile + Bicep module

## What's NOT Implemented

❌ Real carrier integrations  
❌ Foundry model integration for narrative updates  
❌ Observability dashboards for ETA accuracy

## Operational Playbooks

- [Agent latency spikes](../../playbooks/playbook-agent-latency-spikes.md)
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
