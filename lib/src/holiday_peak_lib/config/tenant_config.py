"""Tenant configuration model for truth-layer behavior."""

from pydantic import BaseModel, Field


class TenantConfig(BaseModel):
    """Configuration governing truth-layer behavior per tenant.

    Stored in Cosmos DB ``config`` container (partition key: ``tenant_id``).
    Loaded once per request context and cached in Redis (hot memory).
    Falls back to sensible defaults when not explicitly configured.

    Attributes:
        tenant_id: Unique identifier for the tenant.
        auto_approve_threshold: Confidence score above which enrichment proposals
            are automatically approved without human review (0.0–1.0).
        enrichment_enabled: Master toggle to enable or disable AI enrichment for
            this tenant.
        writeback_enabled: Opt-in flag to enable PIM writeback of approved
            enrichments back to the source system.
        default_protocol: Default communication protocol for agent interactions
            (e.g. ``"acp"``).
        schema_version: Version tag of the tenant config schema used for
            forward-compatibility checks.
        allowed_enrichment_sources: List of accepted enrichment source identifiers
            (e.g. ``["ai", "manual"]``).
        completeness_weights: Per-field weight overrides used when computing the
            product completeness score. Keys are field names; values are floats
            between 0.0 and 1.0.
        hitl_required_fields: Field names that always require human-in-the-loop
            review, regardless of the confidence score.
    """

    tenant_id: str
    auto_approve_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Confidence score above which enrichment is auto-approved.",
    )
    enrichment_enabled: bool = Field(
        default=True,
        description="Master toggle for AI enrichment.",
    )
    writeback_enabled: bool = Field(
        default=False,
        description="Opt-in PIM writeback of approved enrichments.",
    )
    default_protocol: str = Field(
        default="acp",
        description="Default agent communication protocol.",
    )
    schema_version: str = Field(
        default="v1",
        description="Schema version for forward-compatibility checks.",
    )
    allowed_enrichment_sources: list[str] = Field(
        default_factory=lambda: ["ai", "manual"],
        description="Accepted enrichment source identifiers.",
    )
    completeness_weights: dict[str, float] = Field(
        default_factory=dict,
        description="Per-field weight overrides for completeness scoring.",
    )
    hitl_required_fields: list[str] = Field(
        default_factory=list,
        description="Fields that always require human review.",
    )

    def to_cosmos_document(self) -> dict:
        """Serialize the model to a Cosmos DB document.

        Returns:
            A dictionary with ``id`` and ``partition_key`` set to ``tenant_id``
            so the document can be upserted directly into the ``config`` container.
        """
        doc = self.model_dump()
        doc["id"] = self.tenant_id
        doc["partition_key"] = self.tenant_id
        return doc

    @classmethod
    def from_cosmos_document(cls, document: dict) -> "TenantConfig":
        """Deserialize a Cosmos DB document into a :class:`TenantConfig`.

        Args:
            document: Raw document dict retrieved from Cosmos DB.

        Returns:
            A validated :class:`TenantConfig` instance.
        """
        filtered = {
            k: v
            for k, v in document.items()
            if k not in ("id", "partition_key", "_rid", "_self", "_etag", "_attachments", "_ts")
        }
        return cls(**filtered)
