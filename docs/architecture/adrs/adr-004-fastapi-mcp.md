# ADR-004: FastAPI with Dual REST + MCP Exposition

**Status**: Accepted (Revised 2026-04-28 — consolidated dual REST + MCP exposition decision)  
**Date**: 2024-12  
**Deciders**: Architecture Team, Ricardo Cataldi  
**Supersedes**: prior separate decision on Dual Exposition (REST + MCP Servers), now absorbed into this ADR

## Context

Apps must expose two types of APIs:
1. **REST endpoints**: For traditional clients (web/mobile apps, other services)
2. **MCP servers**: For agent-to-agent tool calling and Foundry integration

Apps must also support two client types:
1. **Traditional Clients**: Web/mobile apps, external services (require REST)
2. **Agent Clients**: Foundry agents, internal agent-to-agent calls (benefit from MCP)

Requirements:
- High throughput (10k+ req/s per service)
- Async I/O for parallel adapter calls
- OpenAPI docs auto-generation
- Native Python SDK support
- Both REST and MCP from every agent app

## Decision

**Use FastAPI for REST and fastapi-mcp for MCP server exposition. Expose both REST endpoints and MCP tool servers from every agent app.**

## Implementation Status (2026-03-18)

- **Implemented**: FastAPI is the service framework in active apps, and agent services register MCP tools via `FastAPIMCPServer` in `holiday_peak_lib`.
- **Partially diverged**: The original wording implies uniform dual exposition; in practice, MCP is concentrated in agent services while some services (for example, CRUD) remain REST-only.
- **No supersession**: This ADR remains active for service exposition mechanics; ingress and edge policy changes are tracked separately in [ADR-021](adr-021-apim-agc-edge.md).

### Dual Exposition Rationale
- **REST for Humans**: Human-readable JSON, browser DevTools, Postman testing
- **MCP for Agents**: Automatic tool discovery, streaming support, Foundry native
- **No Duplication**: FastAPI-MCP wraps same business logic for both

### When to Use Which Protocol

| Client Type | Protocol | Use Case |
|-------------|----------|----------|
| Web UI | REST | Product detail page |
| Mobile App | REST | Cart updates |
| Agent (Foundry) | MCP | Multi-step reasoning |
| Agent-to-Agent | MCP | Inter-service tool calls |
| External Partner | REST | API integration |

### Structure
```python
from fastapi import FastAPI
from fastapi_mcp import MCPServer

app = FastAPI()

# REST endpoint
@app.get("/inventory/{sku}")
async def get_inventory(sku: str):
    return await inventory_adapter.fetch(sku)

# MCP server
mcp = MCPServer(app)

@mcp.tool()
async def check_inventory(sku: str) -> dict:
    return await inventory_adapter.fetch(sku)
```

### Dual Exposition Pattern (Single Logic, Two Surfaces)

```python
# Core logic
async def check_inventory(sku: str) -> InventoryStatus:
    return await inventory_adapter.fetch(sku)

# REST endpoint
@app.get("/inventory/{sku}")
async def rest_check_inventory(sku: str):
    return await check_inventory(sku)

# MCP tool
@mcp.tool()
async def mcp_check_inventory(sku: str) -> dict:
    result = await check_inventory(sku)
    return result.model_dump()
```

## Consequences

### Positive
- **Performance**: FastAPI is one of fastest Python frameworks (on par with Node.js)
- **Async Native**: Built on Starlette (async ASGI)
- **Type Safety**: Pydantic models enforce request/response contracts
- **Auto Docs**: OpenAPI/Swagger generated automatically
- **MCP Support**: fastapi-mcp provides zero-overhead MCP wrapping
- **Flexibility**: Support both traditional and agentic workflows
- **Future-proof**: MCP adoption without breaking REST clients
- **Testing**: REST clients easier to test manually

### Negative
- **Framework Lock-in**: Replacing FastAPI requires rewriting routes
- **Learning Curve**: Teams unfamiliar with async/await need training
- **Middleware Complexity**: Custom middleware for auth/logging requires care
- **Dual maintenance**: Keep REST and MCP schemas in sync
- **Confusion**: Teams must choose right protocol
- **Docs**: Maintain OpenAPI + MCP schema

## Alternatives Considered

### Flask
- **Pros**: Mature, large ecosystem
- **Cons**: Sync-only (requires gevent for async); slower than FastAPI

### Django + Ninja
- **Pros**: Batteries-included (ORM, admin)
- **Cons**: Heavier than needed; async support incomplete

### Sanic
- **Pros**: Async-first, fast
- **Cons**: Smaller ecosystem; no MCP integration

### gRPC
- **Pros**: Efficient binary protocol
- **Cons**: No MCP support; requires .proto schemas; limited browser support

## MCP Server Details

### Why MCP?
- **Agent Interop**: Foundry agents can call MCP tools natively
- **Tool Discovery**: MCP schema enables dynamic tool registration
- **Backward Compat**: REST clients unaffected by MCP layer

### MCP Tool Registration
Tools registered via decorator:
```python
@mcp.tool(
    name="check_inventory",
    description="Check product inventory levels",
    parameters={
        "sku": {"type": "string", "description": "Product SKU"}
    }
)
async def check_inventory(sku: str) -> dict:
    ...
```

### MCP vs REST Trade-offs
| Feature | REST | MCP |
|---------|------|-----|
| Human-readable | ✅ JSON | ✅ JSON |
| Browser support | ✅ Yes | ❌ Agent clients only |
| Tool discovery | ❌ Manual | ✅ Automatic |
| Streaming | ⚠️ SSE | ✅ Native |

## Implementation Guidelines

### Project Structure
```
apps/<service>/src/
├── main.py          # FastAPI app + MCP server
├── routers/         # REST route modules
│   ├── inventory.py
│   └── health.py
├── tools/           # MCP tool modules
│   ├── inventory.py
│   └── search.py
└── config.py        # App settings
```

### Startup Sequence
1. Load config from environment
2. Initialize adapters (inventory, pricing, etc.)
3. Build memory tiers (Redis, Cosmos, Blob)
4. Register REST routes
5. Register MCP tools
6. Start uvicorn server

### Error Handling
- REST: Return HTTP status codes (400, 404, 500)
- MCP: Raise `MCPError` with error code + message

### Testing
- REST: `httpx.AsyncClient` for integration tests
- MCP: `mcp_client` library for tool invocation tests

## Related ADRs

- [ADR-001: Python 3.13](adr-001-python-3.13.md) — Async language support
- [ADR-005: Agent Framework](adr-005-agent-framework.md) — Agent consumption of dual APIs

## Migration Notes

This ADR consolidates the former Dual Exposition (REST + MCP Servers) decision.
- Sections "Dual Exposition Rationale", "When to Use Which Protocol", and "Dual Exposition Pattern" were absorbed from that decision.
- The prior dual-exposition ADR is now superseded and redirects here.
