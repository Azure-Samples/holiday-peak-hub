# ADR-005: Microsoft Agent Framework + Foundry

**Status**: Accepted  
**Date**: 2024-12  
**Updated**: 2026-04-28 — Added mandatory Foundry invocation policy  
**Deciders**: Architecture Team, Ricardo Cataldi  
**Tags**: architecture, foundry, agents, telemetry, observability, latency

## Context

Need standardized agent orchestration with support for:
- Multi-step reasoning
- Tool calling
- Memory management
- Model selection (SLM vs LLM)

## Decision

**Use Microsoft Agent Framework with Foundry SDK** for all agent logic.

## Implementation Status (2026-03-18)

- **Implemented**: Agent services consistently use the shared `BaseRetailAgent`/`AgentBuilder` pattern with `FoundryAgentConfig` wiring from environment variables.
- **Partially diverged**: The exact `azure.ai.agents.AgentClient` usage shown here is no longer the dominant integration surface in app code; the repository standard is the `holiday_peak_lib.agents` abstraction layer.
- **Implemented with fallback behavior**: Foundry-targeted configuration is first-class, but local/test execution paths can run without fully provisioned Foundry dependencies.

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

## Mandatory Foundry Invocation Policy (2026-04-28)

### Policy

**All LLM calls MUST route through Azure AI Foundry Agents. No direct Responses API or Chat Completions API bypasses are permitted.**

### Context

The Foundry Agents layer adds 2–5s overhead per request on top of model inference time. A thorough evaluation of switching to the direct Responses API was conducted ([foundry-agents-vs-direct-api-report](../foundry-agents-vs-direct-api-report.md)) covering telemetry, sessions, versioning, reasoning control, tools, middleware, content safety, cost, roadmap risk, and hybrid feasibility.

A hybrid architecture (direct API for latency-critical agents, Foundry for complex ones) was evaluated and **rejected** because it splits the observability surface, loses portal-native monitoring for the majority of agents, and the latency gain does not justify the observability loss.

### Rationale

1. **Portal-native agent monitoring** — The Azure AI Foundry portal agent dashboard (invocations, latency percentiles, error rates, token usage per agent) is a first-class operational tool. Direct API calls are invisible to this dashboard.

2. **Evaluations API for quality drift** — Foundry's evaluation framework operates natively on agent traces, enabling automated quality scoring, regression detection, and A/B comparison across agent versions.

3. **Observability as a solution differentiator** — For a retail platform handling peak holiday traffic, monitoring and auditing every agent interaction through a single pane is a competitive advantage that justifies the latency trade-off.

4. **Latency is mitigable within Foundry Agents** — The following optimizations reduce model-side latency without bypassing the Foundry layer:
   - `reasoning_effort`: `minimal` (fast) / `low` (rich)
   - `max_output_tokens`: 800 (fast) / 2000 (rich)
   - `temperature`: 0.0 (fast) / 0.3 (rich)
   - Env vars: `FOUNDRY_REASONING_EFFORT_*`, `FOUNDRY_MAX_OUTPUT_TOKENS_*`, `FOUNDRY_TEMPERATURE_*`

### Enforcement

- `FoundryAgentInvoker` is the only production `ModelInvoker` implementation
- `BaseRetailAgent.invoke_model()` is the single invocation entry point
- No `ChatCompletionsClient`, `openai.ChatCompletion`, `AzureOpenAI`, or `responses.create()` calls permitted in application code

## Consequences

**Positive**: Foundry ecosystem, Microsoft support, automatic updates, unified observability, quality drift detection  
**Negative**: Vendor lock-in, less flexibility than custom agents, 2–5s latency overhead on every call

## Related ADRs
- [ADR-004: FastAPI with Dual REST + MCP](adr-004-fastapi-mcp.md)
- [ADR-010: SLM-First Model Routing](adr-010-model-routing.md)
- [ADR-024: Agent Communication Policy](adr-024-agent-communication-policy.md)
