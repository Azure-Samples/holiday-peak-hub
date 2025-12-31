# ADR-005: FastAPI + MCP for API Exposition

**Status**: Accepted  
**Date**: 2024-12  
**Deciders**: Architecture Team, Ricardo Cataldi

## Context

Apps must expose two types of APIs:
1. **REST endpoints**: For traditional clients (web/mobile apps, other services)
2. **MCP servers**: For agent-to-agent tool calling and Foundry integration

Requirements:
- High throughput (10k+ req/s per service)
- Async I/O for parallel adapter calls
- OpenAPI docs auto-generation
- Native Python SDK support

## Decision

**Use FastAPI for REST and fastapi-mcp for MCP server exposition.**

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

## Consequences

### Positive
- **Performance**: FastAPI is one of fastest Python frameworks (on par with Node.js)
- **Async Native**: Built on Starlette (async ASGI)
- **Type Safety**: Pydantic models enforce request/response contracts
- **Auto Docs**: OpenAPI/Swagger generated automatically
- **MCP Support**: fastapi-mcp provides zero-overhead MCP wrapping

### Negative
- **Framework Lock-in**: Replacing FastAPI requires rewriting routes
- **Learning Curve**: Teams unfamiliar with async/await need training
- **Middleware Complexity**: Custom middleware for auth/logging requires care

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
- [ADR-010: REST + MCP Exposition](adr-010-rest-and-mcp-exposition.md) — Dual API strategy
