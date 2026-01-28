# CRM Profile Aggregation Service

**Path**: `apps/crm-profile-aggregation/`  
**Domain**: CRM  
**Purpose**: Aggregate customer profile context for downstream agents

## Overview

Builds a consolidated CRM profile with account and interaction history for use by other services.

## Architecture

```mermaid
graph LR
    Client[Profile Request] -->|POST /invoke| API[FastAPI App]
    API --> Agent[Profile Aggregation Agent]
    Agent --> CRM[CRM Adapter]
    Agent --> Analytics[Profile Summary]
```

## Components

### 1. FastAPI Application (`main.py`)

**REST Endpoints**:
- `POST /invoke`
- `GET /health`

**MCP Tools**:
- `/crm/profile/context`
- `/crm/profile/summary`
- `/crm/profile/account`

### 2. Profile Aggregation Agent (`agents.py`)

Orchestrates:
- CRM context assembly
- Profile summarization

**Current Status**: ✅ **IMPLEMENTED (mock adapters)**

### 3. Adapters

**CRM Adapter**: Contact/account/interactions  
**Analytics Adapter**: Profile summary heuristics

**Current Status**: ⚠️ **PARTIAL** — Mock adapters return deterministic data

## What's Implemented

✅ MCP tool registration  
✅ Profile aggregation agent orchestration  
✅ Dockerfile + Bicep module

## What's NOT Implemented

❌ Real CRM integrations  
❌ Foundry model integration for narratives  
❌ Observability dashboards for profile quality

## Operational Playbooks

- [Agent latency spikes](../../playbooks/playbook-agent-latency-spikes.md)
- [Tool call failures](../../playbooks/playbook-tool-call-failures.md)
- [Adapter failure](../../playbooks/playbook-adapter-failure.md)
- [Adapter schema changes](../../playbooks/playbook-adapter-schema-changes.md)

## Sample Implementation

Swap in a CRM adapter with real API calls:

```python
from holiday_peak_lib.adapters.base import BaseAdapter
from holiday_peak_lib.adapters.crm_adapter import CRMConnector

class CrmApiAdapter(BaseAdapter):
    async def _connect_impl(self, **kwargs):
        return None

    async def _fetch_impl(self, query):
        # Call CRM API by entity type
        ...

    async def _upsert_impl(self, payload):
        return payload

    async def _delete_impl(self, identifier):
        return True

crm = CRMConnector(adapter=CrmApiAdapter())
```
