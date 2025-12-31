# ADR-010: Dual Exposition: REST + MCP Servers

**Status**: Accepted  
**Date**: 2024-12

## Context

Apps must support two client types:
1. **Traditional Clients**: Web/mobile apps, external services (require REST)
2. **Agent Clients**: Foundry agents, internal agent-to-agent calls (benefit from MCP)

## Decision

**Expose both REST endpoints and MCP tool servers from every app.**

### Rationale
- **REST for Humans**: Human-readable JSON, browser DevTools, Postman testing
- **MCP for Agents**: Automatic tool discovery, streaming support, Foundry native
- **No Duplication**: FastAPI-MCP wraps same business logic for both

## Implementation

Single business logic, dual exposure:
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

### When to Use Which?
| Client Type | Protocol | Use Case |
|-------------|----------|----------|
| Web UI | REST | Product detail page |
| Mobile App | REST | Cart updates |
| Agent (Foundry) | MCP | Multi-step reasoning |
| Agent-to-Agent | MCP | Inter-service tool calls |
| External Partner | REST | API integration |

## Consequences

**Positive**: 
- Flexibility: Support both traditional and agentic workflows
- Future-proof: MCP adoption without breaking REST clients
- Testing: REST clients easier to test manually

**Negative**: 
- Dual maintenance: Keep REST and MCP schemas in sync
- Confusion: Teams must choose right protocol
- Docs: Maintain OpenAPI + MCP schema

## Related ADRs
- [ADR-005: FastAPI + MCP](adr-005-fastapi-mcp.md)
- [ADR-006: Agent Framework](adr-006-agent-framework.md)
