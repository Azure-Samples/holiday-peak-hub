"""REST routes for the Truth Ingestion service."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from .adapters import (
    IngestionAdapters,
    build_ingestion_adapters,
    ingest_bulk_products,
    ingest_single_product,
)

router = APIRouter(prefix="/ingest", tags=["ingestion"])

# Module-level adapter instance (replaced in tests via dependency injection)
_adapters: Optional[IngestionAdapters] = None


def get_adapters() -> IngestionAdapters:
    global _adapters  # noqa: PLW0603
    if _adapters is None:
        _adapters = build_ingestion_adapters()
    return _adapters


def set_adapters(adapters: IngestionAdapters) -> None:
    """Allow test fixtures to inject mock adapters."""
    global _adapters  # noqa: PLW0603
    _adapters = adapters


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class IngestProductRequest(BaseModel):
    """Request body for single product ingestion."""

    product: dict[str, Any] = Field(..., description="Raw PIM product payload")
    field_mapping: Optional[dict[str, str]] = Field(
        default=None,
        description="Optional field name overrides (canonical → source field name)",
    )


class BulkIngestRequest(BaseModel):
    """Request body for bulk product ingestion."""

    products: list[dict[str, Any]] = Field(..., min_length=1)
    field_mapping: Optional[dict[str, str]] = None
    concurrency: int = Field(default=5, ge=1, le=50)


class SyncRequest(BaseModel):
    """Request body for a full PIM sync."""

    max_pages: int = Field(default=100, ge=1, le=1000)
    page_size: int = Field(default=100, ge=1, le=500)
    concurrency: int = Field(default=5, ge=1, le=50)
    field_mapping: Optional[dict[str, str]] = None


class WebhookPayload(BaseModel):
    """Generic PIM webhook notification."""

    event_type: str
    entity_id: Optional[str] = None
    data: Optional[dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Job tracking (in-memory for lightweight services; replace with Redis/Cosmos)
# ---------------------------------------------------------------------------


_jobs: dict[str, dict[str, Any]] = {}


def _new_job(job_type: str) -> str:
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"job_id": job_id, "type": job_type, "status": "pending", "result": None}
    return job_id


def _update_job(job_id: str, status: str, result: Any = None) -> None:
    if job_id in _jobs:
        _jobs[job_id]["status"] = status
        _jobs[job_id]["result"] = result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/product")
async def ingest_product(request: IngestProductRequest) -> dict[str, Any]:
    """Ingest a single product from a PIM payload."""
    adapters = get_adapters()
    try:
        result = await ingest_single_product(
            request.product,
            adapters,
            field_mapping=request.field_mapping,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok", "result": result}


@router.post("/bulk")
async def ingest_bulk(request: BulkIngestRequest) -> dict[str, Any]:
    """Ingest multiple products in a single batch call."""
    adapters = get_adapters()
    try:
        results = await ingest_bulk_products(
            request.products,
            adapters,
            concurrency=request.concurrency,
            field_mapping=request.field_mapping,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    errors = [r for r in results if "error" in r]
    return {
        "status": "ok",
        "total": len(results),
        "succeeded": len(results) - len(errors),
        "failed": len(errors),
        "results": results,
    }


@router.post("/sync")
async def trigger_sync(
    request: SyncRequest,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """Trigger a full paginated PIM sync in the background."""
    job_id = _new_job("sync")
    adapters = get_adapters()

    async def _run_sync() -> None:
        try:
            all_products = await adapters.pim.fetch_all_products(max_pages=request.max_pages)
            if all_products:
                results = await ingest_bulk_products(
                    all_products,
                    adapters,
                    concurrency=request.concurrency,
                    field_mapping=request.field_mapping,
                )
                _update_job(job_id, "completed", {"count": len(results), "results": results})
            else:
                _update_job(job_id, "completed", {"count": 0, "results": []})
        except Exception as exc:  # noqa: BLE001
            _update_job(job_id, "failed", {"error": str(exc)})

    background_tasks.add_task(_run_sync)
    return {"status": "accepted", "job_id": job_id}


@router.get("/status/{job_id}")
async def get_job_status(job_id: str) -> dict[str, Any]:
    """Check the status of an ingestion job."""
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    return job


@router.post("/webhook")
async def receive_webhook(payload: WebhookPayload) -> dict[str, Any]:
    """Receive and process a PIM webhook notification."""
    adapters = get_adapters()
    event_type = payload.event_type
    entity_id = payload.entity_id
    data = payload.data or {}

    if event_type in {"product.created", "product.updated"} and (data or entity_id):
        product_data = {**data}
        if entity_id:
            product_data.setdefault("id", entity_id)
        if not product_data:
            return {"status": "skipped", "reason": "empty data payload"}
        try:
            result = await ingest_single_product(product_data, adapters)
            return {"status": "processed", "entity_id": result.get("entity_id")}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "skipped", "event_type": event_type}
