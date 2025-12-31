# Ecommerce Catalog Search Service

Standalone FastAPI + MCP service exposing catalog search capabilities using the shared micro-framework.

## Run locally

```bash
pip install -e .[test]
uvicorn ecommerce_catalog_search.main:app --reload
```

## Tests

```bash
pytest
```

## Endpoints
- `GET /health`
- `POST /invoke`
