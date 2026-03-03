"""Product Truth Layer data models.

Pydantic v2 schemas for the core entities of the Product Truth Layer stored in
Cosmos DB (spec section 7.2).  All models support ``model_dump()`` for Cosmos
DB document serialisation.

>>> style = ProductStyle(id="S1", brand="Acme", modelName="Widget Pro", categoryId="cat-001")
>>> style.id
'S1'
>>> variant = ProductVariant(id="V1", styleId="S1", upc="012345678901", size="M", color="red")
>>> variant.styleId
'S1'
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from .product import CatalogProduct

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class EntityType(str, Enum):
    """Discriminator for style vs. variant entities."""

    STYLE = "style"
    VARIANT = "variant"


class AttributeSource(str, Enum):
    """Origin system for an attribute value."""

    PIM = "PIM"
    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


class SharePolicy(str, Enum):
    """Data-sharing policy for an attribute."""

    INTERNAL_ONLY = "internalOnly"
    ALLOWED_PARTNERS = "allowedPartners"
    PUBLIC = "public"


class AttributeStatus(str, Enum):
    """Lifecycle status of a proposed attribute."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"


class AuditAction(str, Enum):
    """Actions recorded in the audit trail."""

    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"
    WRITTEN_BACK = "written_back"


class GapReportTarget(str, Enum):
    """Completeness scoring target."""

    CATEGORY_ONLY = "category-only"
    UCP = "UCP"
    ACP = "ACP"


# ---------------------------------------------------------------------------
# Shared value objects
# ---------------------------------------------------------------------------


class Provenance(BaseModel):
    """Audit metadata tracking who created/updated a record and when."""

    model_config = ConfigDict(populate_by_name=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="createdAt",
    )
    created_by: str = Field("SYSTEM", alias="createdBy")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="updatedAt",
    )
    updated_by: str = Field("SYSTEM", alias="updatedBy")


# ---------------------------------------------------------------------------
# Core product graph entities
# ---------------------------------------------------------------------------


class ProductStyle(BaseModel):
    """Top-level product concept partitioned by ``categoryId`` in Cosmos DB.

    ``sourceRefs`` carries raw PIM identifiers for provenance so that the truth
    layer can always be traced back to its origin systems.

    >>> ps = ProductStyle(id="S1", brand="Nike", modelName="Air Max 90", categoryId="footwear")
    >>> ps.brand
    'Nike'
    >>> ps.variantIds
    []
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    brand: str
    model_name: str = Field(alias="modelName")
    category_id: str = Field(alias="categoryId")
    variant_ids: list[str] = Field(default_factory=list, alias="variantIds")
    asset_ids: list[str] = Field(default_factory=list, alias="assetIds")
    source_refs: list[str] = Field(
        default_factory=list,
        alias="sourceRefs",
        description="Raw PIM IDs for provenance.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="updatedAt",
    )

    def to_catalog_product(self) -> CatalogProduct:
        """Convert this style to a :class:`~holiday_peak_lib.schemas.product.CatalogProduct`.

        Provides backward-compatibility bridge for downstream consumers that
        still work with the legacy catalog schema.

        >>> ps = ProductStyle(id="S1", brand="Acme", modelName="Foo", categoryId="cat-1")
        >>> cp = ps.to_catalog_product()
        >>> cp.sku
        'S1'
        >>> cp.brand
        'Acme'
        """
        return CatalogProduct(
            sku=self.id,
            name=self.model_name,
            brand=self.brand,
            category=self.category_id,
            attributes={"sourceRefs": self.source_refs},
        )


class ProductVariant(BaseModel):
    """Size/colour/SKU variant linked to a :class:`ProductStyle`.

    >>> pv = ProductVariant(id="V1", styleId="S1", upc="012345678901", size="M", color="red")
    >>> pv.size
    'M'
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    style_id: str = Field(alias="styleId")
    upc: Optional[str] = None
    size: Optional[str] = None
    width: Optional[str] = None
    color: Optional[str] = None
    asset_ids: list[str] = Field(default_factory=list, alias="assetIds")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="updatedAt",
    )


# ---------------------------------------------------------------------------
# Attribute truth layer
# ---------------------------------------------------------------------------


class TruthAttribute(BaseModel):
    """Approved attribute in the truth store.

    ``status`` is always ``'official'`` for records in this model; use
    :class:`ProposedAttribute` for the candidate lifecycle.

    >>> ta = TruthAttribute(
    ...     entityType="style", entityId="S1", attributeKey="material",
    ...     value="leather", source="PIM"
    ... )
    >>> ta.status
    'official'
    """

    model_config = ConfigDict(populate_by_name=True)

    entity_type: EntityType = Field(alias="entityType")
    entity_id: str = Field(alias="entityId")
    attribute_key: str = Field(alias="attributeKey")
    value: Any
    unit: Optional[str] = None
    source: AttributeSource
    share_policy: SharePolicy = Field(SharePolicy.INTERNAL_ONLY, alias="sharePolicy")
    provenance: Provenance = Field(default_factory=Provenance)
    status: str = "official"


class ProposedAttribute(BaseModel):
    """Candidate attribute pending human-in-the-loop review.

    Extends :class:`TruthAttribute` fields with proposal-lifecycle fields.

    >>> pa = ProposedAttribute(
    ...     entityType="variant", entityId="V1", attributeKey="weight",
    ...     value=0.5, source="SYSTEM", confidence=0.87, modelRunId="run-42"
    ... )
    >>> pa.status
    <AttributeStatus.PROPOSED: 'proposed'>
    >>> pa.confidence
    0.87
    """

    model_config = ConfigDict(populate_by_name=True)

    # --- inherited fields (mirrors TruthAttribute) ---
    entity_type: EntityType = Field(alias="entityType")
    entity_id: str = Field(alias="entityId")
    attribute_key: str = Field(alias="attributeKey")
    value: Any
    unit: Optional[str] = None
    source: AttributeSource
    share_policy: SharePolicy = Field(SharePolicy.INTERNAL_ONLY, alias="sharePolicy")
    provenance: Provenance = Field(default_factory=Provenance)

    # --- proposal-specific fields ---
    status: AttributeStatus = AttributeStatus.PROPOSED
    confidence: float = Field(..., ge=0.0, le=1.0)
    model_run_id: str = Field(alias="modelRunId")
    evidence_refs: list[str] = Field(default_factory=list, alias="evidenceRefs")
    validation_errors: list[str] = Field(default_factory=list, alias="validationErrors")


# ---------------------------------------------------------------------------
# Gap report
# ---------------------------------------------------------------------------


class GapReport(BaseModel):
    """Completeness scoring output per product entity.

    >>> gr = GapReport(entityId="S1", completenessScore=0.75, target="UCP")
    >>> gr.completenessScore
    0.75
    >>> gr.missingKeys
    []
    """

    model_config = ConfigDict(populate_by_name=True)

    entity_id: str = Field(alias="entityId")
    missing_keys: list[str] = Field(default_factory=list, alias="missingKeys")
    invalid_keys: list[str] = Field(default_factory=list, alias="invalidKeys")
    completeness_score: float = Field(..., ge=0.0, le=1.0, alias="completenessScore")
    target: GapReportTarget


# ---------------------------------------------------------------------------
# Audit event
# ---------------------------------------------------------------------------


class AuditEvent(BaseModel):
    """Immutable change-log entry for the truth layer audit trail.

    >>> ae = AuditEvent(entityId="S1", action="proposed", actor="user-1")
    >>> ae.action
    <AuditAction.PROPOSED: 'proposed'>
    """

    model_config = ConfigDict(populate_by_name=True)

    entity_id: str = Field(alias="entityId")
    action: AuditAction
    actor: str
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="JSON bag: attribute key, old/new value, reason.",
    )


# ---------------------------------------------------------------------------
# Asset metadata
# ---------------------------------------------------------------------------


class AssetMetadata(BaseModel):
    """Digital asset reference stored in the ``assets`` Cosmos container.

    >>> am = AssetMetadata(id="A1", productId="S1", url="https://cdn.example.com/img.jpg", assetType="image")
    >>> am.assetType
    'image'
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str
    product_id: str = Field(alias="productId")
    url: str
    asset_type: str = Field(alias="assetType")
    mime_type: Optional[str] = Field(None, alias="mimeType")
    alt_text: Optional[str] = Field(None, alias="altText")
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="updatedAt",
    )


# ---------------------------------------------------------------------------
# Category schema
# ---------------------------------------------------------------------------


class CategorySchema(BaseModel):
    """Defines required and optional attributes per category.

    Stored in the ``schemas`` Cosmos container, partitioned by ``categoryId``.

    >>> cs = CategorySchema(categoryId="footwear", requiredKeys=["material", "closure"])
    >>> "material" in cs.required_keys
    True
    """

    model_config = ConfigDict(populate_by_name=True)

    category_id: str = Field(alias="categoryId")
    required_keys: list[str] = Field(default_factory=list, alias="requiredKeys")
    optional_keys: list[str] = Field(default_factory=list, alias="optionalKeys")
    protocol_overlays: dict[str, Any] = Field(
        default_factory=dict,
        alias="protocolOverlays",
        description="Protocol-specific field overrides keyed by protocol version.",
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="updatedAt",
    )
