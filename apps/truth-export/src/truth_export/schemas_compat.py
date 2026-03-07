"""Compatibility layer for truth schemas used by truth-export.

Prefers canonical models from ``holiday_peak_lib.schemas.truth`` when available.
Falls back to minimal local models for environments pinned to older
``holiday-peak-lib`` releases that do not include the truth schema module.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from holiday_peak_lib.schemas.truth import (  # type: ignore
        AuditAction,
        AuditEvent,
        ExportResult,
        ProductStyle,
        TruthAttribute,
    )
else:
    try:
        from holiday_peak_lib.schemas.truth import (  # type: ignore
            AuditAction,
            AuditEvent,
            ExportResult,
            ProductStyle,
            TruthAttribute,
        )
    except ModuleNotFoundError:

        class AuditAction(str, Enum):
            EXPORTED = "exported"

        class ProductStyle(BaseModel):
            model_config = ConfigDict(populate_by_name=True)

            id: str
            brand: str = ""
            model_name: str = Field(default="", alias="modelName")
            category_id: str = Field(default="", alias="categoryId")
            variant_ids: list[str] = Field(default_factory=list, alias="variantIds")
            asset_ids: list[str] = Field(default_factory=list, alias="assetIds")
            source_refs: list[str] = Field(default_factory=list, alias="sourceRefs")

        class TruthAttribute(BaseModel):
            model_config = ConfigDict(populate_by_name=True)

            entity_type: str = Field(default="style", alias="entityType")
            entity_id: str = Field(alias="entityId")
            attribute_key: str = Field(alias="attributeKey")
            value: Any
            source: str = "SYSTEM"

        class ExportResult(BaseModel):
            model_config = ConfigDict(populate_by_name=True)

            job_id: str = Field(alias="jobId")
            entity_id: str = Field(alias="entityId")
            protocol: str
            status: str
            payload: dict[str, Any] = Field(default_factory=dict)
            errors: list[str] = Field(default_factory=list)

        class AuditEvent(BaseModel):
            model_config = ConfigDict(populate_by_name=True)

            entity_id: str = Field(alias="entityId")
            action: AuditAction
            actor: str
            timestamp: datetime
            details: dict[str, Any] = Field(default_factory=dict)
