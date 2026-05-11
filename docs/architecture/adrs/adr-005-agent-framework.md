# ADR-005: Microsoft Agent Framework + Foundry

**Status**: Accepted  
**Date**: 2024-12  
**Updated**:
  - 2026-04-28 — Added mandatory Foundry invocation policy *(superseded 2026-05-10; see below)*
  - 2026-05-10 — Reversed to mandatory **MAF direct-model** invocation policy; portal-managed Foundry Agent records retired  
   - 2026-05-11 — Recorded Wave 4c code cleanup; portal-agent Azure resources remain manual deprovisioning scope
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

## Mandatory Foundry Invocation Policy (2026-04-28) — SUPERSEDED 2026-05-10

> **Status**: Superseded by *Mandatory MAF Invocation Policy (2026-05-10)* below. The 2026-04-28 policy is retained for historical context; it is no longer in force. The latency/observability trade-off it accepted was re-evaluated after the inventory hosted-agent precedent (commit `4cf0e546`, 2026-04-25) and the data did not hold once direct-model invocation was prototyped end-to-end.

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

## Mandatory MAF Invocation Policy (2026-05-10)

### Policy

**All LLM calls MUST route through `agent_framework.Agent` over a pluggable `ChatClient` (MAF direct-model invocation). Portal-managed Foundry Agent records (V2 prompt-agent path: `project_client.agents.create_version` with `PromptAgentDefinition`) are retired. Foundry remains the canonical model-deployment, telemetry, and evaluation backend — not an agent-runtime intermediation layer.**

### Context

The 2026-04-28 policy mandated that every LLM call route through a portal-managed Foundry Agent record. Two pieces of evidence accumulated against that policy:

1. **Latency overhead is real and unmitigated.** The 2–5s overhead per request did not yield the operational return the prior policy claimed. Portal-native invocation dashboards were redundant with the per-agent OTel → Application Insights traces we already emit; the Evaluations API surface continued to operate against agent traces regardless of whether those traces originated from a portal-managed Agent record or from a MAF in-process `Agent`.

2. **The inventory hosted-agent precedent (commit `4cf0e546`, 2026-04-25).** A direct-model implementation (`apps/inventory-health-check/src/.../hosted_main.py`) using `agent_framework.foundry.FoundryChatClient` + `agent_framework.Agent` + `default_options={"store": False}` was prototyped and then deleted — not because the direct-model approach was wrong, but because it had been shipped as an *additional* entry point alongside `main.py`, creating a dual-runtime anti-pattern where two MAF agents (one direct, one portal-attached) existed for the same service. The lesson from that experiment is the foundation of this amendment: **single architecture, no parallel stacks.** The replacement direction below is the correct shape with the dual-runtime mistake removed.

3. **Tool-calling fidelity.** The `FoundryAgentInvoker` plumbing forwards tools through a hand-rolled JSON-text-parsing path (`_inject_tool_prompt` + `_extract_tool_calls_from_text` + `schema_tools_injected` flag in `lib/src/holiday_peak_lib/agents/foundry.py`). Native function-calling under MAF `Agent(tools=[...])` is structurally cleaner: the model emits structured `tool_calls`, MAF executes the Python callable in-process, and feeds the result back into the loop. The JSON-parsing fallback is deleted as part of the cutover.

### Rationale

1. **Provider-agnostic by design.** The direct-model path uses MAF's `ChatClient` abstraction (`FoundryChatClient`, `OpenAIChatClient`, `AzureOpenAIChatClient`, etc.). Foundry is one supported provider, not a mandatory intermediation layer. Switching providers becomes a `ChatClient` swap rather than a re-architecting exercise.

2. **Observability preserved, not lost.** Foundry remains the canonical:
   - **Model deployment plane** — `MODEL_DEPLOYMENT_NAME_FAST` / `MODEL_DEPLOYMENT_NAME_RICH` continue to point at Foundry-hosted deployments.
   - **Telemetry backend** — OTel exporter routes traces to Application Insights; Foundry tracing endpoint is configured via `APPLICATIONINSIGHTS_CONNECTION_STRING` (the same env var the deleted `hosted_main.py` already used).
   - **Evaluation surface** — the Foundry Evaluations API continues to operate on emitted agent traces; it does not require a portal-managed Agent record to function.

3. **Lifecycle owned by the image.** Prompt, model deployment reference, and tool registrations are baked into the AKS container image. There is no Foundry-portal Agent record to drift against. A prompt change is a code change, gated by PR review and CI; not a portal edit that bypasses code review.

4. **No tool-shape regression.** Holiday Peak Hub has no tool dependency on the Foundry Agent Service's server-side tool dispatch (no Code Interpreter, no `file_search`, no Bing grounding via Agent). Every tool is a local Python callable. Native MAF function-calling is a strict superset of what the prompt-agent path delivered.

### Enforcement

- `DirectModelInvoker` (in `lib/src/holiday_peak_lib/agents/direct.py`) is the only production `ModelInvoker` implementation.
- `BaseRetailAgent.invoke_model()` remains the single invocation entry point at the agent-class boundary.
- `AgentBuilder.with_direct_models(slm_config=..., llm_config=..., complexity_threshold=...)` is the only sanctioned wiring path in service `main.py`.
- `FoundryAgentInvoker`, `/foundry/agents/ensure`, `ensure-foundry-agents.{sh,ps1}`, `project_client.agents.create_version`, and the JSON-text tool-call parser have been removed from framework runtime code as of Wave 4c (see [docs/project-status.md](../../project-status.md)).
- The 42 V2 portal-managed agents in project `aipholidaris` (21 services × `fast` + `rich` roles) remain outside repository automation scope for this cleanup and will be deprovisioned manually by the owner.
- **Single-architecture guardrail (from the inventory hosted-agent lesson):** A service must not ship a second entry point (e.g., `hosted_main.py`, parallel `ResponsesHostServer`, secondary port) alongside `main.py`. The MAF `Agent` is constructed inside the existing FastAPI handler in `main.py`. PRs introducing parallel runtimes are rejected at review.
- No `ChatCompletionsClient`, `openai.ChatCompletion`, `AzureOpenAI`, or `responses.create()` calls permitted in application code outside the MAF `ChatClient` boundary.

## Consequences

**Positive (2026-05-10 direction)**: Provider-agnostic chat-client surface; image-owned prompt/model/tool lifecycle (no portal drift); native function-calling fidelity; deletion of JSON-text tool-call parser; 2–5s per-request latency reclaimed; single architecture across all 26 agent services.

**Negative (2026-05-10 direction)**: One-time migration cost across 26 services; portal Agent dashboard ceases to be a usable invocation surface (mitigated by OTel → Application Insights traces, which already cover the same data); the 42 V2 portal agents in `aipholidaris` need manual deprovisioning after cutover (irreversible without re-running provisioning).

**Historical (2024-12 → 2026-04-28 direction, retained for context)**: Foundry ecosystem, Microsoft support, automatic updates, unified observability, quality drift detection — vs. vendor lock-in, less flexibility than custom agents, 2–5s latency overhead on every call.

## Related ADRs
- [ADR-004: FastAPI with Dual REST + MCP](adr-004-fastapi-mcp.md)
- [ADR-010: SLM-First Model Routing](adr-010-model-routing.md)
- [ADR-024: Agent Communication Policy](adr-024-agent-communication-policy.md)
