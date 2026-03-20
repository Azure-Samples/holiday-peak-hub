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


class SourceType(str, Enum):
    """Origin category for enrichment/search contextual data."""

    TEXT_ENRICHMENT = "text_enrichment"
    HYBRID = "hybrid"
    AI_REASONING = "ai_reasoning"
    PRODUCT_CONTEXT = "product_context"
    CATEGORY_INFERENCE = "category_inference"
    IMAGE_ANALYSIS = "image_analysis"


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
    source_type: Optional[SourceType] = Field(None, alias="sourceType")
    source_assets: list[str] = Field(default_factory=list, alias="sourceAssets")
    original_data: dict[str, Any] = Field(default_factory=dict, alias="originalData")
    enriched_data: dict[str, Any] = Field(default_factory=dict, alias="enrichedData")
    reasoning: Optional[str] = None


class ProductEnrichmentProposal(ProposedAttribute):
    """Compatibility model name for enrichment proposals.

    Keeps the existing ``ProposedAttribute`` payload contract while exposing a
    dedicated semantic type for enrichment/search pipelines.
    """

    model_config = ConfigDict(populate_by_name=True)


class IntentClassification(BaseModel):
    """Intent classification result for a search/enrichment request."""

    model_config = ConfigDict(populate_by_name=True)

    intent: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    entities: dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None


class SearchEnrichedProduct(BaseModel):
    """Shared search result enriched with context for downstream UI/services."""

    model_config = ConfigDict(populate_by_name=True)

    sku: str
    score: Optional[float] = Field(None, ge=0.0, le=1.0)
    source_type: Optional[SourceType] = Field(None, alias="sourceType")
    source_assets: list[str] = Field(default_factory=list, alias="sourceAssets")
    original_data: dict[str, Any] = Field(default_factory=dict, alias="originalData")
    enriched_data: dict[str, Any] = Field(default_factory=dict, alias="enrichedData")
    intent_classification: Optional[IntentClassification] = Field(
        None,
        alias="intentClassification",
    )
    reasoning: Optional[str] = None


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


# ---------------------------------------------------------------------------
# Export models
# ---------------------------------------------------------------------------


class ExportJob(BaseModel):
    """An export job request consumed from the export-jobs Event Hub topic.

    >>> ej = ExportJob(jobId="j1", entityId="S1", protocol="UCP")
    >>> ej.protocol
    'UCP'
    """

    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")
    entity_id: str = Field(alias="entityId")
    protocol: str
    partner_id: Optional[str] = Field(None, alias="partnerId")
    requested_by: Optional[str] = Field(None, alias="requestedBy")
    requested_at: Optional[datetime] = Field(None, alias="requestedAt")
    options: dict[str, Any] = Field(default_factory=dict)


class ExportResult(BaseModel):
    """Result of a completed export job.

    >>> er = ExportResult(jobId="j1", entityId="S1", protocol="UCP", payload={})
    >>> er.status
    'completed'
    """

    model_config = ConfigDict(populate_by_name=True)

    job_id: str = Field(alias="jobId")
    entity_id: str = Field(alias="entityId")
    protocol: str
    status: str = "completed"
    payload: dict[str, Any] = Field(default_factory=dict)
    exported_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        alias="exportedAt",
    )
    errors: list[str] = Field(default_factory=list)
