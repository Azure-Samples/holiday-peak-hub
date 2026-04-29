# Sequence Diagram: FoundryAgentInvoker Flow

This diagram illustrates the agent invocation flow using the Microsoft Agent Framework (MAF) `FoundryAgentInvoker`, which replaced the legacy `FoundryInvoker` in PR #802.

## Flow Overview

1. **Request** → FastAPI endpoint receives invoke request
2. **Agent Build** → `AgentBuilder` composes agent with tools, memory, and model config
3. **Model Routing** → SLM-first assessment, optional upgrade to LLM
4. **MAF Invocation** → `FoundryAgentInvoker` delegates to `FoundryAgent` runtime
5. **Tool Execution** → Tools forwarded through MAF middleware (not silently dropped)
6. **Response** → Structured result returned through the agent pipeline

## Sequence Diagram

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
sequenceDiagram
    actor Client
    participant API as FastAPI App
    participant Builder as AgentBuilder
    participant Agent as BaseRetailAgent
    participant Invoker as FoundryAgentInvoker
    participant MAF as FoundryAgent (MAF)
    participant Foundry as Azure AI Foundry
    participant Tools as MCP Tools
    participant Memory as Memory Stack

    Client->>API: POST /invoke {"query": "..."}
    API->>Builder: build_service_app(slm_config, llm_config)
    Builder->>Agent: compose(tools, memory, guardrails)

    Note over Agent: Step 1: Load Context
    Agent->>Memory: parallel_get(hot, warm)
    Memory-->>Agent: {session, profile, history}

    Note over Agent: Step 2: SLM-First Routing
    Agent->>Invoker: invoke(query, context, tools)
    Invoker->>MAF: FoundryAgent.create(agent_id, tools)
    MAF->>Foundry: POST /agents/{fast}/invoke
    Foundry-->>MAF: {response, tool_calls}

    alt Tool calls present
        Note over MAF: Tools forwarded via MAF middleware
        MAF->>Tools: execute(tool_calls)
        Tools-->>MAF: tool_results
        MAF->>Foundry: POST /agents/{fast}/continue
        Foundry-->>MAF: {final_response}
    end

    MAF-->>Invoker: agent_response

    alt Confidence < threshold
        Note over Invoker: Upgrade to LLM
        Invoker->>MAF: FoundryAgent.create(agent_id_rich, tools)
        MAF->>Foundry: POST /agents/{rich}/invoke
        Foundry-->>MAF: {response, tool_calls}
        MAF-->>Invoker: agent_response
    end

    Invoker-->>Agent: structured_result
    Agent->>Memory: parallel_set(hot, warm)
    Agent-->>API: AgentResponse
    API-->>Client: 200 OK {result}
```

## Key Design Decisions

- **MAF `FoundryAgent` runtime**: Tools are registered with the agent at creation time and forwarded through MAF middleware, solving the silent tool-dropping issue in the legacy `FoundryInvoker`.
- **Parallel memory I/O**: Hot and warm memory are read/written concurrently via `asyncio.gather`.
- **SLM-first with LLM upgrade**: Every request starts with the fast (SLM) model; only complex queries escalate to the rich (LLM) model.

## Related

- [ADR-010: Model Routing](../adrs/adr-010-model-routing.md)
- [Agent Library Reference](../components/libs/agents.md)
- [Components Overview](../components.md)
