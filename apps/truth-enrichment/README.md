# Truth Enrichment

## Purpose
Generates proposed truth-layer attribute enrichments for products.

## Responsibilities
- Detect enrichable product attribute gaps.
- Generate candidate attribute values.
- Persist and expose enrichment job status.

## Key endpoints or interfaces
- `POST /invoke` for synchronous agent requests.
- `POST /enrich/product/{entity_id}` to enrich a product.
- `POST /enrich/field` to enrich a specific field.
- `GET /enrich/status/{job_id}` to read enrichment status.
- Event Hub subscription: `enrichment-jobs`.

## Run/Test commands
```bash
cd apps/truth-enrichment/src
uv sync
uv run uvicorn truth_enrichment.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
