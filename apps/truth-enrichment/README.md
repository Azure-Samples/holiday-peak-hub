# Truth Enrichment Service

AI-powered product attribute enrichment service. Consumes `enrichment-jobs` from Event Hub, performs PIM schema gap detection (required + optional attributes), analyzes DAM images, and generates enrichment proposals for HITL review.

## Enrichment Pipeline

1. Read product and category schema.
2. Detect missing attributes using the full schema (`required` + `optional`).
3. Retrieve DAM assets and run vision analysis per missing field.
4. Run text enrichment when model routing is available.
5. Merge image + text evidence into a proposal with `source_type`, `source_assets`, `original_data`, `enriched_data`, and `reasoning`.
6. Store proposed attributes, append audit events, and publish pending items to `hitl-jobs`.

## Run

```bash
pip install -e .[test]
uvicorn truth_enrichment.main:app --reload
```

## Tests

```bash
pytest
```

## Key Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/enrich/product/{entity_id}` | Trigger on-demand enrichment |
| POST | `/enrich/field` | Enrich a specific field for a product |
| GET | `/enrich/status/{job_id}` | Check enrichment job status |
