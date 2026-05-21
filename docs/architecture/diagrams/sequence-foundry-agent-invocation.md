# Sequence Diagram: DirectModelInvoker Flow

This diagram illustrates the canonical agent invocation flow using the Microsoft Agent Framework (MAF) `DirectModelInvoker`, which constructs `agent_framework.Agent` in-process over a pluggable `ChatClient`.

## Flow Overview

1. **Request** → FastAPI endpoint receives invoke request
2. **Agent Build** → `AgentBuilder` composes agent with tools, memory, and model config
3. **Model Routing** → SLM-first assessment, optional upgrade to LLM
4. **MAF Invocation** -> `DirectModelInvoker` delegates to in-process `agent_framework.Agent`
5. **Tool Execution** -> Tools forwarded through native MAF function-calling
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
    participant Invoker as DirectModelInvoker
    participant MAF as agent_framework.Agent
    participant Chat as FoundryChatClient
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
    Invoker->>MAF: Agent(instructions, chat_client, tools)
    MAF->>Chat: run(messages, deployment=fast)
    Chat-->>MAF: {response, tool_calls}

    alt Tool calls present
        Note over MAF: Tools forwarded via native function-calling
        MAF->>Tools: execute(tool_calls)
        Tools-->>MAF: tool_results
        MAF->>Chat: continue(messages, tool_results)
        Chat-->>MAF: {final_response}
    end

    MAF-->>Invoker: agent_response

    alt Confidence < threshold
        Note over Invoker: Upgrade to LLM
        Invoker->>MAF: Agent(instructions, chat_client, tools)
        MAF->>Chat: run(messages, deployment=rich)
        Chat-->>MAF: {response, tool_calls}
        MAF-->>Invoker: agent_response
    end

    Invoker-->>Agent: structured_result
    Agent->>Memory: parallel_set(hot, warm)
    Agent-->>API: AgentResponse
    API-->>Client: 200 OK {result}
```

## Key Design Decisions

- **MAF direct-model runtime**: Tools are registered with the in-process `Agent` and forwarded through native MAF function-calling. No portal-managed Foundry Agent record is required at runtime.
- **Parallel memory I/O**: Hot and warm memory are read/written concurrently via `asyncio.gather`.
- **SLM-first with LLM upgrade**: Every request starts with the fast (SLM) model; only complex queries escalate to the rich (LLM) model.

## Related

- [ADR-010: Model Routing](../adrs/adr-010-model-routing.md)
- [Agent Library Reference](../components/libs/agents.md)
- [Components Overview](../components.md)
