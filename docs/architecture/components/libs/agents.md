# Agents Component

**Path**: `lib/src/holiday_peak_lib/agents/`  
**Pattern**: Builder Pattern (memory configuration)  
**Related ADRs**: [ADR-006](../../adrs/adr-006-agent-framework.md), [ADR-010](../../adrs/adr-010-rest-and-mcp-exposition.md)

## Purpose

Provides agent orchestration scaffolding using Microsoft Agent Framework with Foundry SDK. Handles tool calling, memory management, model selection, and MCP server exposition. Enables agents to coordinate retail workflows with multi-step reasoning.

## Design Pattern: Builder + Dependency Injection

**Builder Pattern**: Memory tier assembly (see [Memory component](memory.md))  
**Dependency Injection**: Tools and adapters injected at runtime

```python
from holiday_peak_lib.agents import AgentBuilder
from holiday_peak_lib.memory import MemoryBuilder

# Build agent with memory tiers
agent = (AgentBuilder()
    .with_memory(
        MemoryBuilder()
            .with_hot_tier(RedisConfig(...))
            .with_warm_tier(CosmosConfig(...))
            .build()
    )
    .with_tools([inventory_tool, pricing_tool])
    .with_model("gpt-4")
    .build())

# Run agent
response = await agent.run(query="Check inventory for SKU-123")
```

## What's Implemented

✅ **Agent Base Classes**:
- `BaseAgent`: Core orchestration logic
- `MCPAgent`: Wraps agent as MCP tool server
- `RESTAgent`: Exposes agent via FastAPI endpoints

✅ **Tool Registration**: Decorator pattern for registering Python functions as agent tools

✅ **Memory Integration**: Wired to three-tier memory (Redis/Cosmos/Blob)

✅ **Error Handling**: Graceful degradation when tools fail

## What's NOT Implemented (Stubbed/Placeholder)

❌ **Microsoft Agent Framework Integration**: No actual Foundry SDK calls; stub responses only  
❌ **Model Selection Logic**: No SLM vs LLM routing; hardcoded to single model  
❌ **Tool Result Evaluation**: No quality scoring or retry on poor results  
❌ **Streaming Support**: No incremental response streaming (MCP supports it)  
❌ **Session Management**: No multi-turn conversation context tracking  
❌ **Tool Orchestration**: No parallel tool calling or dependency resolution  

**Current Status**: Agent orchestration is **stubbed**. `BaseAgent.run()` returns mock responses. To wire real agents:
1. Install `agent-framework` package: `pip install agent-framework`
2. Configure Foundry endpoint and credentials
3. Replace stub `run()` with `AgentClient.run()`

## Microsoft Agent Framework Integration

### Current Implementation (Stub)

```python
# lib/src/holiday_peak_lib/agents/base_agent.py
class BaseAgent:
    async def run(self, query: str, tools: list[Tool]) -> AgentResponse:
        # STUB: Returns hardcoded response
        return AgentResponse(
            message="This is a stub response.",
            tool_calls=[],
            metadata={}
        )
```

### Production Implementation

```python
from azure.ai.agents import AgentClient
from azure.identity import DefaultAzureCredential

class FoundryAgent(BaseAgent):
    def __init__(self, endpoint: str):
        self.client = AgentClient(
            endpoint=endpoint,
            credential=DefaultAzureCredential()
        )
    
    async def run(self, query: str, tools: list[Tool]) -> AgentResponse:
        # Real Foundry call
        result = await self.client.run(
            agent_id="retail-assistant",
            query=query,
            tools=[t.to_foundry_tool() for t in tools],
            session_id=self.session_id
        )
        
        return AgentResponse(
            message=result.message,
            tool_calls=result.tool_calls,
            metadata={"model": result.model, "tokens": result.usage}
        )
```

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

## Model Selection (NOT IMPLEMENTED)

### Current State

All queries use same model (hardcoded `gpt-4`). No routing logic.

### Recommended Implementation

**SLM vs LLM Routing**:
- **SLM (e.g., GPT-4-nano)**: Simple queries (product search, price lookup) — <500ms latency, low cost
- **LLM (e.g., GPT-4)**: Complex reasoning (multi-step SAGA coordination, personalization) — 2-5s latency, higher cost

```python
class SmartAgent(BaseAgent):
    def __init__(self, slm_endpoint: str, llm_endpoint: str):
        self.slm = AgentClient(endpoint=slm_endpoint)
        self.llm = AgentClient(endpoint=llm_endpoint)
    
    async def run(self, query: str, tools: list[Tool]) -> AgentResponse:
        # Route based on query complexity
        complexity = self._assess_complexity(query)
        
        if complexity < 0.5:
            return await self.slm.run(query=query, tools=tools)
        else:
            return await self.llm.run(query=query, tools=tools)
    
    def _assess_complexity(self, query: str) -> float:
        # Heuristic: word count, tool dependencies
        words = len(query.split())
        return min(words / 50, 1.0)
```

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
