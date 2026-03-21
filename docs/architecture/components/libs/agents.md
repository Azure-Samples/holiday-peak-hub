# Agents Component

**Path**: `lib/src/holiday_peak_lib/agents/`  
**Pattern**: Builder Pattern (memory configuration)  
**Related ADRs**: [ADR-006](../../adrs/adr-006-agent-framework.md), [ADR-010](../../adrs/adr-010-rest-and-mcp-exposition.md)

## Purpose

Provides agent orchestration scaffolding using Microsoft Agent Framework with Foundry SDK. Handles tool calling, memory management, **model routing (SLM vs LLM)**, and MCP server exposition. Enables agents to coordinate retail workflows with multi-step reasoning.

## Design Pattern: Builder + Dependency Injection

**Builder Pattern**: Agent assembly with memory tiers + models  
**Dependency Injection**: Tools, adapters, and MCP hooks injected at runtime

## Provider Strategy Pattern

`BaseRetailAgent` now delegates provider-specific prompt/routing behavior through
a Strategy abstraction in [lib/src/holiday_peak_lib/agents/provider_policy.py](../../../../lib/src/holiday_peak_lib/agents/provider_policy.py):

- `ProviderPolicyStrategy` (interface)
- `DefaultProviderPolicyStrategy`
- `FoundryProviderPolicyStrategy`
- `resolve_provider_policy(provider)` registry/factory

This keeps base orchestration provider-agnostic while allowing Foundry-specific
governance (portal/SDK-owned instructions) and future provider extensions.

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
        slm=ModelTarget(name="slm", model="gpt-5-nano", invoker=fast_invoker),
        llm=ModelTarget(name="llm", model="gpt-5", invoker=rich_invoker),
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

✅ **Agent Builder**:

- `AgentBuilder`: Wires agent class, router, memory tiers, tools, MCP server, and models

✅ **Foundry Integration Helpers**:

- `FoundryAgentConfig` + `build_foundry_model_target` (Azure AI Foundry Agents via `AIProjectClient`)
- Foundry prompt governance in `BaseRetailAgent` (system/developer prompts are stripped in Foundry mode)
- Agents V2 provisioning path (`project_client.agents.create_version` with `PromptAgentDefinition`)
- Agents V2 execution path (`openai_client.conversations` + `openai_client.responses` + `agent_reference`)
- **42 V2 agents provisioned** in Foundry project `aipholidaris` (21 services × 2 roles: fast + rich)
- SDK requirement: `azure-ai-projects>=2.0.0b4` for V2 `create_version` support

✅ **MCP Server Exposure**:

- `FastAPIMCPServer` with `add_tool()` and `mount()`

✅ **Memory Integration**: Wired to three-tier memory (Redis/Cosmos/Blob)

## What's NOT Implemented (Stubbed/Placeholder)

❌ **Automatic Tool Orchestration**: No built-in parallel tool calling or dependency resolution  
❌ **Tool Result Evaluation**: No quality scoring or retry on poor results  
❌ **Session Management**: No multi-turn conversation context tracking  
❌ **MCP Schema Discovery**: No `/mcp/tools` registry endpoint  

**Foundry note**: When running agents on **Foundry Agent Service**, several items above are handled by the platform:
- **Tool orchestration + retries** (server-side tool execution with logging)
- **Conversation/session state** (managed conversations with optional BYO storage)
- **Observability** (conversation traces, tool invocations, and Application Insights integration)
- **Safety controls** (integrated content filters and policy governance)

**Current Status**: Core orchestration and Foundry invokers are implemented, but apps must provide agent classes, tools, and model config.

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
- `PROJECT_NAME` (or `FOUNDRY_PROJECT_NAME`): Azure AI Foundry project name (optional)
- `FOUNDRY_AGENT_ID_FAST` / `FOUNDRY_AGENT_ID_RICH`: Agent IDs created in Foundry
- `FOUNDRY_AGENT_NAME_FAST` / `FOUNDRY_AGENT_NAME_RICH`: Agent names (used for V2 lookup/creation)
- `MODEL_DEPLOYMENT_NAME_FAST` / `MODEL_DEPLOYMENT_NAME_RICH` (optional): Deployment backing the Agent (defaults to `gpt-5-nano` / `gpt-5`)
- `FOUNDRY_STREAM` (optional): `true` to aggregate streaming deltas per target
- `FOUNDRY_STRICT_ENFORCEMENT` (optional): `true` to require successful ensure before serving `/invoke`
- `FOUNDRY_AUTO_ENSURE_ON_STARTUP` (optional): `true` to auto-ensure agents on app startup

**SDK Requirement**: `azure-ai-projects>=2.0.0b4` is required for V2 agent provisioning (`create_version` + `PromptAgentDefinition`).

**V2 Execution**: Agents V2 uses `openai_client.conversations.create()` + `openai_client.responses.create()` with `agent_reference` instead of the legacy threads/runs API. Streaming is not yet supported in V2; the invoker returns a single payload.

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
from holiday_peak_lib.agents.fastapi_mcp import FastAPIMCPServer

app = FastAPI()
mcp = FastAPIMCPServer(app)

# Register tool as MCP endpoint
async def check_inventory(payload: dict) -> dict:
    result = await inventory_adapter.fetch_stock(payload["sku"])
    return result.model_dump()

mcp.add_tool("/inventory/check", check_inventory)
```

### MCP Schema Discovery

`FastAPIMCPServer` now supports per-tool schema metadata registration at add time:

- Optional `input_model` / `output_model` validation (Pydantic)
- Optional versioned schema references (`name`, `version`, optional `uri`)
- Metadata captured in `FastAPIMCPServer.tool_metadata`

Backward compatibility:

- Existing `mcp.add_tool("/path", handler)` usage remains valid.
- Tools without schema models continue to accept/return dict payloads unchanged.
- Teams can incrementally add schema refs and validation without breaking existing MCP paths.

### Model Selection

- **Heuristic**: `_assess_complexity` considers query length and a `requires_multi_tool` flag, returning 0–1.
- **Routing**: `_select_model` picks SLM when complexity < threshold and LLM otherwise (with sensible fallbacks).
- **Integration**: `invoke_model` forwards the selected model + parameters to the provided invoker (e.g., Microsoft Agent Framework client).

### Prompt Governance (Foundry)

When `ModelTarget.provider == "foundry"` (set by `build_foundry_model_target`) and
`AgentDependencies.enforce_foundry_prompt_governance=True` (default),
`BaseRetailAgent` enforces portal/SDK-owned prompt instructions by:

- Removing local `system`/`developer` role messages before model invocation.
- Keeping only conversational roles (`user`, `assistant`) as runtime input.
- Running SLM-first and escalating to LLM by complexity threshold without injecting
    additional local instruction prompts.

This guarantees instruction changes are managed in Azure AI Foundry (portal or SDK),
not by editing service-local prompt strings in `apps/*/agents.py`.

### Foundry Agent Provisioning Endpoint (Per Service)

All services created with `build_service_app` now expose:

- `POST /foundry/agents/ensure`

This endpoint validates that configured Foundry agents exist and can create them
once when missing (via Foundry SDK). Typical request:

```json
{
    "role": "both",
    "create_if_missing": true,
    "names": {"fast": "catalog-fast", "rich": "catalog-rich"},
    "instructions": {"fast": "...", "rich": "..."},
    "models": {"fast": "gpt-5-nano", "rich": "gpt-5"}
}
```

Supported roles:

- `fast` (SLM)
- `rich` (LLM)
- `both`

The service updates in-memory model targets with resolved/created Foundry agent IDs.

Default deployment models in this repo are:

- SLM (`fast`): `gpt-5-nano`
- LLM (`rich`): `gpt-5`

Use **GlobalStandard** (global deployment) SKU in Azure AI Foundry to maximize
regional compatibility and avoid runtime dependency errors.

When `create_if_missing=true`, agent creation requires a model to be provided via
`models.<role>` or configured through `MODEL_DEPLOYMENT_NAME_FAST` /
`MODEL_DEPLOYMENT_NAME_RICH`. If no model is available, the role result returns
`status: "missing_model"` and no agent is created.

### Strict Foundry Enforcement Mode

Set `FOUNDRY_STRICT_ENFORCEMENT=true` to require a successful ensure step before
serving `/invoke` requests:

- Before ensure: `/invoke` returns `503`
- After successful `POST /foundry/agents/ensure`: `/invoke` is enabled

This mode is designed for environments where all agent prompts/instructions must be
managed exclusively in Foundry.

When strict mode is enabled, startup auto-ensure is also enabled by default to
guarantee agent versions exist before serving traffic.

## Observability (PARTIALLY IMPLEMENTED)

### Logging

✅ **Implemented**: Basic operation logging via `configure_logging` + `log_async_operation`

✅ **Foundry-managed** (when using Foundry Agent Service):
- Conversation and tool-call traces
- Structured run logs in the Foundry portal
- Application Insights metrics integration

❌ **NOT Implemented**:
- No token usage tracking
- No tool call latency per step
- No model performance metrics (P50/P95/P99)

**Add Structured Logging**:
```python
from holiday_peak_lib.utils.logging import configure_logging, log_async_operation

logger = configure_logging(app_name="catalog-search")

async def run(self, payload: dict) -> dict:
    return await log_async_operation(
        logger,
        name="agent.run",
        intent=payload.get("query"),
        func=lambda: self.invoke_model(request=payload, messages=[payload.get("query", "")]),
        metadata={"tools": list(self.tools.keys())},
    )
```

### Distributed Tracing (PARTIALLY IMPLEMENTED)

✅ **Implemented in shared runtime**:
- `FoundryTracer` now initializes Azure Monitor + Foundry/OpenTelemetry instrumentors when available.
- `/invoke` wraps agent execution in explicit `agent.handle` spans with service/intent metadata.
- Decision, model invocation, and tool-call events are exposed through `/agent/traces` and `/agent/metrics`.

❌ **Still pending**:
- End-to-end correlation IDs across every external downstream dependency.

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

## Evaluation Harness (PARTIALLY IMPLEMENTED)

✅ **Implemented in flow runtime**:
- Deterministic enrichment and search evaluators are available in `holiday_peak_lib.evaluation`.
- `run_evaluation()` integrates with `azure-ai-evaluation` when installed and degrades gracefully to local fallback.
- Enrichment/search flows now persist latest run output to tracer state surfaced by `GET /agent/evaluation/latest`.

### Missing Capabilities

❌ **Automated Quality Tests**: No scenario-based scheduled evaluation pipelines  
❌ **Latency Benchmarks**: No P95/P99 latency tracking per model  
❌ **Tool Call Accuracy**: No validation that tools return expected results  
❌ **Regression Tests**: No baseline comparisons when changing models  

✅ **Foundry-managed (interactive)**: Foundry Agents playground supports built-in evaluation metrics on threads/runs. This repo does not yet automate those evaluations.

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

✅ **Foundry-managed** (when using Foundry Agent Service): integrated content filters and policy enforcement reduce prompt-injection risk and unsafe outputs.

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
