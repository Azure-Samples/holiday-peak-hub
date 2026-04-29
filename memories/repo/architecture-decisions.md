# Architecture Decisions

## Mandatory: Read ADRs Before Architectural Work

- **ALWAYS read `docs/architecture/adrs/`** before proposing or implementing any architectural change.
- **27 ADR files** (adr-001 through adr-027), sequentially numbered after 2026-04-28 consolidation.
- **5 revised ADRs** (consolidated): ADR-003 (adapter pattern + boundaries + connector registry), ADR-004 (FastAPI + dual REST/MCP exposition), ADR-007 (memory tiers + builder + partitioning + namespace isolation), ADR-017 (azd provisioning + Flux CD GitOps deployment), ADR-024 (agent communication + isolation + async contracts).
- Never contradict an accepted ADR without explicitly proposing a superseding ADR.
- Check for relevant ADRs by topic before creating new patterns, services, or integration points.

## Foundry Agents — Mandatory on Every Call (2026-04-28)

- **ADR**: `docs/architecture/adrs/adr-005-agent-framework.md` (§ Mandatory Foundry Invocation Policy)
- **Decision**: ALL LLM calls MUST route through Azure AI Foundry Agents. No direct Responses API or Chat Completions bypasses.
- **Rationale**: Portal-native agent monitoring and the Evaluations API are strategic observability differentiators for the solution. Bypassing Foundry Agents loses agent-level telemetry, dashboard visibility, and quality drift detection.
- **Rejected alternative**: Hybrid architecture (direct API for latency-critical, Foundry Agents for complex). Rejected because observability value outweighs the 2-5s latency overhead.
- **Decision record**: `docs/architecture/foundry-agents-vs-direct-api-report.md`
- **Latency mitigation** (within Foundry Agents path only):
  - `reasoning_effort`: minimal (fast) / low (rich) — prevents server default of medium
  - `max_output_tokens`: 800 (fast) / 2000 (rich) — caps runaway generation
  - `temperature`: 0.0 (fast) / 0.3 (rich) — reduces speculative sampling
  - Env vars: `FOUNDRY_REASONING_EFFORT_*`, `FOUNDRY_MAX_OUTPUT_TOKENS_*`, `FOUNDRY_TEMPERATURE_*`
