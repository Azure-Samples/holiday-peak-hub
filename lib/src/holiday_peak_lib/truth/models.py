"""Product Truth Layer — data models.

Defines Pydantic v2 models for the Product Graph (Issue #90, #92).
All models track ``source_system`` and ``source_id`` to satisfy the
"never generate data without source references" rule.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AttributeStatus(str, Enum):
    """Lifecycle status of a TruthAttribute or ProposedAttribute."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class AuditEventType(str, Enum):
    """Types of events in the audit trail."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"
    INGESTED = "ingested"
    UPDATED = "updated"


# ---------------------------------------------------------------------------
# ProductStyle (Issue #90)
# ---------------------------------------------------------------------------


class ProductStyle(BaseModel):
    """Top-level product concept partitioned by ``categoryId``.

    A *style* groups all variants (sizes, colours, SKUs) under a single
    canonical product identity. Documents are stored in the ``products``
    Cosmos DB container.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    style_id: str = Field(default_factory=_new_id)
    category_id: str = Field(..., alias="categoryId")
    name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    source_system: str
    source_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# ProductVariant (Issue #90)
# ---------------------------------------------------------------------------


class ProductVariant(BaseModel):
    """Size/colour/SKU variant linked to a :class:`ProductStyle`.

    Stored in the same ``products`` container, partitioned by
    ``categoryId`` (inherited from the parent style).
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    variant_id: str = Field(default_factory=_new_id)
    style_id: str
    category_id: str = Field(..., alias="categoryId")
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    inventory_count: int = 0
    source_system: str
    source_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    attributes: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# TruthAttribute (Issue #90)
# ---------------------------------------------------------------------------


class TruthAttribute(BaseModel):
    """Approved, canonical attribute stored in ``attributes_truth``.

    Partitioned by ``entityId`` (the product style or variant ID).
    Tracks ``confidence``, ``source_system``, and ``source_id`` to
    satisfy traceability requirements.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    entity_id: str = Field(..., alias="entityId")
    attribute_name: str
    attribute_value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source_system: str
    source_id: str
    status: AttributeStatus = AttributeStatus.APPROVED
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# ProposedAttribute (Issue #90)
# ---------------------------------------------------------------------------


class ProposedAttribute(BaseModel):
    """Candidate attribute pending human-in-the-loop review.

    Stored in ``attributes_proposed``, partitioned by ``entityId``.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    entity_id: str = Field(..., alias="entityId")
    attribute_name: str
    attribute_value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source_system: str
    source_id: str
    status: AttributeStatus = AttributeStatus.PENDING
    reviewer: Optional[str] = None
    review_note: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    evidence_ids: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# GapReport (Issue #90)
# ---------------------------------------------------------------------------


class GapReport(BaseModel):
    """Completeness scoring output per product style."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    entity_id: str = Field(..., alias="entityId")
    category_id: str = Field(..., alias="categoryId")
    completeness_score: float = Field(ge=0.0, le=1.0)
    required_missing: list[str] = Field(default_factory=list)
    optional_missing: list[str] = Field(default_factory=list)
    computed_at: datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# AuditEvent (Issue #90)
# ---------------------------------------------------------------------------


class AuditEvent(BaseModel):
    """Immutable audit-trail entry stored in the ``audit`` container.

    Partitioned by ``entityId``.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    entity_id: str = Field(..., alias="entityId")
    event_type: AuditEventType
    actor: str
    attribute_name: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    source_system: str
    source_id: str
    occurred_at: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# AssetMetadata (Issue #90)
# ---------------------------------------------------------------------------


class AssetMetadata(BaseModel):
    """Digital asset reference stored in the ``assets`` container.

    Partitioned by ``productId``.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    product_id: str = Field(..., alias="productId")
    asset_type: str
    url: str
    alt_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    file_size_bytes: Optional[int] = None
    source_system: str
    source_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# CategorySchema (Issue #90)
# ---------------------------------------------------------------------------


class CategorySchema(BaseModel):
    """Category schema defining required/optional attributes per category.

    Stored in the ``schemas`` Cosmos DB container, partitioned by
    ``categoryId``.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    category_id: str = Field(..., alias="categoryId")
    category_name: str
    version: str = "1.0.0"
    required_attributes: list[str] = Field(default_factory=list)
    optional_attributes: list[str] = Field(default_factory=list)
    attribute_types: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# TenantConfig (Issue #92)
# ---------------------------------------------------------------------------


class TenantConfig(BaseModel):
    """Tenant configuration document stored in the ``config`` container.

    Partitioned by ``tenantId``.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    tenant_id: str = Field(..., alias="tenantId")
    tenant_name: str
    auto_approve_threshold: float = Field(default=0.95, ge=0.0, le=1.0)
    human_review_threshold: float = Field(default=0.70, ge=0.0, le=1.0)
    enabled_categories: list[str] = Field(default_factory=list)
    source_systems: list[str] = Field(default_factory=list)
    export_protocols: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    settings: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# MappingDocument (Issue #91)
# ---------------------------------------------------------------------------


class MappingDocument(BaseModel):
    """Canonical-to-protocol field mappings stored in ``mappings``.

    Cosmos DB partition key: ``/protocolVersion``.
    ``id`` is formatted as ``"{protocol}:{version}"`` for deterministic reads.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    protocol: str
    protocol_version: str = Field(..., alias="protocolVersion")
    mappings: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
