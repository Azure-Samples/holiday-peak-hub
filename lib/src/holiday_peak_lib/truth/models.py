"""Pydantic data models for the Product Truth Layer.

All models track ``source_system`` and ``source_id`` to satisfy the requirement
that no product data is generated without source references.  Documents are
kept lean (well under the 2 MB Cosmos DB item limit) by using references for
large data rather than embedding.
"""

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


def _new_id() -> str:
    return str(uuid4())


class ProductVariant(BaseModel):
    """A single size/colour/SKU variant linked to a :class:`ProductStyle`.

    >>> v = ProductVariant(id="v1", style_id="s1", sku="SKU-001",
    ...                    source_system="pim", source_id="ext-001")
    >>> v.sku
    'SKU-001'
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    style_id: str
    sku: str
    size: Optional[str] = None
    color: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_system: str
    source_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ProductStyle(BaseModel):
    """Top-level product concept partitioned by ``categoryId``.

    Cosmos DB partition key: ``/categoryId``

    >>> ps = ProductStyle(id="s1", category_id="CAT-1", name="Blue Jacket",
    ...                   source_system="pim", source_id="ext-s1")
    >>> ps.name
    'Blue Jacket'
    >>> ps.category_id
    'CAT-1'
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    category_id: str = Field(alias="categoryId", serialization_alias="categoryId")
    name: str
    brand: Optional[str] = None
    description: Optional[str] = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    variants: list[ProductVariant] = Field(default_factory=list)
    source_system: str
    source_id: str
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class TruthAttribute(BaseModel):
    """Official approved attribute stored in ``attributes_truth``.

    Cosmos DB partition key: ``/entityId``

    >>> ta = TruthAttribute(id="a1", entity_id="s1", name="color",
    ...                     value="blue", confidence=0.99,
    ...                     source_system="enrichment", source_id="job-1")
    >>> ta.confidence
    0.99
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    entity_id: str = Field(alias="entityId", serialization_alias="entityId")
    name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source_system: str
    source_id: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class ProposedAttribute(BaseModel):
    """Candidate attribute pending HITL review, stored in ``attributes_proposed``.

    Cosmos DB partition key: ``/entityId``

    >>> pa = ProposedAttribute(id="p1", entity_id="s1", name="material",
    ...                        value="cotton", confidence=0.8,
    ...                        source_system="ai", source_id="run-42")
    >>> pa.status
    'pending'
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    entity_id: str = Field(alias="entityId", serialization_alias="entityId")
    name: str
    value: Any
    confidence: float = Field(ge=0.0, le=1.0)
    source_system: str
    source_id: str
    status: str = "pending"
    proposed_at: datetime = Field(default_factory=_utcnow)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class GapReport(BaseModel):
    """Completeness scoring output per product.

    >>> gr = GapReport(id="g1", entity_id="s1", score=0.75,
    ...                missing_required=["weight"], missing_optional=["color"])
    >>> gr.score
    0.75
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    entity_id: str = Field(alias="entityId", serialization_alias="entityId")
    score: float = Field(ge=0.0, le=1.0)
    missing_required: list[str] = Field(default_factory=list)
    missing_optional: list[str] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=_utcnow)


class AuditEvent(BaseModel):
    """Immutable change log entry stored in ``audit``.

    Cosmos DB partition key: ``/entityId``

    >>> ae = AuditEvent(id="e1", entity_id="s1", action="approve",
    ...                 actor="user@example.com", changes={"status": "approved"})
    >>> ae.action
    'approve'
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    entity_id: str = Field(alias="entityId", serialization_alias="entityId")
    action: str
    actor: str
    changes: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=_utcnow)


class AssetMetadata(BaseModel):
    """Digital asset reference stored in ``assets``.

    Cosmos DB partition key: ``/productId``

    >>> am = AssetMetadata(id="as1", product_id="s1", url="https://cdn/img.jpg",
    ...                    asset_type="image", source_system="dam",
    ...                    source_id="dam-001")
    >>> am.asset_type
    'image'
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    product_id: str = Field(alias="productId", serialization_alias="productId")
    url: str
    asset_type: str
    source_system: str
    source_id: str
    created_at: datetime = Field(default_factory=_utcnow)


class CategorySchema(BaseModel):
    """Defines required and optional attributes per category, stored in ``schemas``.

    Cosmos DB partition key: ``/categoryId``

    >>> cs = CategorySchema(id="sc1", category_id="CAT-1",
    ...                     required_attributes=["color", "size"],
    ...                     optional_attributes=["material"])
    >>> "color" in cs.required_attributes
    True
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    category_id: str = Field(alias="categoryId", serialization_alias="categoryId")
    required_attributes: list[str] = Field(default_factory=list)
    optional_attributes: list[str] = Field(default_factory=list)
    attribute_definitions: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class MappingDocument(BaseModel):
    """Canonical-to-protocol field mappings stored in ``mappings``.

    Cosmos DB partition key: ``/protocolVersion``

    ``id`` is formatted as ``"{protocol}:{version}"`` for deterministic reads.

    >>> md = MappingDocument(id="gs1:2024.1", protocol="gs1",
    ...                      protocol_version="2024.1",
    ...                      mappings={"color": "ColourCode"})
    >>> md.protocol
    'gs1'
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    protocol: str
    protocol_version: str = Field(
        alias="protocolVersion", serialization_alias="protocolVersion"
    )
    mappings: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class TenantConfig(BaseModel):
    """Tenant configuration stored in ``config``.

    Cosmos DB partition key: ``/tenantId``

    ``id`` is equal to ``tenantId`` for deterministic reads.

    >>> tc = TenantConfig(id="tenant-1", tenant_id="tenant-1",
    ...                   settings={"locale": "en-US"})
    >>> tc.tenant_id
    'tenant-1'
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=_new_id)
    tenant_id: str = Field(alias="tenantId", serialization_alias="tenantId")
    settings: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
