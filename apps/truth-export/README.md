# Truth Export

## Purpose
Exports approved truth-layer product attributes to downstream protocols and systems.

## Responsibilities
- Export truth attributes as ACP/UCP payloads.
- Support batch export and PIM writeback operations.
- Track export job and protocol status.

## Key endpoints or interfaces
- `POST /invoke` for synchronous agent requests.
- `POST /export/acp/{entity_id}` and `POST /export/ucp/{entity_id}` for protocol export.
- `POST /export/bulk`, `POST /export/pim/{entity_id}`, and `POST /export/pim/batch` for batch/writeback.
- `GET /export/status/{job_id}` and `GET /export/protocols` for status/capabilities.
- Event Hub subscription: `export-jobs`.

## Run/Test commands
```bash
cd apps/truth-export/src
uv sync
uv run uvicorn truth_export.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
