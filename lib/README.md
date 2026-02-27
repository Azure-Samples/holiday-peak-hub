# Holiday Peak Lib

> **v1.0.0** — First stable release. [GitHub Release](https://github.com/Azure-Samples/holiday-peak-hub/releases/tag/v1.0.0)

Core micro-framework for retail agent services. Provides adapters, agents with builder pattern, MCP + FastAPI integration, multi-tier memory (Redis hot, Cosmos warm, Blob cold), Pydantic schemas, and a service app factory.

## Installation

```bash
pip install -e .[dev]
```

## Architecture

```
holiday_peak_lib/
├── adapters/          # Pluggable retail system integrations
│   ├── base.py        # BaseAdapter abstract class
│   ├── crm_adapter.py
│   ├── crud_adapter.py
│   ├── external_api_adapter.py
│   ├── funnel_adapter.py
│   ├── inventory_adapter.py
│   ├── logistics_adapter.py
│   ├── mcp_adapter.py
│   ├── mock_adapters.py
│   ├── pricing_adapter.py
│   └── product_adapter.py
├── agents/            # Agent orchestration
│   ├── base_agent.py  # BaseRetailAgent with SLM/LLM routing
│   ├── builder.py     # AgentBuilder (memory, tools, model targets)
│   ├── fastapi_mcp.py # FastAPIMCPServer for agent-to-agent comms
│   ├── foundry.py     # Azure AI Foundry V2 integration
│   ├── service_agent.py
│   ├── provider_policy.py
│   ├── memory/        # Three-tier memory (hot/warm/cold)
│   └── orchestration/ # SAGA choreography helpers
├── app_factory.py     # build_service_app() — standard FastAPI wiring
├── config/
│   └── settings.py    # ServiceSettings, MemorySettings, PostgresSettings
├── schemas/           # Pydantic v2 domain models
│   ├── core.py, crm.py, funnel.py, inventory.py
│   ├── logistics.py, pricing.py, product.py
└── utils/
    ├── event_hub.py   # EventHubPublisher (async)
    ├── logging.py     # Structured logging + Application Insights
    └── retry.py       # Exponential backoff helpers
```

## Quick Start

```python
from holiday_peak_lib.agents import AgentBuilder, BaseRetailAgent
from holiday_peak_lib.agents.memory import hot, warm, cold
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer
from fastapi import FastAPI

class DemoAgent(BaseRetailAgent):
    async def handle(self, request):
        return {"echo": request}

app = FastAPI()
mcp = FastAPIMCPServer(app)
agent = (
    AgentBuilder()
    .with_agent(DemoAgent)
    .with_memory(
        hot.HotMemory("redis://localhost:6379"),
        warm.WarmMemory("https://cosmos", "db", "container"),
        cold.ColdMemory("https://storage", "container"),
    )
    .with_mcp(mcp)
    .build()
)
```

### Using the App Factory

```python
from holiday_peak_lib.app_factory import build_service_app

app = build_service_app(
    service_name="my-agent",
    slm_config=slm_config,
    llm_config=llm_config,
)
```

## Key Components

### Agents

| Class | Purpose |
|-------|---------|
| `BaseRetailAgent` | Abstract base with SLM-first routing; subclass and implement `handle()` |
| `AgentBuilder` | Fluent builder — compose agents with memory, tools, model targets |
| `FastAPIMCPServer` | Expose agent tools as MCP endpoints for agent-to-agent communication |
| `FoundryAgentConfig` | Azure AI Foundry V2 SDK integration (PromptAgentDefinition, auto-ensure) |

### Memory

| Tier | Class | Backend | Use Case |
|------|-------|---------|----------|
| Hot | `HotMemory` | Redis | Real-time context (< 1ms reads) |
| Warm | `WarmMemory` | Cosmos DB | Medium-term state (session, profile) |
| Cold | `ColdMemory` | Blob Storage | Long-term archival (audit, history) |

### Adapters

All adapters extend `BaseAdapter` and implement canonical interfaces for each retail domain:

- **CRM**: `CRMAdapter` — customer profiles, segments
- **CRUD**: `CRUDAdapter` — transactional operations
- **Funnel**: `FunnelAdapter` — conversion pipeline
- **Inventory**: `InventoryAdapter` — stock levels, reservations
- **Logistics**: `LogisticsAdapter` — shipping, carriers, ETAs
- **Pricing**: `PricingAdapter` — dynamic pricing, promotions
- **Product**: `ProductAdapter` — catalog, enrichment
- **MCP**: `MCPAdapter` — inter-agent protocol
- **ExternalAPI**: `ExternalAPIAdapter` — third-party integrations
- **Mock**: `MockAdapters` — local development and testing

### Schemas

Pydantic v2 models covering all retail domains: `core`, `crm`, `funnel`, `inventory`, `logistics`, `pricing`, `product`.

### Configuration

Environment-variable-driven via Pydantic Settings:

- `ServiceSettings` — service name, port, log level, monitoring
- `MemorySettings` — Redis URL, Cosmos URI/DB/container, Blob URL/container
- `PostgresSettings` — host, port, database, user, password, SSL, pool sizes

## Extension Points

- Implement custom adapters by subclassing `BaseAdapter`
- Register tools via `AgentBuilder.with_tool`
- Swap memory providers by implementing the `HotMemory`/`WarmMemory`/`ColdMemory` interface
- Override tier promotion rules in `MemoryBuilder`
- Subscribe to Event Hubs topics for SAGA participation

## Testing

```bash
cd lib
python -m pytest tests/ --cov=src --cov-report=term-missing
```

**Current**: 165 tests passing, 73% coverage (10 config test failures due to schema drift — tracked in [roadmap](../docs/roadmap/)).

## Related Documentation

- [Components](../docs/architecture/components.md) — Full component catalog
- [ADR-003](../docs/architecture/adrs/adr-003-adapter-pattern.md) — Adapter Pattern
- [ADR-004](../docs/architecture/adrs/adr-004-builder-pattern-memory.md) — Builder Pattern + Memory
- [ADR-005](../docs/architecture/adrs/adr-005-fastapi-mcp.md) — FastAPI + MCP
- [ADR-006](../docs/architecture/adrs/adr-006-agent-framework.md) — Agent Framework
- [ADR-008](../docs/architecture/adrs/adr-008-memory-tiers.md) — Memory Tiers
