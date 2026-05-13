# Agents Component

**Path**: `lib/src/holiday_peak_lib/agents/`  
**Pattern**: Builder Pattern (memory configuration)  
**Related ADRs**: [ADR-005](../../adrs/adr-005-agent-framework.md), [ADR-004](../../adrs/adr-004-fastapi-mcp.md)

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

## Self-Healing Kernel

Services built through `build_service_app` now include a shared self-healing kernel from
`holiday_peak_lib.self_healing`.

- Incident lifecycle: detect -> classify -> remediate -> verify -> escalate/closed
- Surface contract coverage: API/APIM, AKS ingress, MCP, and messaging
- Policy guardrails:
    - Recoverable class is limited to infrastructure misconfiguration (`4xx` and selected `5xx`)
    - Remediation is allowlisted and audit-recorded
    - Image restore/redeploy actions are explicitly forbidden
- Messaging producer hardening:
    - Producer failures now emit a shared failure envelope with category (`configuration`, `payload_validation`, `authentication`, `authorization`, `throttled`, `transient`, `unknown`) and topic/profile metadata
    - Messaging remediation now distinguishes publisher binding resets from consumer binding resets
    - Publish incidents can carry rollback/compensation outcome metadata so failed compensation escalates instead of being auto-remediated silently
- Operational visibility routes:
    - `GET /self-healing/status`
    - `GET /self-healing/incidents`
    - `POST /self-healing/reconcile`

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

✅ **Direct-Model Invocation (canonical, post 2026-05-10)**:

- `DirectModelInvoker` + `build_direct_model_target`: runs `agent_framework.Agent` in-process over a pluggable `ChatClient` (`agent_framework_foundry.FoundryChatClient` by default).
- `AgentBuilder.with_direct_models(*, instructions, slm_config, llm_config, complexity_threshold, chat_client_factory)`: sibling of `with_foundry_models`. Forwards registered tools as runtime callables.
- `app_factory.build_service_app(..., use_direct_model=True)` / `create_standard_app(..., use_direct_model=True)`: per-service opt-in. Falls back to `HOLIDAY_PEAK_DIRECT_MODEL=true` env var. All 26 agent services run on this path as of 2026-05-10 (#990, Wave 3).
- Provider-agnostic via `ChatClientFactory = Callable[[FoundryAgentConfig], Any]` — swap providers without touching invoker logic.
- Native MAF function-calling — dict-schema tool definitions raise `TypeError` (no JSON-text tool-call parser fallback).
- `default_options={"store": False}` — no portal-managed agent record at runtime; MAF `Agent` is stateless per request.
- SDK requirement: `agent-framework>=1.2.0` + `agent-framework-foundry>=1.0.1`.

✅ **Foundry Configuration Helpers (direct-model runtime)**:

- `FoundryAgentConfig` (kept — consumed by `DirectModelInvoker`).
- Endpoint normalization helpers support both project-scoped Foundry endpoints and account endpoints paired with `PROJECT_NAME` / `FOUNDRY_PROJECT_NAME`.
- Portal-agent runtime/provisioning code (`FoundryAgentInvoker`, `build_foundry_model_target`, `/foundry/agents/ensure`, V2 `PromptAgentDefinition`) was removed in Wave 4c.
- The 42 V2 portal agents in Foundry project `aipholidaris` were intentionally not touched by code; manual deprovisioning remains outside this repository change.

✅ **Memory Tools and Parallel I/O**:

- `get_memory`, `set_memory`, `search_memory` tools exposed for agent use
- `asyncio.gather`-based concurrent hot/warm/cold tier operations
- `gather_adapters` helper for concurrent adapter initialization

✅ **Guardrails**:

- `enrichment_guardrail.py`: validation layer for enrichment outputs

✅ **MCP Server Exposure**:

- `FastAPIMCPServer` with `add_tool()` and `mount()`

✅ **Memory Integration**: Wired to three-tier memory (Redis/Cosmos/Blob)

## What's NOT Implemented (Stubbed/Placeholder)

❌ **Automatic Tool Orchestration**: No built-in parallel tool calling or dependency resolution  
❌ **Tool Result Evaluation**: No quality scoring or retry on poor results  
❌ **Session Management**: No multi-turn conversation context tracking  
❌ **MCP Schema Discovery**: No `/mcp/tools` registry endpoint  

**Direct-model note**: The active runtime executes MAF agents in-process. Tool orchestration, retries, session state, and guardrails are therefore owned by framework code, service adapters, and deployment configuration rather than by portal-managed Foundry Agent records.

**Current Status**: Core orchestration, direct-model invocation, MCP exposition, memory, and telemetry helpers are implemented, but apps must provide agent classes, tools, and model config.

## Microsoft Agent Framework (Azure AI Foundry) Integration

### Current Implementation

`BaseRetailAgent` now accepts two `ModelTarget`s (SLM and LLM) and routes based on a simple complexity heuristic (`_assess_complexity`). Each `ModelTarget` carries a model name and an async invoker, keeping the base class SDK-agnostic while allowing Microsoft Agent Framework integration.

### Production Integration Example (Microsoft Agent Framework Direct Model)

```python
from typing import Any

from holiday_peak_lib.agents import (
    AgentBuilder,
    BaseRetailAgent,
    FoundryAgentConfig,
    build_direct_model_target,
)


class RetailAgent(BaseRetailAgent):
    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        # route to the configured direct model target
        messages = [{"role": "user", "content": request["query"]}]
        return await self.invoke_model(request=request, messages=messages)


slm_cfg = FoundryAgentConfig(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    deployment_name=os.environ["MODEL_DEPLOYMENT_NAME_FAST"],
    stream=False,  # set True to aggregate streaming deltas
)
llm_cfg = FoundryAgentConfig(
    endpoint=os.environ["PROJECT_ENDPOINT"],
    deployment_name=os.environ["MODEL_DEPLOYMENT_NAME_RICH"],
)

agent = (
    AgentBuilder()
    .with_agent(RetailAgent)
    .with_models(
        slm=build_direct_model_target(slm_cfg),
        llm=build_direct_model_target(llm_cfg),
        complexity_threshold=0.6,
    )
    .build()
)

response = await agent.handle({"query": "Find Nike shoes", "requires_multi_tool": False})
```

**Env vars expected**
- `PROJECT_ENDPOINT` (or `FOUNDRY_ENDPOINT`): Azure AI Foundry project endpoint of the form `https://<resource>.services.ai.azure.com/api/projects/<project-name>`. The runtime also accepts an Azure AI Services account endpoint and derives the project-scoped endpoint when `PROJECT_NAME` is set.
- `PROJECT_NAME` (or `FOUNDRY_PROJECT_NAME`): Azure AI Foundry project name. Required when the endpoint is not already project-scoped.
- `MODEL_DEPLOYMENT_NAME_FAST` / `MODEL_DEPLOYMENT_NAME_RICH`: Deployments backing the SLM/LLM direct-model targets.
- `FOUNDRY_STRICT_ENFORCEMENT` (optional): `true` to require bound direct-model targets before serving `/invoke`

**SDK Requirement**: `agent-framework>=1.2.0` and `agent-framework-foundry>=1.0.1`. `azure-ai-projects` V2 provisioning APIs are no longer used by the framework runtime.

### Direct-Model Production Example (canonical, post 2026-05-10)

```python
import os
from typing import Any

from holiday_peak_lib.app_factory import create_standard_app
from holiday_peak_lib.agents.base_agent import BaseRetailAgent


class CatalogSearchAgent(BaseRetailAgent):
    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        messages = [{"role": "user", "content": request["query"]}]
        return await self.invoke_model(request=request, messages=messages)


app = create_standard_app(
    require_foundry_readiness=True,
    disable_tracing_without_foundry=True,
    service_name="ecommerce-catalog-search",
    agent_class=CatalogSearchAgent,
    use_direct_model=True,  # opt into MAF direct-model invocation
)
```

When `use_direct_model=True` (or `HOLIDAY_PEAK_DIRECT_MODEL=true`), `app_factory`:

1. Loads service instructions from `prompts/instructions.md` (or the default fallback template).
2. Constructs `FoundryAgentConfig` for `fast` and `rich` roles from env (model deployment names are required; no portal-managed agent ID is required).
3. Calls `AgentBuilder.with_direct_models(instructions=..., slm_config=..., llm_config=...)`.
4. `DirectModelInvoker` wraps the model in an in-process `agent_framework.Agent` over the configured `ChatClient` (`FoundryChatClient` by default).

**Env vars (direct-model path)**
- `PROJECT_ENDPOINT` (or `FOUNDRY_ENDPOINT`): Azure AI Foundry project endpoint.
- `PROJECT_NAME` (or `FOUNDRY_PROJECT_NAME`): Project name (required if endpoint is not project-scoped).
- `MODEL_DEPLOYMENT_NAME_FAST` / `MODEL_DEPLOYMENT_NAME_RICH`: Deployments backing the SLM/LLM targets. These values are required for bound `maf-direct` targets and fail-fast readiness.
- `HOLIDAY_PEAK_DIRECT_MODEL` (optional): `true` to opt into the direct-model path without per-service code changes.

**Provider portability**: pass a custom `chat_client_factory: Callable[[FoundryAgentConfig], ChatClient]` to `with_direct_models()` (or to `app_factory.build_service_app`) to use any MAF-compatible `ChatClient` (Azure OpenAI direct, OpenAI, custom HTTP). `FoundryAgentConfig.deployment_name` becomes the model parameter, and the normalized endpoint is available for provider auth/identity.

**What the direct-model path does NOT use**:
- Portal-managed Foundry Agent records (`FOUNDRY_AGENT_ID_*`).
- `/foundry/agents/ensure` provisioning endpoint.
- `ensure-foundry-agents.{sh,ps1}` CI hooks.
- The JSON-text tool-call parser (`_extract_tool_calls_from_text`).

These were removed from framework runtime code in Wave 4c. Historical design notes may still mention them for audit context.

### Configuration

Agent services configure Foundry-backed direct model deployments through environment variables consumed by `app_factory`:

- `PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`
- `PROJECT_NAME` or `FOUNDRY_PROJECT_NAME` when the endpoint is not project-scoped
- `MODEL_DEPLOYMENT_NAME_FAST`
- `MODEL_DEPLOYMENT_NAME_RICH`

There is no service-local `FoundryAgent` constructor and no portal-agent ID requirement for runtime invocation.

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

### Prompt Governance (Direct Model)

When `ModelTarget.provider == "maf-direct"`, service instructions are loaded from
`prompts/instructions.md` and passed into `DirectModelInvoker`. The app factory
keeps instruction ownership local to the service image while preserving Foundry as
the deployment, telemetry, and evaluation backend.

- Runtime messages remain conversational (`user`, `assistant`, and tool results).
- SLM-first routing still escalates to LLM by complexity threshold.
- Tool schemas are forwarded to MAF as callable tools; dict-schema-only tools are rejected because the JSON-text parser has been removed.

### Direct-Model Deployment Contract

Deploy-time Helm rendering now validates the Foundry contract for each agent service:

- `PROJECT_ENDPOINT` / `PROJECT_NAME` must be present.
- Both direct model roles must be defined (`MODEL_DEPLOYMENT_NAME_FAST` and `MODEL_DEPLOYMENT_NAME_RICH`).

Repo-standard deployment names are:

- SLM (`fast`): `gpt-5-nano`
- LLM (`rich`): `gpt-5`

Use **GlobalStandard** (global deployment) SKU in Azure AI Foundry to maximize
regional compatibility and avoid runtime dependency errors.

### Foundry Readiness Contract

`GET /ready` always includes **actual Foundry runtime status** for the service.

- Library default (`build_service_app` / `create_standard_app`) is **Foundry-preferred, not required**.
- Agentic services opt into enforcement with `require_foundry_readiness=True`.
- When enforcement is enabled, `/ready` returns `503` until every configured direct-model role has a bound `maf-direct` runtime target.
- When enforcement is disabled, `/ready` remains `200`; `foundry_ready` reflects whether at least one callable direct-model target is available, and unbound roles are still reported in the payload.

- `ready` is contextual to the service contract: non-enforced services report callable-target readiness, while enforced services require every configured direct-model role to be bound.
- `not_ready` means enforced traffic should not be routed because one or more configured roles remain unbound or a configuration error was recorded.

Readiness payload now includes a `foundry` capability object with:

- `project_configured`
- `endpoint_configured`
- `configured_roles`
- `bound_roles`
- `unbound_roles`
- `resolved_roles` / `unresolved_roles` compatibility aliases
- `last_error`
- `agent_targets_bound`
- `runtime_resolution_required`
- `auto_ensure_on_startup`

`POST /invoke` reuses the same readiness snapshot and fails closed for enforced agentic services when configured roles remain unbound.

Foundry tracer collection can be controlled per service via
`disable_tracing_without_foundry` on `create_standard_app` / `build_service_app`.
This flag is maintained as a per-service compatibility hint. Core telemetry
remains enabled so fallback/local execution paths keep emitting traces,
metrics, and latest-evaluation data for admin observability surfaces.

### Strict Foundry Enforcement Mode

Set `FOUNDRY_STRICT_ENFORCEMENT=true` to require bound direct-model targets before
serving `/invoke` requests:

- With bound direct-model targets: strict mode enforces Foundry readiness for `/invoke`
- Without bound direct-model targets: `/invoke` can continue through local/fallback logic

This mode is designed for environments where deployed agent services must fail closed on model configuration drift.

Startup auto-ensure is retired with the portal-agent provisioning path; strict mode now depends on direct-model target configuration and `/ready` state.

## Observability (PARTIALLY IMPLEMENTED)

### Logging

✅ **Implemented**: Basic operation logging via `configure_logging` + `log_async_operation`

✅ **Foundry-backed direct model**:
- Agent traces emitted through OpenTelemetry / Application Insights
- Tool-call and request spans captured by framework telemetry
- Evaluation payloads remain available to the Foundry evaluation surface

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

✅ **Foundry-backed direct model**: deployed model content filters remain in force, but prompt-injection handling, tool authorization, and output redaction are framework/service responsibilities.

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
    result = await self._invoke_tool(tool_name, args)
    
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

Test with a real Foundry-backed direct model target:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_agent_foundry_call():
    app = create_standard_app(
        service_name="ecommerce-catalog-search",
        agent_class=CatalogSearchAgent,
        use_direct_model=True,
        require_foundry_readiness=True,
    )
    response = await app.state.agent.handle({"query": "Find Nike shoes"})
    assert "Nike" in str(response)
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

- [ADR-005: Agent Framework](../../adrs/adr-005-agent-framework.md)
- [ADR-004: FastAPI with Dual REST + MCP Exposition](../../adrs/adr-004-fastapi-mcp.md)
- [ADR-007: Memory Architecture](../../adrs/adr-007-memory-tiers.md)
