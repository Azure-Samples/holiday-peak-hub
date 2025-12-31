# ADR-006: Microsoft Agent Framework + Foundry

**Status**: Accepted  
**Date**: 2024-12

## Context

Need standardized agent orchestration with support for:
- Multi-step reasoning
- Tool calling
- Memory management
- Model selection (SLM vs LLM)

## Decision

**Use Microsoft Agent Framework with Foundry SDK** for all agent logic.

### Rationale
- **Standards Compliance**: Aligned with Microsoft AI strategy
- **Foundry Integration**: Native support for deployed models
- **Tool Calling**: Built-in function calling support
- **Memory**: Session state management included
- **Python First**: Native SDK, no FFI overhead

## Implementation

```python
from azure.ai.agents import AgentClient
from holiday_peak_lib.memory import AgentMemory

agent = AgentClient(endpoint=..., credential=...)
tools = [inventory_tool, pricing_tool]
response = await agent.run(
    query="Check inventory for SKU-123",
    tools=tools,
    memory=memory
)
```

## Consequences

**Positive**: Foundry ecosystem, Microsoft support, automatic updates  
**Negative**: Vendor lock-in, less flexibility than custom agents

## Related ADRs
- [ADR-010: REST + MCP](adr-010-rest-and-mcp-exposition.md)
