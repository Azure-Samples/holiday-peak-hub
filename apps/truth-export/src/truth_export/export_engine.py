"""Export engine — orchestrates protocol-mapped product exports."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from holiday_peak_lib.adapters.acp_mapper import AcpCatalogMapper
from holiday_peak_lib.adapters.ucp_mapper import UcpProtocolMapper

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
