"""Adapters for the truth-export service."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from holiday_peak_lib.integrations import (
    PIMConnectionConfig,
    PIMWritebackManager,
    ProductData,
    TenantConfig,
)
from holiday_peak_lib.integrations.pim_generic_rest import GenericRestPIMConnector

from .schemas_compat import ProductStyle, TruthAttribute


@dataclass
class MockTruthStoreAdapter:
    """In-memory stub that simulates the Cosmos DB truth store.

    Replace with a real Cosmos DB adapter in production environments.
    """

    _styles: dict[str, ProductStyle] = field(default_factory=dict)
    _attributes: dict[str, list[TruthAttribute]] = field(default_factory=dict)
    _results: list[dict[str, Any]] = field(default_factory=list)
    _audit_events: list[dict[str, Any]] = field(default_factory=list)
    _protocol_mappings: dict[str, dict[str, Any]] = field(default_factory=dict)

    async def get_product_style(self, style_id: str) -> ProductStyle | None:
        return self._styles.get(style_id)

    async def get_truth_attributes(self, style_id: str) -> list[TruthAttribute]:
        return self._attributes.get(style_id, [])

    async def get_protocol_mapping(self, _protocol: str) -> dict[str, Any]:
        """Return a stub field-mapping config for *protocol*."""
        protocol = _protocol.lower()
        if protocol in self._protocol_mappings:
            return self._protocol_mappings[protocol]
        return {"protocol_version": "1.0"}

    async def get_attributes(self, style_id: str) -> list[dict[str, Any]]:
        attrs = await self.get_truth_attributes(style_id)
        return [
            {
                "field": attr.attribute_key,
                "value": attr.value,
                "version": self._extract_attr_version(attr),
                "writeback_eligible": True,
            }
            for attr in attrs
        ]

    async def save_export_result(self, result: dict[str, Any]) -> None:
        self._results.append(result)

    async def save_audit_event(self, event: dict[str, Any]) -> None:
        self._audit_events.append(event)

    @staticmethod
    def _extract_attr_version(attr: TruthAttribute) -> str | None:
        raw_timestamp = getattr(attr, "updated_at", None) or getattr(attr, "timestamp", None)
        if raw_timestamp is None:
            return None
        if isinstance(raw_timestamp, datetime):
            return raw_timestamp.isoformat()
        return str(raw_timestamp)

    # ------------------------------------------------------------------
    # Seeding helpers (useful in tests)
    # ------------------------------------------------------------------

    def seed_style(self, style: ProductStyle) -> None:
        self._styles[style.id] = style

    def seed_attributes(self, style_id: str, attributes: list[TruthAttribute]) -> None:
        self._attributes[style_id] = attributes

    def seed_protocol_mapping(self, protocol: str, mapping: dict[str, Any]) -> None:
        self._protocol_mappings[protocol.lower()] = dict(mapping)


@dataclass
class AuditStoreAdapter:
    """Adapter exposing the audit contract required by PIM writeback manager."""

    truth_store: MockTruthStoreAdapter

    async def record(self, entry: dict[str, Any]) -> None:
        await self.truth_store.save_audit_event(entry)


class GenericPIMWritebackAdapter:
    """Thin adapter that conforms to ``PIMWritebackManager`` expectations."""

    def __init__(self, connector: GenericRestPIMConnector) -> None:
        self._connector = connector

    async def get_product(self, sku: str) -> ProductData | None:
        return await self._connector.fetch_product(sku)

    async def push_enrichment(self, sku: str, field_name: str, value: Any) -> dict[str, Any]:
        product = await self.get_product(sku)
        if product is None:
            product = ProductData(sku=sku, title=sku)
        return await self._connector.push_enrichment(product, {field_name: value})


@dataclass
class ExportJobTracker:
    """In-memory export job status tracker."""

    _jobs: dict[str, dict[str, Any]] = field(default_factory=dict)

    def create(self, entity_id: str, protocol: str, partner_id: str | None = None) -> str:
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = {
            "job_id": job_id,
            "entity_id": entity_id,
            "protocol": protocol,
            "partner_id": partner_id,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        return job_id

    def update(self, job_id: str, status: str, **extra: Any) -> None:
        if job_id in self._jobs:
            self._jobs[job_id]["status"] = status
            self._jobs[job_id].update(extra)

    def get(self, job_id: str) -> dict[str, Any] | None:
        return self._jobs.get(job_id)

    def all_jobs(self) -> list[dict[str, Any]]:
        return list(self._jobs.values())


@dataclass
class TruthExportAdapters:
    """Container for truth-export adapters."""

    truth_store: MockTruthStoreAdapter
    job_tracker: ExportJobTracker
    writeback_manager: PIMWritebackManager


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _default_field_mapping(pim_type: str) -> dict[str, str]:
    connector_type = pim_type.lower()
    if connector_type == "akeneo":
        return {
            "identifier": "sku",
            "values.name": "title",
            "values.description": "description",
            "values.color": "color",
            "updated": "last_modified",
        }
    if connector_type == "salsify":
        return {
            "salsify:id": "sku",
            "salsify:name": "title",
            "salsify:description": "description",
            "salsify:color": "color",
            "salsify:updated_at": "last_modified",
        }
    return {}


def _resolve_field_mapping(pim_type: str) -> dict[str, str]:
    env_mapping = os.getenv("PIM_FIELD_MAPPING_JSON")
    if env_mapping:
        try:
            parsed = json.loads(env_mapping)
            if isinstance(parsed, dict):
                return {str(k): str(v) for k, v in parsed.items()}
        except json.JSONDecodeError:
            return _default_field_mapping(pim_type)
    return _default_field_mapping(pim_type)


def _build_tenant_config() -> TenantConfig:
    fields_raw = (os.getenv("PIM_WRITEBACK_FIELDS") or "").strip()
    fields = [field.strip() for field in fields_raw.split(",") if field.strip()]
    writeback_enabled = _env_bool("PIM_WRITEBACK_ENABLED", _env_bool("TRUTH_WRITEBACK_ENABLED"))
    return TenantConfig(
        tenant_id=os.getenv("PIM_WRITEBACK_TENANT_ID", "default"),
        writeback_enabled=writeback_enabled,
        dry_run=_env_bool("PIM_WRITEBACK_DRY_RUN", default=False),
        rate_limit_per_minute=_env_int("PIM_WRITEBACK_RATE_LIMIT_PER_MINUTE", default=60),
        writeback_fields=fields,
    )


def _build_pim_connector() -> GenericRestPIMConnector:
    pim_type = os.getenv("PIM_CONNECTOR_TYPE", "generic")
    config = PIMConnectionConfig(
        base_url=os.getenv("PIM_BASE_URL", "https://example.invalid"),
        auth_type=os.getenv("PIM_AUTH_TYPE", "bearer"),
        auth_credentials={
            "token": os.getenv("PIM_AUTH_TOKEN", ""),
            "username": os.getenv("PIM_AUTH_USERNAME", ""),
            "password": os.getenv("PIM_AUTH_PASSWORD", ""),
            "header": os.getenv("PIM_AUTH_HEADER", "X-Api-Key"),
            "key": os.getenv("PIM_AUTH_KEY", ""),
            "access_token": os.getenv("PIM_AUTH_ACCESS_TOKEN", ""),
        },
        product_endpoint=os.getenv("PIM_PRODUCT_ENDPOINT", "/api/products"),
        asset_endpoint=os.getenv("PIM_ASSET_ENDPOINT", "/api/assets"),
        category_endpoint=os.getenv("PIM_CATEGORY_ENDPOINT", "/api/categories"),
        search_endpoint=os.getenv("PIM_SEARCH_ENDPOINT", "/api/products/search"),
        field_mapping=_resolve_field_mapping(pim_type),
        page_size=_env_int("PIM_PAGE_SIZE", default=100),
        rate_limit_rps=_env_int("PIM_RATE_LIMIT_RPS", default=10),
        max_retries=_env_int("PIM_MAX_RETRIES", default=3),
        retry_backoff_base=float(os.getenv("PIM_RETRY_BACKOFF_BASE", "0.5")),
        timeout_seconds=float(os.getenv("PIM_TIMEOUT_SECONDS", "30.0")),
    )
    return GenericRestPIMConnector(config)


def build_truth_export_adapters() -> TruthExportAdapters:
    """Create the default adapter bundle for the truth-export service."""
    truth_store = MockTruthStoreAdapter()
    writeback_manager = PIMWritebackManager(
        pim_connector=GenericPIMWritebackAdapter(_build_pim_connector()),
        truth_store=truth_store,
        audit_store=AuditStoreAdapter(truth_store),
        tenant_config=_build_tenant_config(),
    )
    return TruthExportAdapters(
        truth_store=truth_store,
        job_tracker=ExportJobTracker(),
        writeback_manager=writeback_manager,
    )
