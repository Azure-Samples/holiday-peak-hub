# ADR-028: Continuous Agent Evaluation Engine

**Status**: Accepted
**Date**: 2026-05
**Issue**: #897
**Deciders**: Architecture Team, Platform Engineering

## Context

Holiday Peak Hub is both a framework and a product. The framework needs a reusable evaluation contract for adopters, while the product needs per-agent quality gates that can support continuous monitoring, canary decisions, and manual escalation when quality drifts.

Existing evaluation support was runtime-only: selected agents could call `holiday_peak_lib.evaluation.run_evaluation()` and expose the latest result through `/agent/evaluation/latest`. That was useful for local checks, but insufficient for production governance because it lacked versioned datasets, shared schemas, optional app-factory discovery, CI entry points, and a formal integration path for self-healing escalation.

The current product runtime is the direct-model Microsoft Agent Framework path. This ADR does not reintroduce the retired portal-agent runtime, `AgentBuilder.with_foundry_models()`, or `/foundry/agents/ensure`.

## Decision

Introduce a shared continuous evaluation engine in `holiday_peak_lib.evaluation`.

The engine uses per-service `.foundry/` directories as the local source of truth for evaluation configuration and JSONL datasets. It uses Azure AI Evaluation when that optional SDK is available, and falls back to deterministic local scoring when the SDK or Foundry environment is unavailable.

Services opt in by adding `.foundry/eval-config.yaml` and dataset files under their service root. App factory discovery is optional and scoped to per-service configuration; services without evaluation assets still start normally.

### Core Contracts

- `EvalConfig` describes agent name, evaluators, thresholds, datasets, model targets, and event publishing intent.
- `EvalCase` validates JSONL test cases with `query`, `expected_behavior`, optional `response`, optional `ground_truth`, and expected SLM/LLM tier.
- `EvaluationRunResult` remains backward-compatible for existing app calls and adds canonical keys: `eval.score`, `eval.baseline_id`, and `baselineSource: continuous-eval`.
- `DriftReport` captures threshold and baseline breaches.
- `EvaluationDriftSignal` adapts quality drift into the self-healing `FailureSignal` contract.
- `EvaluationResultEvent` is the normalized payload shape for `agent-evaluation-results` consumers.

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
  O --> EV[agent-evaluation-results payload]
```

### Patterns

- **Repository**: `DatasetLoader` isolates `.foundry` file storage from runtime evaluation logic.
- **Strategy**: `FoundryEvaluatorStrategy` and `LocalEvaluatorStrategy` provide interchangeable scoring backends.
- **Template Method**: `BaseEvaluationRunner.run()` defines load -> select evaluator -> execute -> collect result.
- **Factory Method**: app factory discovery returns a configured runner only when a service opts in with `.foundry` assets.

## Consequences

### Positive

- Agents can opt into CI and continuous monitoring by adding `.foundry/eval-config.yaml` and JSONL cases.
- CI remains resilient because deterministic local scoring runs without Foundry credentials.
- Evaluation drift enters the existing incident lifecycle without permitting autonomous prompt, model, or code changes.
- Existing `run_evaluation()` callers remain backward-compatible.
- ADR-029 and ADR-031 now have stable evaluation keys for canary gates and telemetry consumers.

### Negative

- Initial local fallback metrics are coarse and primarily validate dataset readiness until real responses or Foundry runs are available.
- Per-agent datasets require ongoing ownership and refresh discipline.
- Continuous monitoring can create alert noise if thresholds are calibrated too aggressively.

### Risk Mitigation

- Drift detection uses configurable consecutive-failure windows and rate limits.
- `SurfaceType.EVALUATION` is T3 manual-only in the self-healing kernel.
- The framework discovery path is opt-in and does not block services without `.foundry/eval-config.yaml`.
- The implementation preserves the direct-model runtime and Hosted/Custom Foundry surface taxonomy from ADR-036.

## References

- [ADR-005](adr-005-agent-framework.md) — Microsoft Agent Framework + Foundry
- [ADR-010](adr-010-model-routing.md) — SLM-First Model Routing Strategy
- [ADR-017](adr-017-deployment-strategy.md) — Deployment Strategy
- [ADR-024](adr-024-agent-communication-policy.md) — Agent Communication Policy and Async Contracts
- [ADR-025](adr-025-self-healing-boundaries.md) — Self-Healing Boundaries
- [ADR-029](adr-029-agc-weighted-canary-policy.md) — AGC Weighted Canary Policy with Automatic Rollback
- [ADR-031](adr-031-otel-span-attributes-contract.md) — OTEL Span Attributes Contract for Retail Agents
- [ADR-036](adr-036-foundry-agent-surface-taxonomy.md) — Foundry Agent Surface Taxonomy