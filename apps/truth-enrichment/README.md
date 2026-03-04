# Truth Enrichment Service

AI-powered product attribute enrichment service. Consumes `enrichment-jobs` from Event Hub, uses Azure AI Foundry to generate missing attribute values, and writes proposed attributes for HITL review.

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
