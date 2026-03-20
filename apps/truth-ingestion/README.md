# Truth Ingestion

## Purpose
Ingests source product payloads into truth-layer processing workflows.

## Responsibilities
- Ingest single and bulk product payloads.
- Trigger and track sync jobs.
- Process source webhooks into ingestion flows.

## Key endpoints or interfaces
- `POST /invoke` for synchronous agent requests.
- `POST /ingest/product`, `POST /ingest/bulk`, and `POST /ingest/sync` for ingestion operations.
- `GET /ingest/status/{job_id}` for job status.
- `POST /ingest/webhook` for source webhook ingestion.
- Event Hub subscription: `ingest-jobs`.

## Run/Test commands
```bash
cd apps/truth-ingestion/src
uv sync
uv run uvicorn truth_ingestion.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
