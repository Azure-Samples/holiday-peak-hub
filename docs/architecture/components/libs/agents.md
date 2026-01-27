# Agents Component

**Path**: `lib/src/holiday_peak_lib/agents/`  
**Pattern**: Builder Pattern (memory configuration)  
**Related ADRs**: [ADR-006](../../adrs/adr-006-agent-framework.md), [ADR-010](../../adrs/adr-010-rest-and-mcp-exposition.md)

## Purpose

Provides agent orchestration scaffolding using Microsoft Agent Framework with Foundry SDK. Handles tool calling, memory management, **model routing (SLM vs LLM)**, and MCP server exposition. Enables agents to coordinate retail workflows with multi-step reasoning.

## Design Pattern: Builder + Dependency Injection

**Builder Pattern**: Memory tier assembly (see [Memory component](memory.md))  
**Dependency Injection**: Tools and adapters injected at runtime

```python
import os
from typing import Any

from holiday_peak_lib.agents import AgentBuilder
from holiday_peak_lib.agents.base_agent import BaseRetailAgent, ModelTarget
from holiday_peak_lib.agents.memory import HotMemory, WarmMemory, ColdMemory
from holiday_peak_lib.agents.orchestration.router import RoutingStrategy


class RetailAgent(BaseRetailAgent):
    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        # Implement domain-specific workflow here
        return {"echo": request}


agent = (
    AgentBuilder()
    .with_agent(RetailAgent)
    .with_router(RoutingStrategy())
    .with_memory(
        HotMemory("redis://localhost:6379"),
        WarmMemory("https://cosmos-uri", "db", "container"),
        ColdMemory("https://blob-account.blob.core.windows.net", "container"),
    )
    .with_tool("check_inventory", inventory_tool)
    .with_models(
        slm=ModelTarget(name="slm", model="gpt-4o-mini", invoker=fast_invoker),
        llm=ModelTarget(name="llm", model="gpt-4o", invoker=rich_invoker),
        complexity_threshold=0.6,
    )
    .build()
)

# Run agent
response = await agent.handle({"query": "Check inventory for SKU-123"})
```

## What's Implemented

✅ **Agent Base Classes**:

- `BaseRetailAgent`: Adds SLM/LLM routing and SDK-agnostic model invocation
- `MCPAgent`: Wraps agent as MCP tool server
- `RESTAgent`: Exposes agent via FastAPI endpoints

✅ **Tool Registration**: Decorator pattern for registering Python functions as agent tools

✅ **Memory Integration**: Wired to three-tier memory (Redis/Cosmos/Blob)

✅ **Error Handling**: Graceful degradation when tools fail

## What's NOT Implemented (Stubbed/Placeholder)

❌ **Microsoft Agent Framework Integration**: No actual Foundry SDK calls; stub responses only  
✅ **Model Selection Logic**: SLM vs LLM routing via `BaseRetailAgent._select_model()`
❌ **Tool Result Evaluation**: No quality scoring or retry on poor results  
❌ **Streaming Support**: No incremental response streaming (MCP supports it)  
❌ **Session Management**: No multi-turn conversation context tracking  
❌ **Tool Orchestration**: No parallel tool calling or dependency resolution 

**Current Status**: Agent orchestration is **stubbed**. `BaseAgent.run()` returns mock responses. To wire real agents:

1. Install `agent-framework` package: `pip install agent-framework`
2. Configure Foundry endpoint and credentials
3. Replace stub `run()` with `AgentClient.run()`

## Microsoft Agent Framework (Azure AI Foundry) Integration

### Current Implementation

`BaseRetailAgent` now accepts two `ModelTarget`s (SLM and LLM) and routes based on a simple complexity heuristic (`_assess_complexity`). Each `ModelTarget` carries a model name and an async invoker, keeping the base class SDK-agnostic while allowing Microsoft Agent Framework integration.

### Production Integration Example (Microsoft Agent Framework)

```python
from typing import Any
```python
from typing import Any

from azure.ai.agents.aio import AgentsClient
from azure.identity.aio import DefaultAzureCredential
from holiday_peak_lib.agents import (
    AgentBuilder,
    BaseRetailAgent,
    FoundryAgentConfig,
    build_foundry_model_target,
)


class RetailAgent(BaseRetailAgent):
    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        # route to the configured Foundry Agent
        messages = [{"role": "user", "content": request["query"]}]
        return await self.invoke_model(request=request, messages=messages)


slm_cfg = FoundryAgentConfig(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    agent_id=os.environ["FOUNDRY_AGENT_ID_FAST"],
    deployment_name=os.environ.get("MODEL_DEPLOYMENT_NAME_FAST"),
    stream=False,  # set True to aggregate streaming deltas
)
llm_cfg = FoundryAgentConfig(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    agent_id=os.environ["FOUNDRY_AGENT_ID_RICH"],
    deployment_name=os.environ.get("MODEL_DEPLOYMENT_NAME_RICH"),
)

agent = (
    AgentBuilder()
    .with_agent(RetailAgent)
    .with_models(
        slm=build_foundry_model_target(slm_cfg),
        llm=build_foundry_model_target(llm_cfg),
        complexity_threshold=0.6,
    )
    .build()
)

response = await agent.handle({"query": "Find Nike shoes", "requires_multi_tool": False})
```

**Env vars expected**
- `PROJECT_ENDPOINT` (or `FOUNDRY_ENDPOINT`): Azure AI Foundry project endpoint
- `FOUNDRY_AGENT_ID_*`: Agent IDs created in Foundry (use different ones for SLM/LLM if desired)
- `MODEL_DEPLOYMENT_NAME_*` (optional): Deployment backing the Agent
- `FOUNDRY_STREAM` (optional): `true` to aggregate streaming deltas per target

**Streaming**: The Foundry SDK already streams deltas; `FoundryAgentConfig.stream=True` uses `runs.stream` and aggregates text so callers still receive a single payload. If you do not need deltas, leave it `False` and the SDK uses `runs.create_and_process`.

### Configuration

```python
# apps/ecommerce-catalog-search/src/config.py
FOUNDRY_ENDPOINT = os.getenv("FOUNDRY_ENDPOINT", "https://<project>.inference.ml.azure.com")
FOUNDRY_AGENT_ID = os.getenv("FOUNDRY_AGENT_ID", "retail-assistant")

agent = FoundryAgent(endpoint=FOUNDRY_ENDPOINT)
```

## MCP Server Exposition

### Pattern

Agents expose tools as MCP servers for agent-to-agent communication.

```python
from fastapi_mcp import MCPServer

app = FastAPI()
mcp = MCPServer(app)

# Register tool as MCP endpoint
@mcp.tool(
    name="check_inventory",
    description="Check product inventory levels",
    parameters={
        "sku": {"type": "string", "description": "Product SKU"}
    }
)
async def check_inventory(sku: str) -> dict:
    result = await inventory_adapter.fetch_stock(sku)
    return result.model_dump()
```

### MCP Schema Discovery

MCP clients can query available tools:
```bash
GET /mcp/tools
{
  "tools": [
    {
      "name": "check_inventory",
      "description": "Check product inventory levels",
      "parameters": { ... }
    }
  ]
}
```

### Model Selection

- **Heuristic**: `_assess_complexity` considers query length and a `requires_multi_tool` flag, returning 0–1.
- **Routing**: `_select_model` picks SLM when complexity < threshold and LLM otherwise (with sensible fallbacks).
- **Integration**: `invoke_model` forwards the selected model + parameters to the provided invoker (e.g., Microsoft Agent Framework client).

## Observability (PARTIALLY IMPLEMENTED)

### Logging

✅ **Implemented**: Basic query/response logging

❌ **NOT Implemented**:
- No token usage tracking
- No tool call latency per step
- No model performance metrics (P50/P95/P99)

**Add Structured Logging**:
```python
import logging
from holiday_peak_lib.utils.logging import get_logger

logger = get_logger(__name__)

async def run(self, query: str, tools: list[Tool]) -> AgentResponse:
    logger.info("agent.query", extra={
        "query": query,
        "tools": [t.name for t in tools],
        "session_id": self.session_id
    })
    
    start = time.time()
    result = await self.client.run(...)
    duration_ms = (time.time() - start) * 1000
    
    logger.info("agent.response", extra={
        "duration_ms": duration_ms,
        "tokens_used": result.usage.total_tokens,
        "model": result.model
    })
    
    return result
```

### Distributed Tracing (NOT IMPLEMENTED)

Add OpenTelemetry spans for end-to-end visibility:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

async def run(self, query: str, tools: list[Tool]) -> AgentResponse:
    with tracer.start_as_current_span("agent.run") as span:
        span.set_attribute("query", query)
        span.set_attribute("tool_count", len(tools))
        
        result = await self.client.run(...)
        
        span.set_attribute("tokens", result.usage.total_tokens)
        return result
```

## Evaluation Harness (NOT IMPLEMENTED)

### Missing Capabilities

❌ **Automated Quality Tests**: No scenario-based evaluation pipelines  
❌ **Latency Benchmarks**: No P95/P99 latency tracking per model  
❌ **Tool Call Accuracy**: No validation that tools return expected results  
❌ **Regression Tests**: No baseline comparisons when changing models  

### Recommended Implementation

```python
# lib/tests/agents/eval_harness.py
import pytest
from holiday_peak_lib.agents.eval import EvaluationHarness, Scenario

harness = EvaluationHarness(agent=agent)

@pytest.mark.asyncio
async def test_agent_latency():
    scenarios = [
        Scenario(query="Find Nike shoes", expected_tool="search_catalog"),
        Scenario(query="Check inventory for SKU-123", expected_tool="check_inventory")
    ]
    
    results = await harness.run(scenarios)
    
    # Assert latency < 3s
    for r in results:
        assert r.duration_ms < 3000
    
    # Assert tool accuracy > 90%
    accuracy = sum(1 for r in results if r.tool_called == r.expected_tool) / len(results)
    assert accuracy > 0.9
```

## Security Considerations

### Agent Prompt Injection (NOT ADDRESSED)

**Risk**: Malicious user queries manipulate agent to call unintended tools or leak data.

**Mitigations**:
- Input sanitization: Strip special characters, limit query length
- Tool access control: Restrict tools per user role
- Output filtering: Redact sensitive data (PII, credentials)

```python
def sanitize_query(query: str) -> str:
    # Remove potential injection patterns
    query = re.sub(r'[<>{}]', '', query)
    return query[:500]  # Max 500 chars

async def run(self, query: str, tools: list[Tool]) -> AgentResponse:
    safe_query = sanitize_query(query)
    # ... rest of agent logic
```

### Tool Authorization (NOT IMPLEMENTED)

Each tool should check user permissions:
```python
@mcp.tool()
async def delete_order(order_id: str, user_id: str) -> dict:
    # Check if user owns order
    order = await db.get_order(order_id)
    if order.user_id != user_id:
        raise PermissionError("Not authorized")
    
    await db.delete_order(order_id)
    return {"deleted": True}
```

## Performance Tuning

### Parallel Tool Calling (NOT IMPLEMENTED)

When agent needs multiple independent tools, call in parallel:
```python
async def run_tools_parallel(self, tool_calls: list[ToolCall]) -> list[ToolResult]:
    tasks = [self._call_tool(tc) for tc in tool_calls]
    return await asyncio.gather(*tasks)
```

### Caching (NOT IMPLEMENTED)

Cache tool results in hot memory (Redis):
```python
async def call_tool(self, tool_name: str, args: dict) -> ToolResult:
    cache_key = f"tool:{tool_name}:{hash(str(args))}"
    
    # Check cache
    cached = await self.memory.hot.get(cache_key)
    if cached:
        return ToolResult.from_dict(cached)
    
    # Call tool
    result = await self.tools[tool_name](**args)
    
    # Cache for 5 minutes
    await self.memory.hot.set(cache_key, result.to_dict(), ttl=300)
    return result
```

## Testing

### Unit Tests

✅ **Implemented**: Basic tests in `lib/tests/agents/`

```python
@pytest.mark.asyncio
async def test_agent_run_stub():
    agent = BaseAgent()
    response = await agent.run(query="test", tools=[])
    assert response.message
```

### Integration Tests (NOT IMPLEMENTED)

Test with real Foundry endpoint:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_foundry_call():
    agent = FoundryAgent(endpoint=os.getenv("FOUNDRY_ENDPOINT"))
    response = await agent.run(
        query="Find Nike shoes",
        tools=[search_catalog_tool]
    )
    assert "Nike" in response.message
```

## Runbooks (NOT PROVIDED)

**Operational playbooks needed**:
- **Agent Latency Spikes**: Diagnose slow model inference, tool timeouts
- **Tool Call Failures**: Fallback strategies when adapters error
- **Model Degradation**: Switch to backup model when primary is unavailable

## Related Components

- [Memory](memory.md) — Three-tier memory for agent state
- [Adapters](adapters.md) — Tools call adapters for external data
- [Orchestration](orchestration.md) — SAGA coordination across agents

## Related ADRs

- [ADR-006: Agent Framework](../../adrs/adr-006-agent-framework.md)
- [ADR-010: REST + MCP Exposition](../../adrs/adr-010-rest-and-mcp-exposition.md)
- [ADR-004: Builder Pattern](../../adrs/adr-004-builder-pattern-memory.md)
