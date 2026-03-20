"""Export engine — orchestrates protocol-mapped product exports."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.adapters.ucp_mapper import UcpProtocolMapper
from holiday_peak_lib.integrations import PIMWritebackManager, WritebackResult, WritebackStatus

from .schemas_compat import AuditAction, AuditEvent, ExportResult


class ExportEngine:
    """Applies the correct :class:`ProtocolMapper` and returns an
    :class:`ExportResult`.

    The engine is intentionally stateless — callers supply the product,
    attributes, and mapping config; the engine selects the mapper, runs the
    transform, validates the output, and writes an audit event.
    """

    _MAPPERS = {
        "acp": AcpCatalogMapper(),
        "ucp": UcpProtocolMapper(),
    }

    def export(
        self,
        job_id: str,
        product: Any,
        attributes: list[Any],
        protocol: str,
        mapping: dict[str, Any] | None = None,
        *,
        partner_id: str | None = None,
    ) -> Any:
        """Run the export pipeline for a single product.

        Args:
            job_id: Identifier for the export job (for audit correlation).
            product: Canonical product style from the truth store.
            attributes: Approved truth attributes for the product.
            protocol: Target protocol name (``"acp"`` or ``"ucp"``).
            mapping: Field-mapping config (loaded from Cosmos).  Defaults to
                an empty dict when not supplied.
            partner_id: Optional partner identifier for ACP policy filtering.

        Returns:
            An :class:`ExportResult` with the serialised payload.
        """
        _ = partner_id
        protocol_lower = protocol.lower()
        mapper = self._MAPPERS.get(protocol_lower)
        if mapper is None:
            return ExportResult(
                jobId=job_id,
                entityId=product.id,
                protocol=protocol,
                status="failed",
                errors=[f"Unsupported protocol: {protocol!r}"],
            )

        effective_mapping: dict[str, Any] = mapping or {}
        payload = mapper.map(product, attributes, effective_mapping)

        protocol_version = str(effective_mapping.get("protocol_version", "1.0"))
        valid = mapper.validate_output(payload, protocol_version)

        return ExportResult(
            jobId=job_id,
            entityId=product.id,
            protocol=protocol_lower,
            status="completed" if valid else "invalid",
            payload=payload,
            errors=[] if valid else ["Output failed protocol validation"],
        )

    def build_audit_event(
        self,
        job_id: str,
        product: Any,
        protocol: str,
        actor: str = "truth-export",
    ) -> Any:
        """Create an :class:`AuditEvent` for a completed export."""
        return AuditEvent(
            entityId=product.id,
            action=AuditAction.EXPORTED,
            actor=actor,
            timestamp=datetime.now(timezone.utc),
            details={"job_id": job_id, "protocol": protocol},
        )

    def supported_protocols(self) -> list[str]:
        """Return the names of all registered protocol mappers."""
        return list(self._MAPPERS.keys())

    async def writeback_entity(
        self,
        manager: PIMWritebackManager,
        entity_id: str,
        *,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Execute PIM writeback for a single entity.

        This command-style method is reused by REST routes and event handlers.
        """
        result = await (
            manager.dry_run(entity_id) if dry_run else manager.writeback_product(entity_id)
        )
        summary = result.model_dump()
        summary["dry_run"] = dry_run
        summary["status"] = self._resolve_writeback_status(summary)
        summary["pim_response_summary"] = self._build_pim_response_summary(summary)
        return summary

    async def writeback_to_pim(
        self,
        manager: PIMWritebackManager,
        truth_store: Any,
        entity_id: str,
        *,
        approved_attributes: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Write back approved attributes only, preserving manager safety guards."""
        if not approved_attributes:
            return await self.writeback_entity(manager, entity_id, dry_run=dry_run)

        approved_set = {field for field in approved_attributes if field}
        if dry_run:
            preview = await self.writeback_entity(manager, entity_id, dry_run=True)
            return self._filter_writeback_summary(preview, approved_set)

        raw_attributes = await truth_store.get_attributes(entity_id)
        selected = [
            attr
            for attr in raw_attributes
            if attr.get("field") in approved_set and attr.get("writeback_eligible", False)
        ]

        if not selected:
            skipped_summary: dict[str, Any] = {
                "entity_id": entity_id,
                "total": 0,
                "succeeded": 0,
                "skipped": 0,
                "conflicts": 0,
                "errors": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "results": [],
                "dry_run": False,
                "status": "skipped",
            }
            skipped_summary["pim_response_summary"] = self._build_pim_response_summary(
                skipped_summary
            )
            return skipped_summary

        async def _write_one(attr: dict[str, Any]) -> WritebackResult:
            return await manager.writeback_attribute(
                entity_id,
                field=str(attr.get("field")),
                value=attr.get("value"),
                truth_version=attr.get("version"),
            )

        results = list(await asyncio.gather(*[_write_one(attr) for attr in selected]))
        summary = self._summarize_field_results(entity_id, results, dry_run=False)
        summary["status"] = self._resolve_writeback_status(summary)
        summary["pim_response_summary"] = self._build_pim_response_summary(summary)
        return summary

    async def writeback_batch(
        self,
        manager: PIMWritebackManager,
        entity_ids: list[str],
        *,
        dry_run: bool = False,
        max_concurrency: int = 5,
    ) -> list[dict[str, Any]]:
        """Execute batched writeback with bounded concurrency."""
        semaphore = asyncio.Semaphore(max(1, max_concurrency))

        async def _run_one(entity_id: str) -> dict[str, Any]:
            async with semaphore:
                return await self.writeback_entity(manager, entity_id, dry_run=dry_run)

        tasks = [_run_one(entity_id) for entity_id in entity_ids]
        return list(await asyncio.gather(*tasks))

    def build_writeback_audit_event(
        self,
        *,
        entity_id: str,
        result: dict[str, Any],
        trigger: str,
        actor: str = "truth-export",
    ) -> AuditEvent:
        """Create an audit event for a PIM writeback execution."""
        return AuditEvent(
            entityId=entity_id,
            action=AuditAction.EXPORTED,
            actor=actor,
            timestamp=datetime.now(timezone.utc),
            details={
                "trigger": trigger,
                "writeback_status": result.get("status"),
                "dry_run": result.get("dry_run", False),
                "pim_response_summary": result.get("pim_response_summary", {}),
                "writeback_timestamp": result.get("timestamp"),
            },
        )

    @staticmethod
    def _resolve_writeback_status(result: dict[str, Any]) -> str:
        if result.get("errors", 0) > 0:
            return "failed"
        if result.get("conflicts", 0) > 0:
            return "conflict"
        if result.get("succeeded", 0) > 0:
            return "completed"
        return "skipped"

    @staticmethod
    def _build_pim_response_summary(result: dict[str, Any]) -> dict[str, Any]:
        messages = []
        for item in result.get("results", []):
            field = item.get("field")
            status = item.get("status")
            message = item.get("message")
            messages.append({"field": field, "status": status, "message": message})
        return {
            "total": result.get("total", 0),
            "succeeded": result.get("succeeded", 0),
            "skipped": result.get("skipped", 0),
            "conflicts": result.get("conflicts", 0),
            "errors": result.get("errors", 0),
            "messages": messages,
        }

    def _summarize_field_results(
        self,
        entity_id: str,
        field_results: list[WritebackResult],
        *,
        dry_run: bool,
    ) -> dict[str, Any]:
        succeeded = 0
        skipped = 0
        conflicts = 0
        errors = 0
        result_items: list[dict[str, Any]] = []

        for item in field_results:
            status = item.status
            if status == WritebackStatus.SUCCESS:
                succeeded += 1
            elif status in (WritebackStatus.SKIPPED, WritebackStatus.DRY_RUN):
                skipped += 1
            elif status == WritebackStatus.CONFLICT:
                conflicts += 1
            else:
                errors += 1
            result_items.append(item.model_dump())

        return {
            "entity_id": entity_id,
            "total": len(field_results),
            "succeeded": succeeded,
            "skipped": skipped,
            "conflicts": conflicts,
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "results": result_items,
            "dry_run": dry_run,
        }

    def _filter_writeback_summary(
        self,
        summary: dict[str, Any],
        approved_set: set[str],
    ) -> dict[str, Any]:
        filtered_results = [
            result for result in summary.get("results", []) if result.get("field") in approved_set
        ]
        filtered = dict(summary)
        filtered["results"] = filtered_results
        filtered["total"] = len(filtered_results)
        filtered["succeeded"] = len(
            [r for r in filtered_results if r.get("status") == WritebackStatus.SUCCESS.value]
        )
        filtered["skipped"] = len(
            [
                r
                for r in filtered_results
                if r.get("status") in {WritebackStatus.SKIPPED.value, WritebackStatus.DRY_RUN.value}
            ]
        )
        filtered["conflicts"] = len(
            [r for r in filtered_results if r.get("status") == WritebackStatus.CONFLICT.value]
        )
        filtered["errors"] = len(
            [r for r in filtered_results if r.get("status") == WritebackStatus.ERROR.value]
        )
        filtered["status"] = self._resolve_writeback_status(filtered)
        filtered["pim_response_summary"] = self._build_pim_response_summary(filtered)
        return filtered
