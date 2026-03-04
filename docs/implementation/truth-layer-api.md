# Truth Layer API Reference

This document describes currently available truth-layer endpoints and planned service contracts for the ingestion → completeness → enrichment → review → export workflow.

## Scope and Current Status

- Implemented services in the current repo/deployment topology:
  - `truth-ingestion` (custom REST ingestion routes + standard service endpoints)
  - `product-management-consistency-validation` (legacy `/invoke` + event-driven completeness engine)
  - `ecommerce-product-detail-enrichment` (enrichment via `/invoke`)
  - `product-management-acp-transformation` (ACP export via `/invoke`)
  - `crud-service` (transactional APIs, including review endpoints used as interim review flow)
- Deployment behavior: `truth-ingestion` is included in the same `deploy-azd` agent service matrix path as other agent services.
- Planned but not yet delivered as standalone services in this repository:
  - dedicated Truth HITL service
  - dedicated Truth Export service for protocol variants beyond ACP

## Authentication

- `crud-service` endpoints under `/api/auth`, `/api/users`, `/api/reviews` may require bearer auth depending on route and user role.
- Agent services (`truth-ingestion`, `...-enrichment`, `...-consistency-validation`, `...-acp-transformation`) typically expose:
  - `GET /health`
  - `GET /ready`
  - `POST /invoke`
  - optional `/mcp/*` endpoints registered per service
- For APIM deployments, service routes are exposed using:
  - `/agents/<service-name>/health`
  - `/agents/<service-name>/invoke`
  - `/agents/<service-name>/mcp/{tool}`

## Common Error Model

- `400`: invalid request payload
- `401` / `403`: missing or insufficient auth
- `404`: resource not found
- `422`: validation error
- `500`: internal service error
- `503`: readiness/foundry precondition not satisfied

## Rate Limiting

- Ingestion path uses connector-level throttling for upstream PIM calls (`GenericRestPIMConnector` token bucket + retry/backoff for `429`/`5xx`).
- API gateway-level throttling can be applied in APIM; this repo does not hardcode per-route rate limiting in FastAPI routers.

## Endpoint Reference

## 1) Truth Ingestion Service

Base URL: `http://<truth-ingestion-host>`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness |
| GET | `/integrations` | Registered integration health summary |
| POST | `/invoke` | Agent invocation (`action`: `ingest_single`, `ingest_bulk`, `get_status`) |
| POST | `/ingest/product` | Ingest one product payload |
| POST | `/ingest/bulk` | Bulk ingest payload list |
| POST | `/ingest/sync` | Async full sync job trigger |
| GET | `/ingest/status/{job_id}` | Job status lookup |
| POST | `/ingest/webhook` | PIM webhook ingestion |

### Example request: `POST /ingest/product`

```json
{
  "product": {
    "id": "prd-001",
    "sku": "prd-001",
    "title": "Trail Running Shoes",
    "brand": "PeakSport",
    "category_id": "footwear",
    "description": "Lightweight trail shoe"
  }
}
```

## 2) Completeness (Consistency Validation)

Base URL: `http://<consistency-host>`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness |
| POST | `/invoke` | Legacy consistency/completeness validation |

### Event-driven completeness flow (implemented)

- **Consumes**: Event Hub topic `completeness-jobs` (consumer group: `completeness-engine`)
- **Loads**: product + category schema
- **Evaluates**: weighted completeness score and field-level gaps
- **Stores**: gap report via completeness storage adapter (Cosmos-backed with local/test fallback)
- **Publishes**: `enrichment_requested` to `enrichment-jobs` when:
  - completeness score `< COMPLETENESS_THRESHOLD` (default `0.7`)
  - enrichable gaps are present

### Completeness report model highlights

- `entity_id`, `category_id`, `schema_version`
- `completeness_score` (`0.0`–`1.0`)
- `gaps[]` with gap type (`missing` / `invalid`)
- `enrichable_gaps[]`

### Example request: `POST /invoke` (completeness)

```json
{
  "sku": "prd-001"
}
```

## 3) Enrichment Service

Base URL: `http://<enrichment-host>`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness |
| POST | `/invoke` | Enrich product detail context by SKU |

### Example request: `POST /invoke` (enrichment)

```json
{
  "sku": "prd-001",
  "related_limit": 4
}
```

## 4) Review / HITL

- Dedicated Truth HITL service endpoints are planned but not currently present in this repository.
- Current interim review APIs are available on CRUD service:

Base URL: `http://<crud-host>`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/api/reviews?product_id=<id>` | List product reviews |
| POST | `/api/reviews` | Create review (auth required) |
| DELETE | `/api/reviews/{review_id}` | Delete review (author/admin) |

## 5) Export Service

Base URL: `http://<acp-transformation-host>`

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness |
| POST | `/invoke` | Export SKU as ACP payload |

### Example request: `POST /invoke` (export)

```json
{
  "sku": "prd-001",
  "availability": "in_stock",
  "currency": "usd"
}
```

## 6) CRUD Endpoints Used in Truth Workflows

Base URL: `http://<crud-host>`

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | CRUD service liveness |
| GET | `/ready` | CRUD readiness |
| GET | `/api/products` | Product retrieval for validation/export |
| GET | `/api/products/{product_id}` | Product detail |
| GET | `/api/categories` | Category metadata |
| GET | `/api/orders` | Operational workflow context |

## Example End-to-End Workflow

1. Ingest product:
   - `POST /ingest/product`
2. Run completeness validation:
   - `POST <consistency>/invoke` with SKU
3. Enrich product details:
   - `POST <enrichment>/invoke` with SKU
4. Review workflow:
   - Use CRUD review endpoints (current) or dedicated HITL service (planned)
5. Export:
   - `POST <acp-transformation>/invoke`

## Sample Automation Scripts

- [samples/scripts/ingest_sample.py](../../samples/scripts/ingest_sample.py)
- [samples/scripts/bulk_ingest.py](../../samples/scripts/bulk_ingest.py)
- [samples/scripts/review_workflow.py](../../samples/scripts/review_workflow.py)
- [samples/scripts/export_demo.py](../../samples/scripts/export_demo.py)

## Postman Collection

- [samples/postman/truth-layer.postman_collection.json](../../samples/postman/truth-layer.postman_collection.json)
