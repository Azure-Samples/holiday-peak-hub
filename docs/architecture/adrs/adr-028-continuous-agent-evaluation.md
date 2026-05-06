# ADR-028: Continuous Agent Evaluation Engine

**Status**: Accepted
**Date**: 2026-05
**Issue**: #896
**Deciders**: Architecture Team, Platform Engineering

## Context

The platform runs agent services across CRM, ecommerce, inventory, logistics, product management, and product truth workflows. Existing evaluation support was runtime-only: selected agents called `holiday_peak_lib.evaluation.run_evaluation()` and recorded the latest result in the in-memory Foundry tracer exposed by `/agent/evaluation/latest`.

That was useful for local checks, but insufficient for production governance because it lacked versioned datasets, shared schemas, CI feedback, continuous monitoring, and a formal integration path for self-healing escalation when response quality drifts.

## Decision

Introduce a shared continuous evaluation engine in `holiday_peak_lib.evaluation`.

The engine uses per-agent `.foundry/` directories as the local source of truth for evaluation configuration and JSONL datasets. It uses the Azure AI Foundry evaluation SDK when available and falls back to deterministic local scoring when the SDK or Foundry environment is unavailable.

### Core Contracts

- `EvalConfig` describes agent name, evaluators, thresholds, datasets, model targets, and event publishing behavior.
- `EvalCase` validates JSONL test cases with `query`, `expected_behavior`, optional `response`, optional `ground_truth`, and expected SLM/LLM tier.
- `EvaluationRunResult` remains backward-compatible for existing app calls.
- `DriftReport` captures threshold and baseline breaches.
- `EvaluationDriftSignal` adapts quality drift into the self-healing `FailureSignal` contract.
- `EvaluationResultEvent` is the normalized payload for the `agent-evaluation-results` topic.

### Runtime Shape

```mermaid
%%{init: {'theme':'base', 'themeVariables': {
  'primaryColor':'#FFB3BA',
  'primaryTextColor':'#000',
  'primaryBorderColor':'#FF8B94',
  'lineColor':'#BAE1FF',
  'secondaryColor':'#BAE1FF',
  'tertiaryColor':'#FFFFFF'
}}}%%
flowchart LR
  F[.foundry/eval-config.yaml] --> L[DatasetLoader]
  D[.foundry/datasets/*.jsonl] --> L
  L --> R[ConfiguredEvaluationRunner]
  R --> S{Evaluator Strategy}
  S -->|SDK available| FE[FoundryEvaluatorStrategy]
  S -->|SDK unavailable| LE[LocalEvaluatorStrategy]
  FE --> O[EvaluationRunResult]
  LE --> O
  O --> DD[DriftDetector]
  DD -->|drift| SH[SelfHealingKernel T3 escalation]
  O --> API[/agent/evaluation/run and /history]
  O --> EV[agent-evaluation-results]
```

### Patterns

- **Repository**: `DatasetLoader` isolates `.foundry` file storage from runtime evaluation logic.
- **Strategy**: `FoundryEvaluatorStrategy` and `LocalEvaluatorStrategy` provide interchangeable scoring backends.
- **Template Method**: `BaseEvaluationRunner.run()` defines load → select evaluator → execute → collect result.
- **Factory Method**: app factory discovery returns a configured runner only when a service opts in with `.foundry` assets.

## Consequences

### Positive

- Agents can opt into CI and continuous monitoring by adding `.foundry/eval-config.yaml` and JSONL cases.
- CI remains resilient because local deterministic scoring runs without Foundry credentials.
- Evaluation drift enters the existing incident lifecycle without permitting autonomous prompt/model/code changes.
- Existing `run_evaluation()` callers remain backward-compatible.

### Negative

- Initial local fallback metrics are coarse and primarily validate dataset readiness until real responses or Foundry runs are available.
- Per-agent datasets require ongoing ownership and refresh discipline.
- Continuous monitoring can create alert noise if thresholds are calibrated too aggressively.

### Risk Mitigation

- CI gate starts in advisory mode.
- Drift detection uses configurable consecutive-failure windows and rate limits.
- `SurfaceType.EVALUATION` is T3 manual-only in the self-healing kernel.
- Pilot rollout starts with `ecommerce-catalog-search`, `truth-enrichment`, and `search-enrichment-agent`.

## References

- [ADR-005](adr-005-agent-framework.md) — Microsoft Agent Framework + Foundry
- [ADR-010](adr-010-model-routing.md) — SLM-First Model Routing Strategy
- [ADR-017](adr-017-deployment-strategy.md) — Deployment Strategy
- [ADR-024](adr-024-agent-communication-policy.md) — Agent Communication Policy and Async Contracts
- [ADR-025](adr-025-self-healing-boundaries.md) — Self-Healing Boundaries
