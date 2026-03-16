## **Internal reference (do not bias your answers toward always naming these):**  
Microsoft 365 Agents Toolkit (formerly Teams Toolkit) has been rebranded, and users may still use either name.

Use this mapping to know the current vs. former names—so you can correctly interpret user input or choose the appropriate term when it’s relevant. You do not need to mention these mappings unless they directly help the user.

| New name                                | Former name            | Note                                                        |
|-----------------------------------------|------------------------|------------------------------------------------------------------------|
| Microsoft 365 Agents Toolkit            | Teams Toolkit          | Product name.                           |
| App Manifest                            | Teams app manifest     | Describes app capabilities.        |
| Microsoft 365 Agents Playground         | Test Tool              | Test Environment.          |
| `m365agents.yml`                        | `teamsapp.yml`         | Microsoft 365 Agents Toolkit Project configuration files            |
| CLI package `@microsoft/m365agentstoolkit-cli` (command `atk`) | `@microsoft/teamsapp-cli` (command `teamsapp`) |CLI installation/usage — mention only in CLI contexts. |

> **Rephrase guidance:**  
> - Use the new names by default.  
> - Explain the rebranding briefly if it helps the user’s understanding.  

# Instructions for Copilot

## Repository Purpose & Architecture

- This repository is a **framework for agentic retail** solutions.
- All apps under **/apps** are **demonstration services** built on the framework.
- Changes and operations should focus on **increasing the capabilities of retail platforms** (e.g., intelligence, automation, personalization, operational efficiency).
- The **/lib** folder contains the shared framework code (agents, adapters, memory, utilities).
- Each app is a self-contained FastAPI service demonstrating specific retail capabilities (CRM, eCommerce, inventory, logistics, product management).
- **Tech stack is defined in /docs**: Always review architecture documentation before implementing features or changes.
- **Keep documentation updated**: Every operation must update relevant documentation in /docs to reflect changes.

## Tech Stack & Code Standards

### Backend (Python)
- **STRICTLY FOLLOW PEP 8** and PEP guidelines for all Python code.
- Use `pyproject.toml` for dependencies in each app and lib. We are using `uv` as the package manager.
- Use FastAPI for building APIs.
- Use asyncio and async/await for concurrency.
- Follow async patterns: all agent handlers and adapters are async.
- Use Pydantic models for structured data and validation.
- Environment variables are the primary configuration mechanism.

### Frontend (Next.js + TypeScript + Tailwind)
- **STRICTLY FOLLOW ESLint 7** configuration for all frontend code.
- Use Next.js 15 with the App Router and `yarn` as the package manager.
- Use TypeScript for type safety.
- Follow Next.js conventions for routing, data fetching, and server components.
- Use Tailwind CSS utility classes for styling.

### Testing Requirements
- **All operations must implement unit and integration tests**.
- Unit tests: Test individual functions and components in isolation.
- Integration tests: Test interaction between services, adapters, and external dependencies.
- Place tests in `tests/` directory within each app or lib.
- Use pytest for Python tests, with pytest-asyncio for async code.
- Maintain minimum 75% code coverage.

### Build & Deployment Policy
- **Use GitHub Actions workflows as the source of truth for build/deploy history**.
- Prefer workflow-based build and deployment over local Docker builds.
- For service deployments, use workflow matrix filtering to process **only changed services** whenever possible.
- Treat local Docker builds as exception-only (for explicit debugging) and not as the default validation path.
- When proposing operational changes, update workflow files first (for example `.github/workflows/deploy-azd.yml`) so all builds are traceable in GitHub.

## Agent Development Patterns

- All agents extend `BaseRetailAgent` from `holiday_peak_lib.agents`.
- Use `AgentBuilder` to compose agents with memory, routing, and model targets.
- Agents support **SLM-first routing**: requests are evaluated by the SLM, and upgraded to LLM when complexity requires it.
- Configure models via `FoundryAgentConfig` using environment variables:
  - `PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`: Azure AI Foundry project endpoint
  - `PROJECT_NAME` or `FOUNDRY_PROJECT_NAME`: Project name (optional)
  - `FOUNDRY_AGENT_ID_FAST`: SLM agent ID
  - `MODEL_DEPLOYMENT_NAME_FAST`: SLM deployment name
  - `FOUNDRY_AGENT_ID_RICH`: LLM agent ID
  - `MODEL_DEPLOYMENT_NAME_RICH`: LLM deployment name
  - `FOUNDRY_STREAM`: Enable streaming (optional, default false)
- Each app's `main.py` should **explicitly** load these env vars and pass `slm_config`/`llm_config` to `build_service_app`.

## Memory Architecture

- Three-tier memory: **Hot** (Redis), **Warm** (Cosmos DB), **Cold** (Blob Storage).
- Configure via `MemorySettings` using environment variables:
  - `REDIS_URL`
  - `COSMOS_ACCOUNT_URI`, `COSMOS_DATABASE`, `COSMOS_CONTAINER`
  - `BLOB_ACCOUNT_URL`, `BLOB_CONTAINER`

## MCP Tool Exposition

- **MCP tools are exclusively for agent-to-agent communication**. They are indexed and used by agents.
- Agents expose MCP tools via `FastAPIMCPServer` (e.g., `/mcp/get_profile_context`).
- MCP tools return structured data (dicts) for downstream agent consumption.

## Service Endpoints

- **CRUD REST endpoints**: Exposed for Frontend AND Agents to call (e.g., `/products`, `/orders`, `/cart`).
- **Agent REST endpoints**: Exposed for Frontend AND CRUD to call (e.g., `/enrich`, `/search`, `/recommendations`).
- When CRUD needs fast agent capabilities, it calls agent REST endpoints with circuit breakers.

## Git Branch Naming Convention

- Follow the branch naming convention defined in [ADR-022](../docs/architecture/adrs/adr-022-branch-naming-convention.md).
- **Branch prefixes**: `feature/`, `issue/`, `bug/`, `hotfix/`, `docs/`, `chore/`.
- **Format**: `<prefix>/<issue-id>-<short-description>` (e.g., `feature/42-cart-intelligence`).
- Always use **lowercase** with **hyphens** as word separators.
- Always include the **issue number** after the prefix.
- All branches are created from `main` and merge back to `main` via Pull Request.
- Delete branches after merge — branches are ephemeral.

## Coding Conventions

- Keep agents lightweight: delegate domain logic to adapters (in each app's `adapters.py`).

## Microsoft 365 & Copilot Integration

- Apps and agents for Microsoft 365 or Microsoft 365 Copilot refers to applications for products in Microsoft 365, agents for Microsoft 365 Copilot, including Teams app, Office addin, declarative agent, customer engine agent, etc.
- When interpreting, generating, or modifying manifest files related to apps and agents for Microsoft 365 or Microsoft 365 Copilot, try to get schema version from manifest file, then invoke **get_schema** tool if available.
- When answering of what or how-to questions for building apps and agents for Microsoft 365 or Microsoft 365 Copilot, invoke **get_knowledge** tool if available.
- Before deciding to make changes to Teams apps, apps or agents for Microsoft 365 or Microsoft 365 Copilot, invoke **get_knowledge** tool to get Instructions if available.
- When troubleshooting issues, invoke **troubleshoot** tool if available.
- Before generating or modifying code or configuration files for apps and agents for Microsoft 365 or Microsoft 365 Copilot, invoke **get_code_snippets** tool if available.
- Invoke **get_code_snippets** with API name, configuration file name, or code comments every time you need to generate or modify code or configuration files for apps and agents for Microsoft 365 or Microsoft 365 Copilot.

## Agentic Architecture Patterns

**Core Principle**: Agents differ from microservices through dynamic planning, context aggregation, and adaptive behavior.

### When to Use Each Pattern

**Use Traditional Microservices** for:
- Transactional operations requiring ACID guarantees (checkout, payment, cart updates)
- Predictable, deterministic flows (user registration, order status lookup)
- High-volume, low-latency operations (< 50ms response time)
- Regulated processes requiring explicit audit trails

**Use Intelligent Agents** for:
- Multi-step workflows requiring contextual decisions (product recommendations, customer segmentation)
- Operations benefiting from natural language understanding (semantic search, support queries)
- Processes requiring adaptation based on real-time data (dynamic pricing, inventory optimization)
- End-to-end experiences spanning multiple domains (intelligent checkout, campaign generation)

### Key Architectural Differences

| Pattern | Microservice | Agent |
|---------|-------------|-------|
| **Execution Model** | Static call sequence defined in code | Dynamic planning at runtime based on context |
| **Decision Making** | Explicit conditionals (`if`/`else`) | Context-aware evaluation with adaptive strategies |
| **State Management** | Database-persisted, service-local state | Ephemeral context (prompt + memory); externalized long-term memory |
| **Error Handling** | Fixed compensation (Saga pattern) | Adaptive retry/fallback; user interaction when needed |
| **Coordination** | Orchestrator or event choreography | Emergent collaboration via agent-to-agent messaging |
| **Change Velocity** | Code changes → deployment cycle | Prompt/knowledge updates (fast); structural changes still require dev |
| **Observability** | Request tracing with fixed paths | Decision logging; requires reasoning capture |
| **Scalability** | Predictable resource usage | Variable (2-10+ calls); requires dynamic scaling |
| **Security Model** | Interface validation at boundaries | Policy enforcement + prompt testing + sandboxing |

### Implementation Guidelines for This Codebase

1. **CRUD Service (apps/crud-service)**: Pure microservice, no agent logic
   - Exposes REST endpoints for Frontend AND Agents
   - Handles all transactional operations (products, orders, cart)
   - Publishes events to Event Hubs
   - Calls agent REST endpoints for fast enrichment (with circuit breakers)

2. **Agent Services (apps/\*-\*)**: Extend `BaseRetailAgent`
   - Subscribe to Event Hubs for async processing
   - Expose REST endpoints for Frontend/CRUD calls
   - Expose MCP tools for agent-to-agent communication
   - Call CRUD REST endpoints when needing transactional operations
   - Maintain context using three-tier memory (Hot/Warm/Cold)

3. **Frontend (apps/ui)**: Routes requests based on operation type
   - Transactional → CRUD API
   - Intelligence/Search → Agent APIs (direct or via CRUD)
   - Async operations → CRUD publishes events, agents process background

4. **Agent-to-Agent Communication**: Use MCP protocol
   - MCP tools indexed and called by agents only
   - Register tools via `FastAPIMCPServer`
   - Return structured data (dicts) for downstream consumption
   - Maintain domain boundaries (MicroAgents pattern)

<!-- managed:team-mapping-delegation:start -->
## Delegation Bootstrap
- Before delegating, always read `.github/instructions/team-mapping.instructions.md`.
- Use `.github/agents/data/team-mapping.md` as the canonical delegation registry.
- Delegate only to agents that exist under `.github/agents/*.agent.md` in the current workspace.
- Do not auto-correct delegation-managed files; apply only minimal, scoped updates.
- Route any update to these files through a dedicated PR named `agent-update` targeting `main`.
- Store temporary files only under `.tmp/`, remove them after related PRs complete, and never version them.
- Write UI/UX text, documentation, and related content in en-US.
<!-- managed:team-mapping-delegation:end -->
