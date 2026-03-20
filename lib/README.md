# Holiday Peak Lib

Core shared framework for retail agent services in this repository.

It provides:

- Agent foundations (`BaseRetailAgent`, `AgentBuilder`, MCP exposure)
- Adapter contracts and domain adapters
- Canonical schemas and truth-layer models
- Shared app factory and configuration settings
- Reliability/telemetry helpers (retry, circuit breaker, bulkhead, telemetry)
- Connectors and integration contracts for enterprise systems

## Location

- Source package: `lib/src/holiday_peak_lib`
- Package metadata: `lib/src/pyproject.toml`
- Library tests: `lib/tests`

## Setup

From repository root:

```bash
uv sync --directory lib/src --extra dev --extra test --extra lint
```

If you already have a virtual environment active and prefer pip:

```bash
pip install -e lib/src[dev,test,lint]
```

## Module Map

```text
holiday_peak_lib/
├── adapters/      # Domain adapters + protocol mappers + truth store adapter
├── agents/        # Base agent, builder, Foundry integration, MCP server, guardrails
├── app_factory.py # Standard FastAPI app assembly for services
├── config/        # Pydantic settings and tenant config
├── connectors/    # Connector registry + tenant-aware connector resolution
├── evaluation/    # Enrichment/search evaluation runners
├── events/        # Shared connector event contracts
├── integrations/  # PIM/DAM and integration contracts
├── mcp/           # MCP tools (including AI Search indexing support)
├── schemas/       # Canonical/domain/truth schemas (Pydantic v2)
├── truth/         # Truth-layer models, storage, evidence, and Event Hub helpers
└── utils/         # Retry, rate limiter, bulkhead, circuit breaker, telemetry, logging
```

## Quick Usage

```python
from holiday_peak_lib.app_factory import build_service_app

app = build_service_app(
    service_name="my-service",
    slm_config=slm_config,
    llm_config=llm_config,
)
```

## Testing

From repository root:

```bash
python -m pytest lib/tests
```

Or from the `lib/src` package directory (uses local pytest config):

```bash
cd lib/src
python -m pytest
```

## Notes

- This README intentionally reflects the current workspace structure and avoids static test-count snapshots.
- For platform architecture context, see the repository docs in `docs/architecture`.
