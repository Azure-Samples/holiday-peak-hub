# Agentic Setup Benchmark Bundle

Holiday Peak Hub can generate a public-safe Agentic Setup Benchmark (ASB) bundle for production-like setup-surface evaluation. The bundle is local and deterministic by default: it uses synthetic retail requests, repository topology metadata, and a declared cost model instead of private production traces.

## Scope

The ASB bundle supports three evidence tracks:

- **Cost boundary checks**: `tests/evaluation/asb_v1/cost-model.yaml` declares finite coordinate bounds and normalized cost components. Those bounds define the compact production-like setup region used by the evaluation.
- **Topology extraction**: `lib/src/holiday_peak_lib/evaluation/catalog_topology.py` extracts the agent/API graph from `apps/foundry-surfaces.yaml` and CRUD `AgentClient` calls.
- **Production-like workload execution**: `scripts/evaluation/run_agentic_setup_benchmark.py` generates setup-surface, local quadratic support, falsification, manifest, and claim-map artifacts.

The bundle is production-like, not private production telemetry. It preserves the repository's framework-and-product positioning while keeping all generated evidence public-safe.

## Data Policy

The initial ASB v1 scenario under `tests/evaluation/asb_v1/` contains synthetic retail requests only. It must not include customer data, secrets, proprietary identifiers, or live telemetry exports. Future telemetry-derived runs can replace the cost source, but only after redaction and provenance are documented in the generated manifest.

## Cost Model

`cost-model.yaml` maps operational quantities into the cost function `Phi`:

- model tokens,
- tool/API calls,
- memory operations,
- search operations,
- latency,
- human-review minutes.

Each component has a unit, a non-negative weight, a positive baseline, and a source. Coordinate bounds are required for retrieval depth, memory policy, tool budget, token budget, topology policy, and HITL policy. The runner writes `cost-provenance.json` with the assumptions and compactness check.

## Run Commands

Generate a bundle:

```powershell
python scripts/evaluation/run_agentic_setup_benchmark.py --scenario tests/evaluation/asb_v1 --output-dir .tmp/asb_v1
```

Validate a bundle:

```powershell
python scripts/evaluation/validate_asb_bundle.py --bundle-dir .tmp/asb_v1
```

Regenerate only the claim map:

```powershell
python scripts/evaluation/export_setup_claim_map.py --bundle-dir .tmp/asb_v1
```

## Generated Output Policy

Generated ASB bundles should be written under `.tmp/` for local validation. Commit scenario assets, scripts, modules, tests, and documentation; do not commit generated `.tmp/asb_v1` outputs unless a future release process explicitly promotes a baseline artifact.

## Artifact Contract

The validator expects the following generated artifacts:

- `bundle.json`
- `manifest.json`
- `dataset-manifest.json`
- `model-manifest.json`
- `cost-provenance.json`
- `catalog-topology.json`
- `topology-metrics.csv`
- `grid-search.csv`
- `holdout.csv`
- `pareto.csv`
- `qlst-scalar.csv`
- `qlst-multivariate.csv`
- `falsification.csv`
- `claim-map.yaml`

## Architecture Notes

The ASB implementation is additive under the evaluation framework. It uses data-oriented Pydantic contracts for bundle state and a small Strategy seam for cost sources: `SyntheticCostSource` for reproducible public-safe local runs and `TelemetryCostSource` for future redacted telemetry-derived runs. The deterministic runner keeps cloud-hosted Foundry evaluation as an optional overlay rather than a reproducibility requirement.
