# ADR-001: Python 3.13 as Primary Language

**Status**: Accepted  
**Date**: 2024-12  
**Deciders**: Architecture Team, Ricardo Cataldi

## Context

The accelerator requires a language that supports:
- Async/await for concurrent I/O (Redis, Cosmos, Blob, Event Hubs, AI Search)
- Rich ecosystem for AI/ML integration (Microsoft Agent Framework, Foundry SDK)
- Fast iteration cycles for adapter/agent development
- Strong typing for maintainability (Pydantic, type hints)
- Enterprise support and Azure SDK maturity

## Decision

**Adopt Python 3.13 across all libs and apps.**

### Rationale
1. **Performance**: Python 3.13 includes JIT improvements and faster async/await
2. **Async Native**: First-class `asyncio` support for parallel adapter calls
3. **AI Ecosystem**: Microsoft Agent Framework, Foundry SDK, Azure SDKs all Python-first
4. **Typing**: Pydantic v2 + Python 3.13 type hints enable strong contracts
5. **Tooling**: pytest, pylint, black, isort provide robust CI/CD gates

## Consequences

### Positive
- **Fast Development**: Rapid prototyping for adapters and agents
- **Azure Integration**: Native SDKs for all required services
- **Agent Framework**: Direct Foundry integration without FFI overhead
- **Hiring**: Large talent pool familiar with Python

### Negative
- **Runtime Performance**: Lower than compiled languages for CPU-bound tasks (mitigated by offloading ML to hosted models)
- **Packaging**: Virtual env management adds setup complexity (mitigated by standardized pyproject.toml)
- **GIL**: Global Interpreter Lock limits true parallelism (mitigated by async I/O focus and multi-process deployment)

## Alternatives Considered

### C# / .NET
- **Pros**: Better runtime performance, strong typing, Azure SDK parity
- **Cons**: Smaller AI/ML ecosystem; Agent Framework support lagging; slower iteration for prototypes

### TypeScript / Node.js
- **Pros**: Single language for UI + backend; strong async model
- **Cons**: Weaker AI/ML ecosystem; no native Agent Framework support; less mature Azure AI SDKs

### Go
- **Pros**: Excellent concurrency, fast binaries
- **Cons**: Minimal AI/ML libraries; no Agent Framework support; immature Azure AI SDKs

## Implementation Notes

- All pyproject.toml files specify `requires-python = ">=3.13"`
- CI matrix tests on Python 3.13 only (no backcompat with 3.11/3.12)
- Azure Functions / AKS base images locked to Python 3.13 slim
- Pre-commit hooks enforce pylint, black, isort compliance

## Related ADRs

- [ADR-005: FastAPI + MCP](adr-005-fastapi-mcp.md) — Async framework choice
- [ADR-006: Agent Framework](adr-006-agent-framework.md) — Python-first SDK
