"""Fabric-to-Azure-AI-Search ingestion planning and provisioning.

This module stays inside the search-enrichment bounded context because it owns
search document shaping and AI Search publication for catalog retrieval.
"""

# Pylint: keep the bounded-context planning, payload builders, and MCP wrappers
# colocated so existing Fabric ingestion tool paths and mapping contracts stay stable.
# pylint: disable=too-many-lines

from __future__ import annotations

import asyncio
import importlib
import os
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Awaitable, Callable, Mapping, Protocol, Sequence
from uuid import uuid4

import httpx
from azure.core.credentials import AccessToken
from azure.core.credentials_async import AsyncTokenCredential

_SEARCH_API_VERSION = "2026-04-01"
_DEFAULT_INDEX_NAME = "product_search_index"
_DEFAULT_VECTOR_FIELD = "content_vector"
_DEFAULT_SEMANTIC_CONFIG = "catalog-semantic-config"
_DEFAULT_DATASOURCE_NAME = "fabric-product-datasource"
_DEFAULT_SKILLSET_NAME = "fabric-product-skillset"
_DEFAULT_INDEXER_NAME = "fabric-product-indexer"
_DEFAULT_EMBEDDING_MODEL = "text-embedding-3-small"
_DEFAULT_EMBEDDING_DIMENSIONS = 1536
_DEFAULT_SAMPLE_ROWS = 5
_MAX_SAMPLE_ROWS = 50
_TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 504}
_SUPPORTED_SOURCE_KINDS = {"sql", "onelake_files"}


class MCPToolServer(Protocol):
    """Minimal MCP server protocol for registering service-local tools."""

    def add_tool(
        self,
        path: str,
        handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]],
    ) -> None: ...


class FabricSearchIngestionError(RuntimeError):
    """Structured error raised by ingestion planning and provisioning."""

    def __init__(
        self,
        *,
        kind: str,
        message: str,
        operator_action: str | None = None,
        status_code: int = 400,
    ) -> None:
        super().__init__(message)
        self.kind = kind
        self.operator_action = operator_action
        self.status_code = status_code

    def to_response(self, operation: str) -> dict[str, Any]:
        """Return an MCP-safe error response without exposing secrets."""
        error: dict[str, Any] = {
            "kind": self.kind,
            "message": str(self),
        }
        if self.operator_action:
            error["operator_action"] = self.operator_action
        return {
            "status": "error",
            "operation": operation,
            "http_status": self.status_code,
            "error": error,
        }


@dataclass(frozen=True, slots=True)
class FabricSourceSettings:  # pylint: disable=too-many-instance-attributes
    """Environment-backed Fabric source settings.

    Field count mirrors the operator environment contract for Fabric ingestion.
    """

    source_kind: str = "sql"
    sql_endpoint: str | None = None
    sql_database: str | None = None
    sql_schema: str = "dbo"
    sql_table: str | None = None
    sql_connection_string: str | None = None
    workspace_id: str | None = None
    onelake_workspace_endpoint: str | None = None
    onelake_lakehouse_id: str | None = None
    onelake_files_path: str | None = None
    auth_mode: str = "managed_identity"
    incremental_column: str | None = None
    soft_delete_column: str | None = None
    soft_delete_marker: str | None = None
    approval_column: str | None = None
    approval_accepted_values: tuple[str, ...] = ()
    sample_rows: int = _DEFAULT_SAMPLE_ROWS

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "FabricSourceSettings":
        """Load Fabric settings from environment variables."""
        values = environ or os.environ
        source_kind = _clean(values.get("FABRIC_SOURCE_KIND"), "sql").lower()
        accepted_values = _split_csv(values.get("FABRIC_APPROVAL_ACCEPTED_VALUES"))
        return cls(
            source_kind=source_kind,
            sql_endpoint=_optional(values.get("FABRIC_SQL_ENDPOINT")),
            sql_database=_optional(values.get("FABRIC_SQL_DATABASE")),
            sql_schema=_clean(values.get("FABRIC_SQL_SCHEMA"), "dbo"),
            sql_table=_optional(values.get("FABRIC_SQL_TABLE")),
            sql_connection_string=_optional(values.get("FABRIC_SQL_CONNECTION_STRING")),
            workspace_id=_optional(values.get("FABRIC_WORKSPACE_ID")),
            onelake_workspace_endpoint=_optional(values.get("FABRIC_ONELAKE_WORKSPACE_ENDPOINT")),
            onelake_lakehouse_id=_optional(values.get("FABRIC_ONELAKE_LAKEHOUSE_ID")),
            onelake_files_path=_optional(values.get("FABRIC_ONELAKE_FILES_PATH")),
            auth_mode=_clean(values.get("FABRIC_AUTH_MODE"), "managed_identity").lower(),
            incremental_column=_optional(values.get("FABRIC_INCREMENTAL_COLUMN")),
            soft_delete_column=_optional(values.get("FABRIC_SOFT_DELETE_COLUMN")),
            soft_delete_marker=_optional(values.get("FABRIC_SOFT_DELETE_MARKER")),
            approval_column=_optional(values.get("FABRIC_APPROVAL_COLUMN")),
            approval_accepted_values=tuple(accepted_values),
            sample_rows=_bounded_int(
                values.get("FABRIC_SAMPLE_ROWS"),
                default=_DEFAULT_SAMPLE_ROWS,
                minimum=0,
                maximum=_MAX_SAMPLE_ROWS,
            ),
        )

    @property
    def sql_source_name(self) -> str:
        """Return the SQL source label without credentials."""
        parts = [self.sql_database, self.sql_schema, self.sql_table]
        return ".".join(part for part in parts if part)

    def validate(self) -> None:
        """Validate source settings against Fabric and AI Search constraints."""
        if self.source_kind not in _SUPPORTED_SOURCE_KINDS:
            raise FabricSearchIngestionError(
                kind="unsupported_source_kind",
                message=(
                    f"FABRIC_SOURCE_KIND must be one of {sorted(_SUPPORTED_SOURCE_KINDS)}; "
                    f"received {self.source_kind!r}."
                ),
                operator_action=(
                    "Use FABRIC_SOURCE_KIND=sql for Fabric SQL database, warehouse, or SQL "
                    "analytics endpoints; use onelake_files only for lakehouse Files content."
                ),
            )
        if self.source_kind == "sql":
            self._validate_sql()
            return
        self._validate_onelake_files()

    def _validate_sql(self) -> None:
        if self.sql_connection_string:
            return
        missing = [
            name
            for name, value in (
                ("FABRIC_SQL_ENDPOINT", self.sql_endpoint),
                ("FABRIC_SQL_DATABASE", self.sql_database),
                ("FABRIC_SQL_TABLE", self.sql_table),
            )
            if not value
        ]
        if missing:
            raise FabricSearchIngestionError(
                kind="fabric_sql_configuration_missing",
                message=f"Missing Fabric SQL settings: {', '.join(missing)}.",
                operator_action=(
                    "Provide FABRIC_SQL_ENDPOINT, FABRIC_SQL_DATABASE, FABRIC_SQL_TABLE, "
                    "or provide FABRIC_SQL_CONNECTION_STRING for data source provisioning."
                ),
            )

    def _validate_onelake_files(self) -> None:
        missing = [
            name
            for name, value in (("FABRIC_ONELAKE_LAKEHOUSE_ID", self.onelake_lakehouse_id),)
            if not value
        ]
        if not self.workspace_id and not self.onelake_workspace_endpoint:
            missing.append("FABRIC_WORKSPACE_ID or FABRIC_ONELAKE_WORKSPACE_ENDPOINT")
        if missing:
            raise FabricSearchIngestionError(
                kind="fabric_onelake_configuration_missing",
                message=f"Missing OneLake Files settings: {', '.join(missing)}.",
                operator_action=(
                    "Provide a Fabric workspace id or workspace endpoint, a lakehouse id, "
                    "and an optional Files path."
                ),
            )
        _guard_onelake_files_path(self.onelake_files_path)


@dataclass(frozen=True, slots=True)
class AISearchResourceSettings:  # pylint: disable=too-many-instance-attributes
    """Environment-backed Azure AI Search resource settings.

    Field count mirrors the operator environment contract for Search provisioning.
    """

    endpoint: str | None = None
    auth_mode: str = "managed_identity"
    admin_key: str | None = None
    keyword_index_name: str = _DEFAULT_INDEX_NAME
    vector_index_name: str = _DEFAULT_INDEX_NAME
    index_name: str = _DEFAULT_INDEX_NAME
    vector_field: str = _DEFAULT_VECTOR_FIELD
    datasource_name: str = _DEFAULT_DATASOURCE_NAME
    skillset_name: str = _DEFAULT_SKILLSET_NAME
    indexer_name: str = _DEFAULT_INDEXER_NAME
    semantic_config_name: str = _DEFAULT_SEMANTIC_CONFIG
    embedding_resource_uri: str | None = None
    embedding_deployment_name: str | None = None
    embedding_model_name: str = _DEFAULT_EMBEDDING_MODEL
    embedding_dimensions: int = _DEFAULT_EMBEDDING_DIMENSIONS
    api_version: str = _SEARCH_API_VERSION

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "AISearchResourceSettings":
        """Load AI Search settings from environment variables."""
        values = environ or os.environ
        keyword_index = _optional(values.get("AI_SEARCH_INDEX"))
        vector_index = _optional(values.get("AI_SEARCH_VECTOR_INDEX"))
        unified_index = vector_index or keyword_index or _DEFAULT_INDEX_NAME
        return cls(
            endpoint=_optional(values.get("AI_SEARCH_ENDPOINT")),
            auth_mode=_clean(values.get("AI_SEARCH_AUTH_MODE"), "managed_identity").lower(),
            admin_key=_optional(values.get("AI_SEARCH_ADMIN_KEY")),
            keyword_index_name=keyword_index or unified_index,
            vector_index_name=vector_index or unified_index,
            index_name=unified_index,
            vector_field=_clean(values.get("AI_SEARCH_VECTOR_FIELD"), _DEFAULT_VECTOR_FIELD),
            datasource_name=_clean(
                values.get("AI_SEARCH_DATASOURCE_NAME"), _DEFAULT_DATASOURCE_NAME
            ),
            skillset_name=_clean(values.get("AI_SEARCH_SKILLSET_NAME"), _DEFAULT_SKILLSET_NAME),
            indexer_name=_clean(values.get("AI_SEARCH_INDEXER_NAME"), _DEFAULT_INDEXER_NAME),
            semantic_config_name=_clean(
                values.get("AI_SEARCH_SEMANTIC_CONFIG_NAME"), _DEFAULT_SEMANTIC_CONFIG
            ),
            embedding_resource_uri=_optional(values.get("EMBEDDING_RESOURCE_URI")),
            embedding_deployment_name=_optional(values.get("EMBEDDING_DEPLOYMENT_NAME")),
            embedding_model_name=_clean(
                values.get("EMBEDDING_MODEL_NAME"), _DEFAULT_EMBEDDING_MODEL
            ),
            embedding_dimensions=_bounded_int(
                values.get("EMBEDDING_DIMENSIONS"),
                default=_DEFAULT_EMBEDDING_DIMENSIONS,
                minimum=1,
                maximum=4096,
            ),
        )

    def validate_for_resource_build(self) -> None:
        """Validate AI Search settings needed for resource payload construction."""
        if not self.endpoint:
            raise FabricSearchIngestionError(
                kind="ai_search_endpoint_missing",
                message="AI_SEARCH_ENDPOINT is required for provisioning search resources.",
                operator_action="Set AI_SEARCH_ENDPOINT to the target Azure AI Search service URL.",
            )
        if not self.embedding_resource_uri or not self.embedding_deployment_name:
            raise FabricSearchIngestionError(
                kind="embedding_configuration_missing",
                message=(
                    "EMBEDDING_RESOURCE_URI and EMBEDDING_DEPLOYMENT_NAME are required "
                    "for integrated vectorization."
                ),
                operator_action=(
                    "Configure the Azure OpenAI or Foundry embedding resource, deployment, "
                    "model name, and dimensions."
                ),
            )

    def validate_for_provisioning(self) -> None:
        """Validate settings required to call Azure AI Search REST APIs."""
        self.validate_for_resource_build()
        if self.auth_mode in {"api_key", "admin_key", "key"} and not self.admin_key:
            raise FabricSearchIngestionError(
                kind="ai_search_admin_key_missing",
                message="AI_SEARCH_ADMIN_KEY is required when AI_SEARCH_AUTH_MODE uses a key.",
                operator_action=(
                    "Set AI_SEARCH_AUTH_MODE=managed_identity or provide AI_SEARCH_ADMIN_KEY."
                ),
            )

    @property
    def compatibility_warnings(self) -> tuple[str, ...]:
        """Return warnings when catalog-search index env vars are not unified."""
        if self.keyword_index_name == self.vector_index_name:
            return ()
        return (
            "AI_SEARCH_INDEX and AI_SEARCH_VECTOR_INDEX differ. Fabric ingestion builds a "
            "unified hybrid index named by AI_SEARCH_VECTOR_INDEX; set both catalog-search "
            "variables to the same value for a single retrieval index.",
        )


@dataclass(frozen=True, slots=True)
class FabricSearchIngestionSettings:
    """Combined settings for Fabric source and AI Search resources."""

    fabric: FabricSourceSettings
    search: AISearchResourceSettings

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "FabricSearchIngestionSettings":
        """Load all ingestion settings from environment variables."""
        return cls(
            fabric=FabricSourceSettings.from_env(environ),
            search=AISearchResourceSettings.from_env(environ),
        )

    def to_safe_dict(self) -> dict[str, Any]:
        """Return settings metadata with secrets redacted."""
        return {
            "fabric": {
                "source_kind": self.fabric.source_kind,
                "sql_endpoint_configured": bool(self.fabric.sql_endpoint),
                "sql_database": self.fabric.sql_database,
                "sql_schema": self.fabric.sql_schema,
                "sql_table": self.fabric.sql_table,
                "sql_connection_string_configured": bool(self.fabric.sql_connection_string),
                "workspace_id_configured": bool(self.fabric.workspace_id),
                "onelake_workspace_endpoint_configured": bool(
                    self.fabric.onelake_workspace_endpoint
                ),
                "onelake_lakehouse_id": self.fabric.onelake_lakehouse_id,
                "onelake_files_path": self.fabric.onelake_files_path,
                "auth_mode": self.fabric.auth_mode,
                "incremental_column": self.fabric.incremental_column,
                "soft_delete_column": self.fabric.soft_delete_column,
                "approval_column": self.fabric.approval_column,
                "approval_accepted_values": list(self.fabric.approval_accepted_values),
                "sample_rows": self.fabric.sample_rows,
            },
            "ai_search": {
                "endpoint_configured": bool(self.search.endpoint),
                "auth_mode": self.search.auth_mode,
                "admin_key_configured": bool(self.search.admin_key),
                "index_name": self.search.index_name,
                "keyword_index_name": self.search.keyword_index_name,
                "vector_index_name": self.search.vector_index_name,
                "vector_field": self.search.vector_field,
                "datasource_name": self.search.datasource_name,
                "skillset_name": self.search.skillset_name,
                "indexer_name": self.search.indexer_name,
                "semantic_config_name": self.search.semantic_config_name,
                "embedding_resource_uri_configured": bool(self.search.embedding_resource_uri),
                "embedding_deployment_name": self.search.embedding_deployment_name,
                "embedding_model_name": self.search.embedding_model_name,
                "embedding_dimensions": self.search.embedding_dimensions,
            },
        }


@dataclass(frozen=True, slots=True)
class SourceColumn:
    """Column metadata discovered from Fabric SQL or Files metadata."""

    name: str
    data_type: str = "nvarchar"
    nullable: bool = True
    sample_values: tuple[Any, ...] = ()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceColumn":
        """Build a column from a dictionary payload."""
        raw_samples = payload.get("sample_values") or payload.get("samples") or ()
        if not isinstance(raw_samples, Sequence) or isinstance(raw_samples, (str, bytes)):
            raw_samples = ()
        return cls(
            name=str(payload.get("name") or payload.get("column_name") or "").strip(),
            data_type=str(payload.get("data_type") or payload.get("type") or "nvarchar"),
            nullable=bool(payload.get("nullable", True)),
            sample_values=tuple(raw_samples),
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize column metadata for MCP responses and tests."""
        return {
            "name": self.name,
            "data_type": self.data_type,
            "nullable": self.nullable,
            "sample_values": list(self.sample_values),
        }


@dataclass(frozen=True, slots=True)
class SourceMetadata:
    """Discovered source metadata plus bounded sample rows."""

    source_kind: str
    source_name: str
    columns: tuple[SourceColumn, ...]
    sample_rows: tuple[dict[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceMetadata":
        """Build source metadata from a dictionary payload."""
        columns_payload = payload.get("columns") or ()
        columns = tuple(
            column
            for column in (SourceColumn.from_dict(item) for item in columns_payload)
            if column.name
        )
        sample_rows_payload = payload.get("sample_rows") or ()
        sample_rows = tuple(dict(row) for row in sample_rows_payload if isinstance(row, Mapping))
        warnings = tuple(str(item) for item in payload.get("warnings") or ())
        return cls(
            source_kind=str(payload.get("source_kind") or "sql"),
            source_name=str(payload.get("source_name") or payload.get("name") or "source"),
            columns=columns,
            sample_rows=sample_rows,
            warnings=warnings,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize source metadata for MCP responses and tests."""
        return {
            "source_kind": self.source_kind,
            "source_name": self.source_name,
            "columns": [column.to_dict() for column in self.columns],
            "sample_rows": list(self.sample_rows),
            "warnings": list(self.warnings),
        }


class FabricMetadataProvider(Protocol):
    """Adapter protocol for discovering Fabric source structure."""

    async def discover(self) -> SourceMetadata: ...


@dataclass(frozen=True, slots=True)
class StaticFabricMetadataProvider:
    """Test/operator adapter for injected source metadata."""

    metadata: SourceMetadata

    async def discover(self) -> SourceMetadata:
        """Return injected metadata without live Fabric dependencies."""
        return self.metadata


@dataclass(frozen=True, slots=True)
class FabricSqlMetadataProvider:
    """Adapter for discovering Fabric SQL table metadata over TDS."""

    settings: FabricSourceSettings

    async def discover(self) -> SourceMetadata:
        """Discover table columns and bounded samples using an optional SQL driver."""
        self.settings.validate()
        try:
            pyodbc = importlib.import_module("pyodbc")
        except ImportError as exc:
            raise FabricSearchIngestionError(
                kind="fabric_sql_driver_unavailable",
                message=(
                    "Fabric SQL metadata discovery requires a SQL Server ODBC driver "
                    "and the optional pyodbc package at runtime."
                ),
                operator_action=(
                    "Install/use the Microsoft ODBC Driver for SQL Server plus pyodbc, "
                    "or call this MCP tool with injected source_metadata/columns for "
                    "offline planning."
                ),
                status_code=424,
            ) from exc

        return await asyncio.to_thread(self._discover_sync, pyodbc)

    def _discover_sync(self, pyodbc: Any) -> SourceMetadata:
        connection_string = _build_fabric_sql_pyodbc_connection_string(self.settings)
        connection = pyodbc.connect(connection_string, timeout=15)
        try:
            cursor = connection.cursor()
            cursor.execute(
                """
                SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
                ORDER BY ORDINAL_POSITION
                """,
                self.settings.sql_schema,
                self.settings.sql_table,
            )
            rows = cursor.fetchall()
            columns = tuple(
                SourceColumn(
                    name=str(row.COLUMN_NAME),
                    data_type=str(row.DATA_TYPE),
                    nullable=str(row.IS_NULLABLE).upper() == "YES",
                )
                for row in rows
            )
            if not columns:
                raise FabricSearchIngestionError(
                    kind="fabric_sql_table_not_found",
                    message=f"No columns found for Fabric SQL source {self.settings.sql_source_name}.",
                    operator_action="Verify FABRIC_SQL_SCHEMA and FABRIC_SQL_TABLE.",
                    status_code=404,
                )
            sample_rows = self._load_sample_rows(cursor)
            return SourceMetadata(
                source_kind="sql",
                source_name=self.settings.sql_source_name,
                columns=_attach_sample_values(columns, sample_rows),
                sample_rows=tuple(sample_rows),
            )
        finally:
            connection.close()

    def _load_sample_rows(self, cursor: Any) -> list[dict[str, Any]]:
        if self.settings.sample_rows <= 0:
            return []
        source_table = _quote_sql_identifier(self.settings.sql_schema)
        source_table = f"{source_table}.{_quote_sql_identifier(self.settings.sql_table or '')}"
        cursor.execute(f"SELECT TOP {self.settings.sample_rows} * FROM {source_table}")
        column_names = [str(item[0]) for item in cursor.description or ()]
        rows = []
        for row in cursor.fetchall():
            rows.append(
                {
                    column_name: _json_safe_value(value)
                    for column_name, value in zip(column_names, row, strict=False)
                }
            )
        return rows


@dataclass(frozen=True, slots=True)
class OneLakeFilesMetadataProvider:
    """Adapter for OneLake Files metadata supported by the AI Search indexer."""

    settings: FabricSourceSettings

    async def discover(self) -> SourceMetadata:
        """Return file/content metadata for OneLake Files ingestion."""
        self.settings.validate()
        return SourceMetadata(
            source_kind="onelake_files",
            source_name=(
                f"lakehouse:{self.settings.onelake_lakehouse_id}/"
                f"{self.settings.onelake_files_path or ''}"
            ),
            columns=(
                SourceColumn("metadata_storage_path", "Edm.String", False),
                SourceColumn("metadata_storage_name", "Edm.String", True),
                SourceColumn("metadata_storage_last_modified", "Edm.DateTimeOffset", True),
                SourceColumn("metadata_storage_content_type", "Edm.String", True),
                SourceColumn("content", "Edm.String", True),
            ),
            warnings=(
                "OneLake support is Files/shortcuts only. Workspace Tables and "
                "Parquet/Delta table content are intentionally rejected.",
            ),
        )


@dataclass(frozen=True, slots=True)
class FieldMapping:
    """Mapping from a Fabric source column to an AI Search index field."""

    target_field: str
    source_field: str | None
    transform: str
    confidence: float
    evidence: tuple[str, ...]
    source_fields: tuple[str, ...] = ()
    indexer_supported: bool = True

    def to_dict(self) -> dict[str, Any]:
        """Serialize the mapping for MCP responses and tests."""
        return {
            "target_field": self.target_field,
            "source_field": self.source_field,
            "source_fields": list(self.source_fields),
            "transform": self.transform,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "indexer_supported": self.indexer_supported,
        }


@dataclass(frozen=True, slots=True)
class GovernanceApprovalSignal:
    """Governance signal for approval-aware ingestion planning."""

    status: str
    column: str | None = None
    accepted_values: tuple[str, ...] = ()
    recommended_action: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize governance metadata for operator-facing responses."""
        return {
            "status": self.status,
            "column": self.column,
            "accepted_values": list(self.accepted_values),
            "recommended_action": self.recommended_action,
            "truth_lifecycle_state_mutated": False,
        }


@dataclass(frozen=True, slots=True)
class MappingPlan:
    """Deterministic source-to-index mapping plan."""

    source: SourceMetadata
    index_name: str
    vector_field: str
    mappings: tuple[FieldMapping, ...]
    governance: GovernanceApprovalSignal
    warnings: tuple[str, ...] = ()

    @property
    def confidence(self) -> float:
        """Return average confidence across mapped fields."""
        if not self.mappings:
            return 0.0
        return round(sum(mapping.confidence for mapping in self.mappings) / len(self.mappings), 3)

    def mapping_for(self, target_field: str) -> FieldMapping | None:
        """Return the first mapping for a target field."""
        return next(
            (mapping for mapping in self.mappings if mapping.target_field == target_field),
            None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the mapping plan for MCP responses and tests."""
        return {
            "source": self.source.to_dict(),
            "index_name": self.index_name,
            "vector_field": self.vector_field,
            "confidence": self.confidence,
            "mappings": [mapping.to_dict() for mapping in self.mappings],
            "governance": self.governance.to_dict(),
            "warnings": list(self.warnings),
        }


class MappingStrategy(Protocol):
    """Strategy interface for deterministic column-to-field matching."""

    def match(
        self,
        *,
        target_field: str,
        columns: Sequence[SourceColumn],
        sample_rows: Sequence[Mapping[str, Any]],
    ) -> FieldMapping | None: ...


@dataclass(frozen=True, slots=True)
class ExactSynonymMappingStrategy:
    """Strategy pattern: match target fields by exact normalized synonym."""

    synonyms: Mapping[str, tuple[str, ...]]

    def match(
        self,
        *,
        target_field: str,
        columns: Sequence[SourceColumn],
        sample_rows: Sequence[Mapping[str, Any]],
    ) -> FieldMapping | None:
        del sample_rows
        synonym_set = {_normalize_name(value) for value in self.synonyms.get(target_field, ())}
        synonym_set.add(_normalize_name(target_field))
        for column in columns:
            normalized = _normalize_name(column.name)
            if normalized in synonym_set:
                return FieldMapping(
                    target_field=target_field,
                    source_field=column.name,
                    source_fields=(column.name,),
                    transform="copy",
                    confidence=0.98,
                    evidence=(f"source column {column.name!r} matched synonym",),
                )
        return None


@dataclass(frozen=True, slots=True)
class SampleValueMappingStrategy:
    """Strategy pattern: infer mappings from bounded sample values."""

    def match(
        self,
        *,
        target_field: str,
        columns: Sequence[SourceColumn],
        sample_rows: Sequence[Mapping[str, Any]],
    ) -> FieldMapping | None:
        del sample_rows
        if target_field not in {"price", "currency", "rating", "availability"}:
            return None
        for column in columns:
            samples = tuple(value for value in column.sample_values if value not in (None, ""))
            if not samples:
                continue
            if target_field == "price" and _looks_like_price(samples):
                return _sample_mapping(target_field, column, "numeric values resemble prices")
            if target_field == "currency" and _looks_like_currency(samples):
                return _sample_mapping(target_field, column, "sample values resemble ISO currency")
            if target_field == "rating" and _looks_like_rating(samples):
                return _sample_mapping(target_field, column, "numeric values fit rating range")
            if target_field == "availability" and _looks_like_availability(samples):
                return _sample_mapping(target_field, column, "sample values resemble stock status")
        return None


@dataclass(frozen=True, slots=True)
class FallbackPassthroughMappingStrategy:
    """Strategy pattern: low-confidence passthrough for matching normalized names."""

    def match(
        self,
        *,
        target_field: str,
        columns: Sequence[SourceColumn],
        sample_rows: Sequence[Mapping[str, Any]],
    ) -> FieldMapping | None:
        del sample_rows
        normalized_target = _normalize_name(target_field)
        for column in columns:
            if normalized_target in _normalize_name(column.name):
                return FieldMapping(
                    target_field=target_field,
                    source_field=column.name,
                    source_fields=(column.name,),
                    transform="copy",
                    confidence=0.55,
                    evidence=("fallback normalized-name passthrough",),
                )
        return None


_FIELD_SYNONYMS: dict[str, tuple[str, ...]] = {
    "id": ("id", "sku", "product_id", "item_id", "entity_id", "product_key"),
    "sku": ("sku", "product_id", "item_id", "style_id", "style_number"),
    "entity_id": ("entity_id", "product_id", "item_id", "sku", "id"),
    "name": ("name", "title", "product_name", "display_name", "item_name"),
    "description": ("description", "long_description", "body", "product_description"),
    "content": ("content", "search_text", "search_content", "catalog_content"),
    "enriched_description": ("enriched_description", "semantic_description"),
    "category": ("category", "category_name", "department", "class_name"),
    "category_id": ("category_id", "category_key", "department_id", "class_id"),
    "brand": ("brand", "brand_name", "manufacturer", "vendor_brand"),
    "price": ("price", "list_price", "sale_price", "current_price", "unit_price"),
    "currency": ("currency", "currency_code", "price_currency"),
    "rating": ("rating", "average_rating", "review_rating", "stars"),
    "availability": ("availability", "stock_status", "inventory_status", "available_to_promise"),
    "color": ("color", "colour", "primary_color"),
    "material": ("material", "fabric", "materials"),
    "size": ("size", "size_label", "dimension"),
    "gender": ("gender", "gender_target", "audience_gender"),
    "facet_tags": ("facet_tags", "facets", "tags", "filter_tags"),
    "source_last_modified": (
        "source_last_modified",
        "last_modified",
        "modified_at",
        "updated_at",
        "modified_date",
        "metadata_storage_last_modified",
    ),
    "enriched_at": ("enriched_at", "enrichment_timestamp"),
    "source_system": ("source_system", "source", "system_of_record"),
    "source_table": ("source_table", "table_name"),
    "search_keywords": ("search_keywords", "keywords", "keyword_list", "search_terms"),
    "use_cases": ("use_cases", "usecases", "occasions", "usage"),
    "complementary_products": ("complementary_products", "complements", "cross_sell"),
    "substitute_products": ("substitute_products", "substitutes", "alternatives"),
    "marketing_bullets": ("marketing_bullets", "bullets", "selling_points"),
    "target_audience": ("target_audience", "audience", "customer_segment"),
    "seasonal_relevance": ("seasonal_relevance", "season", "seasonality"),
    "sustainability_signals": (
        "sustainability_signals",
        "sustainability",
        "eco_claims",
    ),
    "care_guidance": ("care_guidance", "care_instructions", "care"),
    "completeness_pct": ("completeness_pct", "completeness", "data_quality_score"),
}

_INDEX_TARGET_FIELDS = (
    "id",
    "sku",
    "entity_id",
    "name",
    "description",
    "content",
    "enriched_description",
    "category",
    "category_id",
    "brand",
    "price",
    "currency",
    "rating",
    "availability",
    "color",
    "material",
    "size",
    "gender",
    "facet_tags",
    "source_last_modified",
    "enriched_at",
    "source_system",
    "source_table",
    "search_keywords",
    "use_cases",
    "complementary_products",
    "substitute_products",
    "marketing_bullets",
    "target_audience",
    "seasonal_relevance",
    "sustainability_signals",
    "care_guidance",
    "completeness_pct",
)

_CONTENT_SOURCE_PRIORITY = (
    "name",
    "brand",
    "category",
    "description",
    "search_keywords",
    "use_cases",
    "facet_tags",
)


def build_mapping_plan(
    metadata: SourceMetadata,
    settings: FabricSearchIngestionSettings | None = None,
) -> MappingPlan:
    """Build a deterministic mapping plan for the unified hybrid catalog index."""
    resolved_settings = settings or FabricSearchIngestionSettings.from_env()
    strategies: tuple[MappingStrategy, ...] = (
        ExactSynonymMappingStrategy(_FIELD_SYNONYMS),
        SampleValueMappingStrategy(),
        FallbackPassthroughMappingStrategy(),
    )
    mappings_by_target: dict[str, FieldMapping] = {}
    for target_field in _INDEX_TARGET_FIELDS:
        for strategy in strategies:
            mapping = strategy.match(
                target_field=target_field,
                columns=metadata.columns,
                sample_rows=metadata.sample_rows,
            )
            if mapping is not None:
                mappings_by_target[target_field] = mapping
                break

    _ensure_identifier_mappings(mappings_by_target)
    _ensure_content_mapping(mappings_by_target)
    _ensure_source_constant_mappings(mappings_by_target, metadata)
    _ensure_incremental_mapping(mappings_by_target, resolved_settings.fabric)

    governance = _build_governance_signal(metadata, resolved_settings.fabric)
    warnings = tuple(metadata.warnings) + tuple(resolved_settings.search.compatibility_warnings)
    if mappings_by_target.get("content") and not mappings_by_target["content"].indexer_supported:
        warnings += (
            "Content is planned as a high-signal concat. SQL indexers cannot concatenate "
            "columns in fieldMappings; expose a Fabric SQL view/content column for exact "
            "concat behavior. The generated indexer maps the strongest text field as a "
            "runtime fallback.",
        )
    return MappingPlan(
        source=metadata,
        index_name=resolved_settings.search.index_name,
        vector_field=resolved_settings.search.vector_field,
        mappings=tuple(mappings_by_target.values()),
        governance=governance,
        warnings=warnings,
    )


@dataclass(frozen=True, slots=True)
class SearchResourcePayloads:
    """Builder result for Azure AI Search resource payloads."""

    index: dict[str, Any]
    skillset: dict[str, Any]
    data_source: dict[str, Any]
    indexer: dict[str, Any]
    mapping_plan: MappingPlan
    warnings: tuple[str, ...] = ()

    def to_dict(self, *, redact_sensitive: bool = False) -> dict[str, Any]:
        """Serialize resource payloads for MCP responses and tests."""
        resources = {
            "index": self.index,
            "skillset": self.skillset,
            "data_source": self.data_source,
            "indexer": self.indexer,
        }
        if redact_sensitive:
            resources = _redact_resource_payloads(resources)
        return {
            "resources": resources,
            "mapping_plan": self.mapping_plan.to_dict(),
            "governance": self.mapping_plan.governance.to_dict(),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True, slots=True)
class SearchResourceBuilder:
    """Builder pattern for AI Search index, skillset, data source, and indexer."""

    settings: FabricSearchIngestionSettings

    def build(self, mapping_plan: MappingPlan) -> SearchResourcePayloads:
        """Build all Azure AI Search resources in dependency order."""
        self.settings.fabric.validate()
        self.settings.search.validate_for_resource_build()
        index = self.build_index()
        skillset = self.build_skillset()
        data_source = self.build_data_source()
        indexer = self.build_indexer(mapping_plan)
        warnings = mapping_plan.warnings
        return SearchResourcePayloads(
            index=index,
            skillset=skillset,
            data_source=data_source,
            indexer=indexer,
            mapping_plan=mapping_plan,
            warnings=warnings,
        )

    def build_index(self) -> dict[str, Any]:
        """Build a unified hybrid catalog index payload."""
        search = self.settings.search
        vector_profile = "catalog-vector-profile"
        vectorizer_name = "catalog-openai-vectorizer"
        return {
            "name": search.index_name,
            "fields": _build_index_fields(search.vector_field, search.embedding_dimensions),
            "vectorSearch": {
                "algorithms": [
                    {
                        "name": "hnsw-cosine",
                        "kind": "hnsw",
                        "hnswParameters": {"metric": "cosine"},
                    }
                ],
                "profiles": [
                    {
                        "name": vector_profile,
                        "algorithm": "hnsw-cosine",
                        "vectorizer": vectorizer_name,
                    }
                ],
                "vectorizers": [
                    {
                        "name": vectorizer_name,
                        "kind": "azureOpenAI",
                        "azureOpenAIParameters": {
                            "resourceUri": search.embedding_resource_uri,
                            "deploymentId": search.embedding_deployment_name,
                            "modelName": search.embedding_model_name,
                        },
                    }
                ],
            },
            "semantic": {
                "configurations": [
                    {
                        "name": search.semantic_config_name,
                        "prioritizedFields": {
                            "titleField": {"fieldName": "name"},
                            "prioritizedContentFields": [
                                {"fieldName": "content"},
                                {"fieldName": "enriched_description"},
                                {"fieldName": "description"},
                            ],
                            "prioritizedKeywordsFields": [
                                {"fieldName": "search_keywords"},
                                {"fieldName": "use_cases"},
                                {"fieldName": "facet_tags"},
                                {"fieldName": "brand"},
                                {"fieldName": "category"},
                            ],
                        },
                    }
                ]
            },
        }

    def build_skillset(self) -> dict[str, Any]:
        """Build skillset payload for integrated vectorization."""
        search = self.settings.search
        return {
            "name": search.skillset_name,
            "description": "Generate one product-level embedding for hybrid catalog retrieval.",
            "skills": [
                {
                    "@odata.type": "#Microsoft.Skills.Text.AzureOpenAIEmbeddingSkill",
                    "name": "embed_catalog_content",
                    "description": "Generate one vector for each product search document.",
                    "context": "/document",
                    "resourceUri": search.embedding_resource_uri,
                    "deploymentId": search.embedding_deployment_name,
                    "modelName": search.embedding_model_name,
                    "dimensions": search.embedding_dimensions,
                    "inputs": [{"name": "text", "source": "/document/content"}],
                    "outputs": [{"name": "embedding", "targetName": "embedding"}],
                },
            ],
        }

    def build_data_source(self) -> dict[str, Any]:
        """Build source-specific data source payload."""
        if self.settings.fabric.source_kind == "onelake_files":
            return self._build_onelake_data_source()
        return self._build_sql_data_source()

    def _build_sql_data_source(self) -> dict[str, Any]:
        fabric = self.settings.fabric
        payload: dict[str, Any] = {
            "name": self.settings.search.datasource_name,
            "description": "Fabric SQL source for catalog search enrichment ingestion.",
            "type": "azuresql",
            "credentials": {
                "connectionString": _build_fabric_sql_connection_string(fabric),
            },
            "container": {
                "name": f"[{fabric.sql_schema}].[{fabric.sql_table}]",
            },
        }
        if fabric.incremental_column:
            payload["dataChangeDetectionPolicy"] = {
                "@odata.type": "#Microsoft.Azure.Search.HighWaterMarkChangeDetectionPolicy",
                "highWaterMarkColumnName": fabric.incremental_column,
            }
        if fabric.soft_delete_column and fabric.soft_delete_marker is not None:
            payload["dataDeletionDetectionPolicy"] = {
                "@odata.type": "#Microsoft.Azure.Search.SoftDeleteColumnDeletionDetectionPolicy",
                "softDeleteColumnName": fabric.soft_delete_column,
                "softDeleteMarkerValue": fabric.soft_delete_marker,
            }
        return payload

    def _build_onelake_data_source(self) -> dict[str, Any]:
        fabric = self.settings.fabric
        connection_key = "WorkspaceEndpoint" if fabric.onelake_workspace_endpoint else "ResourceId"
        connection_value = fabric.onelake_workspace_endpoint or fabric.workspace_id
        payload: dict[str, Any] = {
            "name": self.settings.search.datasource_name,
            "description": "Fabric OneLake Files source for catalog search ingestion.",
            "type": "onelake",
            "credentials": {"connectionString": f"{connection_key}={connection_value}"},
            "container": {"name": fabric.onelake_lakehouse_id},
        }
        if fabric.onelake_files_path:
            payload["container"]["query"] = fabric.onelake_files_path
        if fabric.soft_delete_column and fabric.soft_delete_marker is not None:
            payload["dataDeletionDetectionPolicy"] = {
                "@odata.type": "#Microsoft.Azure.Search.SoftDeleteColumnDeletionDetectionPolicy",
                "softDeleteColumnName": fabric.soft_delete_column,
                "softDeleteMarkerValue": fabric.soft_delete_marker,
            }
        return payload

    def build_indexer(self, mapping_plan: MappingPlan) -> dict[str, Any]:
        """Build indexer payload that drives the skillset and target index."""
        return {
            "name": self.settings.search.indexer_name,
            "description": "Fabric catalog ingestion indexer owned by search-enrichment-agent.",
            "dataSourceName": self.settings.search.datasource_name,
            "targetIndexName": self.settings.search.index_name,
            "skillsetName": self.settings.search.skillset_name,
            "fieldMappings": _build_indexer_field_mappings(mapping_plan),
            "outputFieldMappings": [
                {
                    "sourceFieldName": "/document/embedding/*",
                    "targetFieldName": self.settings.search.vector_field,
                }
            ],
            "parameters": {
                "maxFailedItems": 10,
                "maxFailedItemsPerBatch": 5,
                "configuration": {
                    "dataToExtract": "contentAndMetadata",
                    "queryTimeout": "00:10:00",
                },
            },
        }


@dataclass(slots=True)
class SearchResourceProvisioner:
    """REST client for creating/updating AI Search resources."""

    settings: AISearchResourceSettings
    credential: AsyncTokenCredential | None = None
    transport: httpx.AsyncBaseTransport | None = None
    _token: AccessToken | None = field(default=None, init=False, repr=False)

    async def provision(self, resources: SearchResourcePayloads) -> dict[str, Any]:
        """Create or update index, skillset, data source, and indexer resources."""
        self.settings.validate_for_provisioning()
        operations = [
            ("index", f"/indexes('{resources.index['name']}')", resources.index),
            (
                "skillset",
                f"/skillsets('{resources.skillset['name']}')",
                resources.skillset,
            ),
            (
                "data_source",
                f"/datasources('{resources.data_source['name']}')",
                resources.data_source,
            ),
            (
                "indexer",
                f"/indexers('{resources.indexer['name']}')",
                resources.indexer,
            ),
        ]
        results = []
        for resource_type, path, payload in operations:
            response = await self._request_with_retry("PUT", path, json_body=payload)
            results.append(
                {
                    "resource_type": resource_type,
                    "name": payload.get("name"),
                    "http_status": response.status_code,
                    "status": "ok",
                }
            )
        return {
            "status": "ok",
            "operation": "provision_search_resources",
            "resources": results,
            "governance": resources.mapping_plan.governance.to_dict(),
            "catalog_search_env": {
                "AI_SEARCH_INDEX": self.settings.index_name,
                "AI_SEARCH_VECTOR_INDEX": self.settings.index_name,
                "AI_SEARCH_VECTOR_FIELD": self.settings.vector_field,
            },
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def run_indexer(self, indexer_name: str | None = None) -> dict[str, Any]:
        """Run the configured indexer on demand."""
        self.settings.validate_for_provisioning()
        resolved_name = indexer_name or self.settings.indexer_name
        response = await self._request_with_retry(
            "POST",
            f"/indexers('{resolved_name}')/search.run",
        )
        return {
            "status": "accepted" if response.status_code == 202 else "ok",
            "operation": "run_indexer",
            "indexer_name": resolved_name,
            "http_status": response.status_code,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _request_with_retry(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        last_exc: Exception | None = None
        for attempt in range(4):
            try:
                return await self._request_once(method, path, json_body=json_body)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in _TRANSIENT_STATUS_CODES and attempt < 3:
                    await asyncio.sleep(_retry_delay_seconds(exc.response, attempt))
                    last_exc = exc
                    continue
                raise
            except httpx.HTTPError as exc:
                if attempt < 3:
                    await asyncio.sleep(0.5 * (2**attempt))
                    last_exc = exc
                    continue
                raise
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("Unexpected state while issuing AI Search resource request")

    async def _request_once(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        headers = await self._build_headers()
        async with httpx.AsyncClient(
            timeout=20.0,
            transport=self.transport,
        ) as client:
            response = await client.request(
                method,
                _build_search_url(self.settings, path),
                headers=headers,
                json=json_body,
            )
        response.raise_for_status()
        return response

    async def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-ms-client-request-id": str(uuid4()),
        }
        if self.settings.auth_mode in {"api_key", "admin_key", "key"}:
            if not self.settings.admin_key:
                raise ValueError("AI Search admin key is required for key authentication")
            headers["api-key"] = self.settings.admin_key
            return headers
        token = await self._get_bearer_token()
        headers["Authorization"] = f"Bearer {token}"
        return headers

    async def _get_bearer_token(self) -> str:
        now_epoch = int(datetime.now(UTC).timestamp())
        if self._token and self._token.expires_on - 60 > now_epoch:
            return self._token.token
        if self.credential is None:
            raise ValueError("credential is required for managed identity authentication")
        self._token = await self.credential.get_token("https://search.azure.com/.default")
        if self._token is None:
            raise ValueError("Unable to obtain AI Search bearer token")
        return self._token.token


def build_search_resource_provisioner_from_env(
    *,
    transport: httpx.AsyncBaseTransport | None = None,
) -> SearchResourceProvisioner:
    """Build a provisioning REST client from environment variables."""
    search_settings = AISearchResourceSettings.from_env()
    credential: AsyncTokenCredential | None = None
    if search_settings.auth_mode not in {"api_key", "admin_key", "key"}:
        # Import lazily so API-key paths do not require Azure identity startup.
        # pylint: disable-next=import-outside-toplevel
        from azure.identity.aio import DefaultAzureCredential

        credential = DefaultAzureCredential()
    return SearchResourceProvisioner(
        settings=search_settings,
        credential=credential,
        transport=transport,
    )


def register_fabric_search_ingestion_tools(
    mcp: MCPToolServer,
    *,
    provider_factory: (
        Callable[[FabricSearchIngestionSettings, dict[str, Any]], FabricMetadataProvider] | None
    ) = None,
    provisioner_factory: (
        Callable[[AISearchResourceSettings], SearchResourceProvisioner] | None
    ) = None,
) -> None:
    """Register Fabric search-ingestion MCP tools."""

    async def discover_source(payload: dict[str, Any]) -> dict[str, Any]:
        settings = FabricSearchIngestionSettings.from_env()
        try:
            provider = _resolve_metadata_provider(settings, payload, provider_factory)
            metadata = await provider.discover()
            return {
                "status": "ok",
                "operation": "discover_source",
                "source": metadata.to_dict(),
                "settings": settings.to_safe_dict(),
            }
        except FabricSearchIngestionError as exc:
            return exc.to_response("discover_source")

    async def build_plan_tool(payload: dict[str, Any]) -> dict[str, Any]:
        settings = FabricSearchIngestionSettings.from_env()
        try:
            metadata = await _metadata_from_payload_or_provider(
                settings,
                payload,
                provider_factory,
            )
            plan = build_mapping_plan(metadata, settings)
            return {
                "status": "ok",
                "operation": "build_mapping_plan",
                "mapping_plan": plan.to_dict(),
                "governance": plan.governance.to_dict(),
            }
        except FabricSearchIngestionError as exc:
            return exc.to_response("build_mapping_plan")

    async def build_resources_tool(payload: dict[str, Any]) -> dict[str, Any]:
        settings = FabricSearchIngestionSettings.from_env()
        try:
            resources = await _build_resources_from_payload(
                settings,
                payload,
                provider_factory,
            )
            return {
                "status": "ok",
                "operation": "build_search_resources",
                **resources.to_dict(redact_sensitive=True),
            }
        except FabricSearchIngestionError as exc:
            return exc.to_response("build_search_resources")

    async def provision_resources_tool(payload: dict[str, Any]) -> dict[str, Any]:
        settings = FabricSearchIngestionSettings.from_env()
        try:
            resources = await _build_resources_from_payload(
                settings,
                payload,
                provider_factory,
            )
            provisioner = (
                provisioner_factory(settings.search)
                if provisioner_factory is not None
                else build_search_resource_provisioner_from_env()
            )
            return await provisioner.provision(resources)
        except FabricSearchIngestionError as exc:
            return exc.to_response("provision_search_resources")
        except httpx.HTTPStatusError as exc:
            return _http_error_response("provision_search_resources", exc)
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            return _runtime_error_response("provision_search_resources", exc)

    async def run_indexer_tool(payload: dict[str, Any]) -> dict[str, Any]:
        settings = FabricSearchIngestionSettings.from_env()
        try:
            provisioner = (
                provisioner_factory(settings.search)
                if provisioner_factory is not None
                else build_search_resource_provisioner_from_env()
            )
            return await provisioner.run_indexer(
                _optional(str(payload.get("indexer_name") or "")) or settings.search.indexer_name
            )
        except FabricSearchIngestionError as exc:
            return exc.to_response("run_indexer")
        except httpx.HTTPStatusError as exc:
            return _http_error_response("run_indexer", exc)
        except (httpx.HTTPError, ValueError, RuntimeError) as exc:
            return _runtime_error_response("run_indexer", exc)

    mcp.add_tool("/fabric-search-ingestion/discover_source", discover_source)
    mcp.add_tool("/fabric-search-ingestion/build_mapping_plan", build_plan_tool)
    mcp.add_tool("/fabric-search-ingestion/build_search_resources", build_resources_tool)
    mcp.add_tool("/fabric-search-ingestion/provision_search_resources", provision_resources_tool)
    mcp.add_tool("/fabric-search-ingestion/run_indexer", run_indexer_tool)


async def _metadata_from_payload_or_provider(
    settings: FabricSearchIngestionSettings,
    payload: Mapping[str, Any],
    provider_factory: (
        Callable[[FabricSearchIngestionSettings, dict[str, Any]], FabricMetadataProvider] | None
    ),
) -> SourceMetadata:
    provider = _resolve_metadata_provider(settings, dict(payload), provider_factory)
    return await provider.discover()


async def _build_resources_from_payload(
    settings: FabricSearchIngestionSettings,
    payload: Mapping[str, Any],
    provider_factory: (
        Callable[[FabricSearchIngestionSettings, dict[str, Any]], FabricMetadataProvider] | None
    ),
) -> SearchResourcePayloads:
    metadata = await _metadata_from_payload_or_provider(settings, payload, provider_factory)
    plan = build_mapping_plan(metadata, settings)
    return SearchResourceBuilder(settings).build(plan)


def _resolve_metadata_provider(
    settings: FabricSearchIngestionSettings,
    payload: dict[str, Any],
    provider_factory: (
        Callable[[FabricSearchIngestionSettings, dict[str, Any]], FabricMetadataProvider] | None
    ),
) -> FabricMetadataProvider:
    injected = _source_metadata_from_payload(payload)
    if injected is not None:
        return StaticFabricMetadataProvider(injected)
    if provider_factory is not None:
        return provider_factory(settings, payload)
    if settings.fabric.source_kind == "onelake_files":
        return OneLakeFilesMetadataProvider(settings.fabric)
    return FabricSqlMetadataProvider(settings.fabric)


def _source_metadata_from_payload(payload: Mapping[str, Any]) -> SourceMetadata | None:
    source_metadata = payload.get("source_metadata")
    if isinstance(source_metadata, Mapping):
        return SourceMetadata.from_dict(source_metadata)
    columns = payload.get("columns")
    if isinstance(columns, Sequence) and not isinstance(columns, (str, bytes)):
        return SourceMetadata.from_dict(
            {
                "source_kind": payload.get("source_kind") or "sql",
                "source_name": payload.get("source_name") or "injected.metadata",
                "columns": columns,
                "sample_rows": payload.get("sample_rows") or (),
            }
        )
    return None


def _ensure_identifier_mappings(mappings_by_target: dict[str, FieldMapping]) -> None:
    id_mapping = mappings_by_target.get("id")
    if id_mapping is None:
        fallback = mappings_by_target.get("sku") or mappings_by_target.get("entity_id")
        if fallback is not None:
            mappings_by_target["id"] = FieldMapping(
                target_field="id",
                source_field=fallback.source_field,
                source_fields=fallback.source_fields,
                transform="copy",
                confidence=max(fallback.confidence - 0.05, 0.5),
                evidence=("identifier fallback from sku/entity_id",),
            )
    sku_mapping = mappings_by_target.get("sku")
    if sku_mapping is not None and "entity_id" not in mappings_by_target:
        mappings_by_target["entity_id"] = FieldMapping(
            target_field="entity_id",
            source_field=sku_mapping.source_field,
            source_fields=sku_mapping.source_fields,
            transform="copy",
            confidence=max(sku_mapping.confidence - 0.03, 0.5),
            evidence=("entity_id mirrors SKU for catalog-search compatibility",),
        )


def _ensure_content_mapping(mappings_by_target: dict[str, FieldMapping]) -> None:
    content_mapping = mappings_by_target.get("content")
    if content_mapping is not None:
        return
    source_fields = tuple(
        mapping.source_field
        for target_field in _CONTENT_SOURCE_PRIORITY
        if (mapping := mappings_by_target.get(target_field)) and mapping.source_field
    )
    if not source_fields:
        return
    mappings_by_target["content"] = FieldMapping(
        target_field="content",
        source_field=", ".join(source_fields),
        source_fields=source_fields,
        transform="concat_non_empty(name, brand, category, description, keywords, use_cases, facets)",
        confidence=0.76,
        evidence=("derived from high-signal retrieval fields",),
        indexer_supported=False,
    )


def _ensure_source_constant_mappings(
    mappings_by_target: dict[str, FieldMapping],
    metadata: SourceMetadata,
) -> None:
    if "source_system" not in mappings_by_target:
        mappings_by_target["source_system"] = FieldMapping(
            target_field="source_system",
            source_field=None,
            source_fields=(),
            transform=f"constant:{metadata.source_kind}",
            confidence=1.0,
            evidence=("source metadata identifies Fabric source kind",),
            indexer_supported=False,
        )
    if "source_table" not in mappings_by_target:
        mappings_by_target["source_table"] = FieldMapping(
            target_field="source_table",
            source_field=None,
            source_fields=(),
            transform=f"constant:{metadata.source_name}",
            confidence=1.0,
            evidence=("source metadata identifies Fabric source name",),
            indexer_supported=False,
        )


def _ensure_incremental_mapping(
    mappings_by_target: dict[str, FieldMapping],
    fabric: FabricSourceSettings,
) -> None:
    if not fabric.incremental_column or "source_last_modified" in mappings_by_target:
        return
    mappings_by_target["source_last_modified"] = FieldMapping(
        target_field="source_last_modified",
        source_field=fabric.incremental_column,
        source_fields=(fabric.incremental_column,),
        transform="copy",
        confidence=0.9,
        evidence=("FABRIC_INCREMENTAL_COLUMN configured for change detection",),
    )


def _build_governance_signal(
    metadata: SourceMetadata,
    fabric: FabricSourceSettings,
) -> GovernanceApprovalSignal:
    if not fabric.approval_column:
        return GovernanceApprovalSignal(
            status="not_configured",
            recommended_action=(
                "Set FABRIC_APPROVAL_COLUMN and FABRIC_APPROVAL_ACCEPTED_VALUES, or expose "
                "an approved-only SQL view before indexing production catalog data."
            ),
        )
    column_names = {_normalize_name(column.name) for column in metadata.columns}
    if _normalize_name(fabric.approval_column) not in column_names:
        return GovernanceApprovalSignal(
            status="missing_column",
            column=fabric.approval_column,
            accepted_values=fabric.approval_accepted_values,
            recommended_action=(
                "Approval env vars are configured but the discovered source does not include "
                "that column. Verify metadata or expose an approved-only Fabric view."
            ),
        )
    accepted_values = fabric.approval_accepted_values or ("approved", "true", "1")
    return GovernanceApprovalSignal(
        status="configured",
        column=fabric.approval_column,
        accepted_values=accepted_values,
        recommended_action=(
            "Provisioning reports the approval signal only. Search ingestion does not mutate "
            "truth lifecycle state; use a source view if the indexer must filter rows."
        ),
    )


def _build_index_fields(vector_field: str, dimensions: int) -> list[dict[str, Any]]:
    string_searchable = {"name", "description", "content", "enriched_description"}
    simple_filter_fields = {
        "id",
        "sku",
        "entity_id",
        "category",
        "category_id",
        "brand",
        "currency",
        "availability",
        "color",
        "material",
        "size",
        "gender",
        "source_system",
        "source_table",
    }
    collection_fields = {
        "facet_tags",
        "search_keywords",
        "use_cases",
        "complementary_products",
        "substitute_products",
        "marketing_bullets",
        "target_audience",
        "seasonal_relevance",
        "sustainability_signals",
    }
    numeric_fields = {"price", "rating", "completeness_pct"}
    date_fields = {"source_last_modified", "enriched_at"}

    fields: list[dict[str, Any]] = []
    for field_name in _INDEX_TARGET_FIELDS:
        if field_name in collection_fields:
            fields.append(
                {
                    "name": field_name,
                    "type": "Collection(Edm.String)",
                    "searchable": True,
                    "filterable": True,
                    "facetable": field_name in {"facet_tags", "search_keywords", "use_cases"},
                    "retrievable": True,
                }
            )
            continue
        if field_name in numeric_fields:
            fields.append(
                {
                    "name": field_name,
                    "type": "Edm.Double",
                    "filterable": True,
                    "sortable": True,
                    "facetable": True,
                    "retrievable": True,
                }
            )
            continue
        if field_name in date_fields:
            fields.append(
                {
                    "name": field_name,
                    "type": "Edm.DateTimeOffset",
                    "filterable": True,
                    "sortable": True,
                    "retrievable": True,
                }
            )
            continue
        field_payload: dict[str, Any] = {
            "name": field_name,
            "type": "Edm.String",
            "retrievable": True,
        }
        if field_name == "id":
            field_payload.update({"key": True, "filterable": True})
        if field_name in simple_filter_fields:
            field_payload.update({"filterable": True, "sortable": field_name in {"sku", "name"}})
            field_payload["facetable"] = field_name in {
                "category",
                "brand",
                "availability",
                "color",
                "material",
                "size",
                "gender",
                "source_system",
            }
        if field_name in string_searchable or field_name in {"brand", "category"}:
            field_payload["searchable"] = True
        fields.append(field_payload)

    fields.append(
        {
            "name": vector_field,
            "type": "Collection(Edm.Single)",
            "searchable": True,
            "retrievable": False,
            "dimensions": dimensions,
            "vectorSearchProfile": "catalog-vector-profile",
        }
    )
    return fields


def _build_indexer_field_mappings(mapping_plan: MappingPlan) -> list[dict[str, Any]]:
    mappings: list[dict[str, Any]] = []
    for mapping in mapping_plan.mappings:
        if not mapping.indexer_supported or not mapping.source_field:
            continue
        mappings.append(
            {
                "sourceFieldName": mapping.source_field,
                "targetFieldName": mapping.target_field,
            }
        )

    if not any(item["targetFieldName"] == "content" for item in mappings):
        content_mapping = mapping_plan.mapping_for("content")
        fallback_source = _content_fallback_source(content_mapping, mapping_plan)
        if fallback_source:
            mappings.append({"sourceFieldName": fallback_source, "targetFieldName": "content"})

    if mapping_plan.source.source_kind == "onelake_files":
        for item in mappings:
            if (
                item["targetFieldName"] == "id"
                and item["sourceFieldName"] == "metadata_storage_path"
            ):
                item["mappingFunction"] = {"name": "base64Encode"}
                break
    return mappings


def _content_fallback_source(
    content_mapping: FieldMapping | None,
    mapping_plan: MappingPlan,
) -> str | None:
    if content_mapping and content_mapping.source_fields:
        for source_field in content_mapping.source_fields:
            if _normalize_name(source_field) in {"description", "longdescription", "content"}:
                return source_field
        return content_mapping.source_fields[0]
    description_mapping = mapping_plan.mapping_for("description")
    return description_mapping.source_field if description_mapping else None


def _build_fabric_sql_connection_string(settings: FabricSourceSettings) -> str:
    if settings.sql_connection_string:
        return settings.sql_connection_string
    endpoint = settings.sql_endpoint or ""
    database = settings.sql_database or ""
    if settings.auth_mode != "managed_identity":
        raise FabricSearchIngestionError(
            kind="unsupported_fabric_auth_mode",
            message=(
                "Only managed_identity Fabric auth is generated automatically. Use "
                "FABRIC_SQL_CONNECTION_STRING for explicit driver-specific auth."
            ),
            operator_action="Set FABRIC_AUTH_MODE=managed_identity or provide a connection string.",
        )
    return ";".join(
        (
            f"Server=tcp:{endpoint},1433",
            f"Database={database}",
            "Encrypt=yes",
            "TrustServerCertificate=no",
            "Authentication=Active Directory Managed Identity",
            "Connection Timeout=30",
        )
    )


def _build_fabric_sql_pyodbc_connection_string(settings: FabricSourceSettings) -> str:
    if settings.sql_connection_string:
        return settings.sql_connection_string
    return ";".join(
        (
            "Driver={ODBC Driver 18 for SQL Server}",
            _build_fabric_sql_connection_string(settings),
        )
    )


def _attach_sample_values(
    columns: tuple[SourceColumn, ...],
    sample_rows: Sequence[Mapping[str, Any]],
) -> tuple[SourceColumn, ...]:
    if not sample_rows:
        return columns
    updated: list[SourceColumn] = []
    for column in columns:
        samples = tuple(
            row.get(column.name)
            for row in sample_rows[:_DEFAULT_SAMPLE_ROWS]
            if row.get(column.name) not in (None, "")
        )
        updated.append(
            SourceColumn(
                name=column.name,
                data_type=column.data_type,
                nullable=column.nullable,
                sample_values=samples,
            )
        )
    return tuple(updated)


def _guard_onelake_files_path(path: str | None) -> None:
    if not path:
        return
    normalized = path.replace("\\", "/").strip("/").lower()
    if normalized == "tables" or normalized.startswith("tables/") or "/tables/" in normalized:
        raise FabricSearchIngestionError(
            kind="unsupported_onelake_table_location",
            message="OneLake AI Search indexers support lakehouse Files, not workspace Tables.",
            operator_action="Use FABRIC_SOURCE_KIND=sql for table content or point to Files content.",
        )
    if normalized.endswith(".parquet") or "/_delta_log" in normalized or "delta" in normalized:
        raise FabricSearchIngestionError(
            kind="unsupported_onelake_parquet_delta",
            message="OneLake Files indexer does not support Parquet or Delta table content.",
            operator_action="Use the Fabric SQL endpoint or materialize supported file formats in Files.",
        )


def _quote_sql_identifier(identifier: str) -> str:
    return f"[{identifier.replace(']', ']]')}]"


def _json_safe_value(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _sample_mapping(target_field: str, column: SourceColumn, evidence: str) -> FieldMapping:
    return FieldMapping(
        target_field=target_field,
        source_field=column.name,
        source_fields=(column.name,),
        transform="copy",
        confidence=0.68,
        evidence=(evidence,),
    )


def _looks_like_price(values: Sequence[Any]) -> bool:
    numeric = [_to_float(value) for value in values]
    numeric = [value for value in numeric if value is not None]
    return bool(numeric) and all(value >= 0 for value in numeric)


def _looks_like_rating(values: Sequence[Any]) -> bool:
    numeric = [_to_float(value) for value in values]
    numeric = [value for value in numeric if value is not None]
    return bool(numeric) and all(0 <= value <= 5 for value in numeric)


def _looks_like_currency(values: Sequence[Any]) -> bool:
    currency_pattern = re.compile(r"^[A-Z]{3}$")
    text_values = [str(value).strip().upper() for value in values]
    return bool(text_values) and all(currency_pattern.match(value) for value in text_values)


def _looks_like_availability(values: Sequence[Any]) -> bool:
    availability_markers = {
        "in_stock",
        "out_of_stock",
        "available",
        "unavailable",
        "backorder",
        "preorder",
    }
    normalized = {_normalize_name(str(value)) for value in values}
    return bool(normalized & {_normalize_name(value) for value in availability_markers})


def _to_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_name(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _optional(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _clean(value: str | None, default: str) -> str:
    return _optional(value) or default


def _bounded_int(value: str | None, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _build_search_url(settings: AISearchResourceSettings, path: str) -> str:
    endpoint = (settings.endpoint or "").rstrip("/")
    return f"{endpoint}{path}?api-version={settings.api_version}"


def _retry_delay_seconds(response: httpx.Response, attempt: int) -> float:
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            return max(float(retry_after), 0.1)
        except ValueError:
            pass
    return 0.5 * (2**attempt)


def _redact_resource_payloads(resources: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    redacted = {name: dict(payload) for name, payload in resources.items()}
    data_source = dict(redacted.get("data_source") or {})
    credentials = data_source.get("credentials")
    if isinstance(credentials, Mapping) and credentials.get("connectionString"):
        data_source["credentials"] = {"connectionString": "<redacted>"}
        redacted["data_source"] = data_source
    return redacted


def _http_error_response(operation: str, exc: httpx.HTTPStatusError) -> dict[str, Any]:
    status_code = exc.response.status_code
    kind = "http_error"
    if status_code == 404:
        kind = "not_found"
    elif status_code == 429:
        kind = "throttled"
    elif status_code in {401, 403}:
        kind = "permission_error"
    return {
        "status": "error",
        "operation": operation,
        "http_status": status_code,
        "error": {"kind": kind, "message": exc.response.text or str(exc)},
    }


def _runtime_error_response(operation: str, exc: Exception) -> dict[str, Any]:
    return {
        "status": "error",
        "operation": operation,
        "http_status": 500,
        "error": {"kind": "runtime", "message": str(exc)},
    }
