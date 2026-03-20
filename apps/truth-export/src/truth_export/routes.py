"""REST routes for the truth-export service."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .adapters import TruthExportAdapters, build_truth_export_adapters
from .export_engine import ExportEngine

router = APIRouter(prefix="/export", tags=["export"])

# Module-level singletons (overridden in tests via dependency injection)
_engine = ExportEngine()
_adapters: TruthExportAdapters = build_truth_export_adapters()


def get_engine() -> ExportEngine:
    return _engine


def get_adapters() -> TruthExportAdapters:
    return _adapters


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class BulkExportRequest(BaseModel):
    entity_ids: list[str]
    protocol: str = "ucp"
    partner_id: str | None = None


class PIMWritebackRequest(BaseModel):
    dry_run: bool = False
    trigger: str = "api"
    approved_fields: list[str] | None = None


class PIMBatchWritebackRequest(BaseModel):
    entity_ids: list[str] = Field(min_length=1, max_length=100)
    dry_run: bool = False
    max_concurrency: int = Field(default=5, ge=1, le=20)
    approved_fields: list[str] | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/acp/{entity_id}")
async def export_acp(
    entity_id: str,
    partner_id: str | None = None,
    engine: ExportEngine = Depends(get_engine),
    adapters: TruthExportAdapters = Depends(get_adapters),
) -> dict[str, Any]:
    """Export a product as ACP format."""
    return await _run_export(entity_id, "acp", engine, adapters, partner_id=partner_id)


@router.post("/ucp/{entity_id}")
async def export_ucp(
    entity_id: str,
    engine: ExportEngine = Depends(get_engine),
    adapters: TruthExportAdapters = Depends(get_adapters),
) -> dict[str, Any]:
    """Export a product as UCP format."""
    return await _run_export(entity_id, "ucp", engine, adapters)


@router.post("/bulk")
async def export_bulk(
    request: BulkExportRequest,
    engine: ExportEngine = Depends(get_engine),
    adapters: TruthExportAdapters = Depends(get_adapters),
) -> dict[str, Any]:
    """Bulk-export a list of products in the requested protocol."""
    results = []
    for entity_id in request.entity_ids:
        result = await _run_export(
            entity_id,
            request.protocol,
            engine,
            adapters,
            partner_id=request.partner_id,
        )
        results.append(result)
    return {"protocol": request.protocol, "count": len(results), "results": results}


@router.post("/pim/batch")
async def export_pim_batch(
    request: PIMBatchWritebackRequest,
    engine: ExportEngine = Depends(get_engine),
    adapters: TruthExportAdapters = Depends(get_adapters),
) -> dict[str, Any]:
    """Push approved truth attributes for up to 100 entities back to PIM."""
    if len(request.entity_ids) > 100:
        raise HTTPException(status_code=400, detail="Batch size cannot exceed 100 entities")

    if request.approved_fields:
        semaphore = asyncio.Semaphore(max(1, request.max_concurrency))

        async def _run_one(entity_id: str) -> dict[str, Any]:
            async with semaphore:
                return await engine.writeback_to_pim(
                    adapters.writeback_manager,
                    adapters.truth_store,
                    entity_id,
                    approved_attributes=request.approved_fields,
                    dry_run=request.dry_run,
                )

        results = list(
            await asyncio.gather(*[_run_one(entity_id) for entity_id in request.entity_ids])
        )
    else:
        results = await engine.writeback_batch(
            adapters.writeback_manager,
            request.entity_ids,
            dry_run=request.dry_run,
            max_concurrency=request.max_concurrency,
        )

    for entity_result in results:
        await adapters.truth_store.save_export_result(entity_result)
        audit_event = engine.build_writeback_audit_event(
            entity_id=str(entity_result.get("entity_id")),
            result=entity_result,
            trigger="api:batch",
        )
        await adapters.truth_store.save_audit_event(audit_event.model_dump())

    return {
        "count": len(results),
        "dry_run": request.dry_run,
        "max_concurrency": request.max_concurrency,
        "results": results,
    }


@router.post("/pim/{entity_id}")
async def export_pim_single(
    entity_id: str,
    request: PIMWritebackRequest,
    engine: ExportEngine = Depends(get_engine),
    adapters: TruthExportAdapters = Depends(get_adapters),
) -> dict[str, Any]:
    """Push approved truth attributes for one entity back to source PIM."""
    result = await engine.writeback_entity(
        adapters.writeback_manager,
        entity_id,
        dry_run=request.dry_run,
    )
    if request.approved_fields:
        result = await engine.writeback_to_pim(
            adapters.writeback_manager,
            adapters.truth_store,
            entity_id,
            approved_attributes=request.approved_fields,
            dry_run=request.dry_run,
        )
    await adapters.truth_store.save_export_result(result)
    audit_event = engine.build_writeback_audit_event(
        entity_id=entity_id,
        result=result,
        trigger=request.trigger,
    )
    await adapters.truth_store.save_audit_event(audit_event.model_dump())
    return result


@router.get("/status/{job_id}")
async def export_status(
    job_id: str,
    adapters: TruthExportAdapters = Depends(get_adapters),
) -> dict[str, Any]:
    """Check the status of an export job."""
    job = adapters.job_tracker.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Export job {job_id!r} not found")
    return job


@router.get("/protocols")
async def list_protocols(
    engine: ExportEngine = Depends(get_engine),
) -> dict[str, Any]:
    """List supported export protocols."""
    return {"protocols": engine.supported_protocols()}


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


async def _run_export(
    entity_id: str,
    protocol: str,
    engine: ExportEngine,
    adapters: TruthExportAdapters,
    *,
    partner_id: str | None = None,
) -> dict[str, Any]:
    product = await adapters.truth_store.get_product_style(entity_id)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product {entity_id!r} not found")

    attributes = await adapters.truth_store.get_truth_attributes(entity_id)
    mapping = await adapters.truth_store.get_protocol_mapping(protocol)

    job_id = adapters.job_tracker.create(entity_id, protocol, partner_id)

    result = engine.export(
        job_id=job_id,
        product=product,
        attributes=attributes,
        protocol=protocol,
        mapping=mapping,
        partner_id=partner_id,
    )

    await adapters.truth_store.save_export_result(result.model_dump())

    audit = engine.build_audit_event(job_id, product, protocol)
    await adapters.truth_store.save_audit_event(audit.model_dump())

    adapters.job_tracker.update(job_id, result.status)
    return result.model_dump()
