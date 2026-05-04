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

## Retailer IQ / Recommendation Agent Evolution (2026-05-03)

- `docs/roadmap/015-retailer-iq-recommender-system-plan.md` is the canonical plan for Retailer IQ and RecommenderIQ.
- `search-enrichment-agent` is the current evolutionary host for `recommendation-agent` capability; do not rename deployments casually.
- `recommendation-agent` is a capability boundary inside a larger recommendation system, not the whole Retailer IQ system.
- `ecommerce-catalog-search` remains the online search/query consumer; `search-enrichment-agent` owns correlated product enrichment and recommendation candidate/rank/compose surfaces.
- User/customer data must not live in Product Graph; recommendation state uses derived events and approved service contracts across REST/MCP/Event Hubs.
- Hot-path recommendation ranking starts with a deterministic/classical ML baseline; Foundry/LLM is for intent, explanation, governance, or complex orchestration only.
- Concrete recommender schemas/engine helpers stay inside the `recommendation-agent` host; promote only neutral contracts to `holiday_peak_lib` after multiple independent services need them.
- Implemented REST/MCP contracts: `/recommendations/candidates`, `/recommendations/rank`, `/recommendations/compose`, `/recommendations/feedback`, `/recommendations/explain`, `/models/status`.
- Last validation: `python -m pytest apps/search-enrichment-agent/tests` passed with 48 tests.

## Recommender Model Lifecycle Constraint (2026-05-03)

- Recommender model training/tracking must follow the MLET guidance from `https://github.com/cataldir/mlet/`.
- Keep model training offline and outside the request path; the agent serves inference, orchestration, feedback, and model status.
- Use ML Canvas/data readiness before training; start with deterministic and classical ML baselines.
- Track experiments with MLflow: parameters, metrics, artifacts, code version, dataset version, and run lineage.
- Version datasets and pipelines with DVC or equivalent cloud-backed lineage; never commit raw training data to Git.
- Promote models through a registry with explicit Staging/Production/Archived states, approval gates, rollback, and model cards.
- `recommendation-agent` `/models/status` should eventually read active model metadata from the registry instead of hard-coded constants.

## Retailer IQ Demo Notebook (2026-05-03)

- Live notebook artifact: `docs/demos/agent-playgrounds/retailer_iq_recommender_system_live.ipynb`.
- Executive sales notebook artifact: `docs/demos/agent-playgrounds/retailer_iq_recommender_system_demo.ipynb`.
- The notebook targets `holidaypeakhub405` dev through APIM, discovers UI/APIM endpoints, and calls all deployed agent health routes plus CRUD/UI probes.
- Executive framing should lead with Azure as the operating fabric, agentic microservices as governed retail signal providers, and KPI scorecards for conversion, NPS/CSAT, margin, revenue, readiness, latency, and revenue per platform dollar.
- Recommendation-agent demo uses APIM MCP/direct-route attempts for `/models/status`, `/recommendations/candidates`, `/recommendations/rank`, `/recommendations/compose`, `/recommendations/explain`, and `/recommendations/feedback`.
- Keep demo code presentation-oriented and resilient: if APIM/backends are unhealthy, show actual failure status and an explicit local deterministic preview rather than hiding the gap.

## Retailer IQ Root Demo UI (2026-05-04)

- Root route `/` is the primary Retailer IQ executive cockpit demo; notebooks are secondary proof/runbook artifacts.
- First viewport should frame Azure as the operating fabric for agentic retail, with KPI scorecards, agent workload groups, and recommendation-agent proof.
- Root demo must preserve live product/search proof while making RecommenderIQ, Product IQ, Customer IQ, readiness gates, and business impact visible to executives.
- Use deterministic `en-US` number formatting in SSR/client-rendered UI to avoid hydration drift.
- Timed intro overlays must not restart when parent callback identities change during live hook refreshes.
