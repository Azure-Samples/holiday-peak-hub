# Truth HITL

## Purpose
Provides human-in-the-loop review workflows for truth-layer proposed attributes.

## Responsibilities
- Expose pending review queue operations.
- Process approve/reject/edit decisions.
- Support batch review actions and queue metrics.

## Key endpoints or interfaces
- `POST /invoke` for synchronous agent requests.
- `GET /review/queue`, `GET /review/stats`, and `GET /review/{entity_id}` for review retrieval.
- `POST /review/{entity_id}/approve`, `POST /review/{entity_id}/reject`, `POST /review/{entity_id}/edit` for decisions.
- `POST /review/approve/batch` and `POST /review/reject/batch` for bulk decisions.
- Event Hub subscription: `hitl-jobs`.

## Run/Test commands
```bash
cd apps/truth-hitl/src
uv sync
uv run uvicorn truth_hitl.main:app --reload
python -m pytest ../tests
```

## Configuration notes
- Uses Foundry model settings (`PROJECT_ENDPOINT` or `FOUNDRY_ENDPOINT`, fast/rich model identifiers).
- Supports Redis/Cosmos/Blob memory configuration via shared memory settings.
- Requires Event Hub namespace and consumer configuration for background jobs.
