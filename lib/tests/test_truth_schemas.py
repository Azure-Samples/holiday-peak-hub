"""Unit tests for the Product Truth Layer schemas (truth.py)."""

from datetime import datetime, timezone

import pytest
from holiday_peak_lib.schemas.truth import (
    AssetMetadata,
    AttributeSource,
    AttributeStatus,
    AuditAction,
    AuditEvent,
    CategorySchema,
    EntityType,
    GapReport,
    GapReportTarget,
    ProductStyle,
    ProductVariant,
    ProposedAttribute,
    Provenance,
    SharePolicy,
    TruthAttribute,
)


class TestProductStyle:
    """Tests for ProductStyle model."""

    def test_create_minimal(self):
        style = ProductStyle(id="S1", brand="Acme", modelName="Widget Pro", categoryId="cat-001")
        assert style.id == "S1"
        assert style.brand == "Acme"
        assert style.model_name == "Widget Pro"
        assert style.category_id == "cat-001"
        assert style.variant_ids == []
        assert style.asset_ids == []
        assert style.source_refs == []

    def test_create_full(self):
        style = ProductStyle(
            id="S2",
            brand="Nike",
            modelName="Air Max 90",
            categoryId="footwear",
            variantIds=["V1", "V2"],
            assetIds=["A1"],
            sourceRefs=["PIM-001"],
        )
        assert len(style.variant_ids) == 2
        assert style.source_refs == ["PIM-001"]

    def test_alias_population(self):
        """Both alias and Python name should work."""
        style_alias = ProductStyle(id="S3", brand="X", modelName="Y", categoryId="Z")
        style_python = ProductStyle(id="S3", brand="X", model_name="Y", category_id="Z")
        assert style_alias.model_name == style_python.model_name

    def test_updated_at_default(self):
        style = ProductStyle(id="S1", brand="B", modelName="M", categoryId="C")
        assert isinstance(style.updated_at, datetime)

    def test_model_dump(self):
        style = ProductStyle(id="S1", brand="B", modelName="M", categoryId="C")
        data = style.model_dump()
        assert data["id"] == "S1"
        assert "model_name" in data

    def test_to_catalog_product_bridge(self):
        style = ProductStyle(
            id="S1",
            brand="Acme",
            modelName="Pro Shoe",
            categoryId="footwear",
            sourceRefs=["PIM-001"],
        )
        cp = style.to_catalog_product()
        assert cp.sku == "S1"
        assert cp.name == "Pro Shoe"
        assert cp.brand == "Acme"
        assert cp.category == "footwear"
        assert cp.attributes["sourceRefs"] == ["PIM-001"]

    def test_missing_required_fields(self):
        with pytest.raises(Exception):
            ProductStyle(id="S1", brand="B")  # missing modelName, categoryId


class TestProductVariant:
    """Tests for ProductVariant model."""

    def test_create_minimal(self):
        variant = ProductVariant(id="V1", styleId="S1")
        assert variant.id == "V1"
        assert variant.style_id == "S1"
        assert variant.upc is None
        assert variant.size is None
        assert variant.color is None
        assert variant.asset_ids == []

    def test_create_full(self):
        variant = ProductVariant(
            id="V1",
            styleId="S1",
            upc="012345678901",
            size="M",
            width="D",
            color="red",
            assetIds=["A1", "A2"],
        )
        assert variant.upc == "012345678901"
        assert variant.width == "D"
        assert len(variant.asset_ids) == 2

    def test_model_dump(self):
        variant = ProductVariant(id="V1", styleId="S1", size="L")
        data = variant.model_dump()
        assert data["id"] == "V1"
        assert data["style_id"] == "S1"


class TestTruthAttribute:
    """Tests for TruthAttribute model."""

    def test_create_minimal(self):
        ta = TruthAttribute(
            entityType="style",
            entityId="S1",
            attributeKey="material",
            value="leather",
            source="PIM",
        )
        assert ta.entity_id == "S1"
        assert ta.attribute_key == "material"
        assert ta.value == "leather"
        assert ta.source == AttributeSource.PIM
        assert ta.status == "official"
        assert ta.share_policy == SharePolicy.INTERNAL_ONLY

    def test_entity_type_enum(self):
        ta = TruthAttribute(
            entityType="variant",
            entityId="V1",
            attributeKey="weight",
            value=0.5,
            source="SYSTEM",
        )
        assert ta.entity_type == EntityType.VARIANT

    def test_provenance_default(self):
        ta = TruthAttribute(
            entityType="style",
            entityId="S1",
            attributeKey="color",
            value="blue",
            source="HUMAN",
        )
        assert isinstance(ta.provenance, Provenance)
        assert ta.provenance.created_by == "SYSTEM"

    def test_optional_unit(self):
        ta = TruthAttribute(
            entityType="style",
            entityId="S1",
            attributeKey="weight",
            value=1.2,
            unit="kg",
            source="PIM",
        )
        assert ta.unit == "kg"

    def test_share_policy_variants(self):
        for policy in SharePolicy:
            ta = TruthAttribute(
                entityType="style",
                entityId="S1",
                attributeKey="k",
                value="v",
                source="PIM",
                sharePolicy=policy.value,
            )
            assert ta.share_policy == policy


class TestProposedAttribute:
    """Tests for ProposedAttribute model."""

    def test_create_minimal(self):
        pa = ProposedAttribute(
            entityType="variant",
            entityId="V1",
            attributeKey="weight",
            value=0.5,
            source="SYSTEM",
            confidence=0.87,
            modelRunId="run-42",
        )
        assert pa.status == AttributeStatus.PROPOSED
        assert pa.confidence == 0.87
        assert pa.model_run_id == "run-42"
        assert pa.evidence_refs == []
        assert pa.validation_errors == []

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            ProposedAttribute(
                entityType="style",
                entityId="S1",
                attributeKey="k",
                value="v",
                source="PIM",
                confidence=1.5,  # out of range
                modelRunId="run-1",
            )
        with pytest.raises(Exception):
            ProposedAttribute(
                entityType="style",
                entityId="S1",
                attributeKey="k",
                value="v",
                source="PIM",
                confidence=-0.1,  # out of range
                modelRunId="run-1",
            )

    def test_status_transitions(self):
        for status in AttributeStatus:
            pa = ProposedAttribute(
                entityType="style",
                entityId="S1",
                attributeKey="k",
                value="v",
                source="PIM",
                confidence=0.9,
                modelRunId="run-1",
                status=status,
            )
            assert pa.status == status

    def test_with_evidence_and_errors(self):
        pa = ProposedAttribute(
            entityType="style",
            entityId="S1",
            attributeKey="material",
            value="leather",
            source="SYSTEM",
            confidence=0.6,
            modelRunId="run-99",
            evidenceRefs=["ev-1", "ev-2"],
            validationErrors=["value too short"],
        )
        assert len(pa.evidence_refs) == 2
        assert pa.validation_errors[0] == "value too short"

    def test_model_dump(self):
        pa = ProposedAttribute(
            entityType="style",
            entityId="S1",
            attributeKey="k",
            value="v",
            source="PIM",
            confidence=0.8,
            modelRunId="run-1",
        )
        data = pa.model_dump()
        assert data["confidence"] == 0.8


class TestGapReport:
    """Tests for GapReport model."""

    def test_create_minimal(self):
        gr = GapReport(entityId="S1", completenessScore=0.75, target="UCP")
        assert gr.entity_id == "S1"
        assert gr.completeness_score == 0.75
        assert gr.target == GapReportTarget.UCP
        assert gr.missing_keys == []
        assert gr.invalid_keys == []

    def test_score_bounds(self):
        with pytest.raises(Exception):
            GapReport(entityId="S1", completenessScore=1.1, target="UCP")
        with pytest.raises(Exception):
            GapReport(entityId="S1", completenessScore=-0.1, target="UCP")

    def test_with_gaps(self):
        gr = GapReport(
            entityId="S2",
            completenessScore=0.5,
            target="category-only",
            missingKeys=["color", "size"],
            invalidKeys=["weight"],
        )
        assert len(gr.missing_keys) == 2
        assert "weight" in gr.invalid_keys

    def test_target_enum(self):
        for target in GapReportTarget:
            gr = GapReport(entityId="E1", completenessScore=1.0, target=target)
            assert gr.target == target


class TestAuditEvent:
    """Tests for AuditEvent model."""

    def test_create_minimal(self):
        ae = AuditEvent(entityId="S1", action="proposed", actor="user-1")
        assert ae.entity_id == "S1"
        assert ae.action == AuditAction.PROPOSED
        assert ae.actor == "user-1"
        assert ae.details == {}

    def test_timestamp_default(self):
        ae = AuditEvent(entityId="S1", action="approved", actor="reviewer")
        assert isinstance(ae.timestamp, datetime)

    def test_all_actions(self):
        for action in AuditAction:
            ae = AuditEvent(entityId="E1", action=action, actor="actor")
            assert ae.action == action

    def test_details_payload(self):
        ae = AuditEvent(
            entityId="S1",
            action="approved",
            actor="reviewer-99",
            details={
                "attributeKey": "material",
                "oldValue": None,
                "newValue": "leather",
                "reason": "Confirmed by QA",
            },
        )
        assert ae.details["attributeKey"] == "material"
        assert ae.details["newValue"] == "leather"

    def test_model_dump(self):
        ae = AuditEvent(entityId="S1", action="exported", actor="system")
        data = ae.model_dump()
        assert data["entity_id"] == "S1"


class TestAssetMetadata:
    """Tests for AssetMetadata model."""

    def test_create_minimal(self):
        am = AssetMetadata(
            id="A1",
            productId="S1",
            url="https://cdn.example.com/img.jpg",
            assetType="image",
        )
        assert am.id == "A1"
        assert am.product_id == "S1"
        assert am.asset_type == "image"
        assert am.mime_type is None
        assert am.alt_text is None

    def test_create_full(self):
        am = AssetMetadata(
            id="A2",
            productId="S2",
            url="https://cdn.example.com/vid.mp4",
            assetType="video",
            mimeType="video/mp4",
            altText="Product demo video",
        )
        assert am.mime_type == "video/mp4"
        assert am.alt_text == "Product demo video"


class TestCategorySchema:
    """Tests for CategorySchema model."""

    def test_create_minimal(self):
        cs = CategorySchema(categoryId="footwear")
        assert cs.category_id == "footwear"
        assert cs.required_keys == []
        assert cs.optional_keys == []
        assert cs.protocol_overlays == {}

    def test_create_full(self):
        cs = CategorySchema(
            categoryId="footwear",
            requiredKeys=["material", "closure"],
            optionalKeys=["width", "lining"],
            protocolOverlays={"v2": {"closure": "fastening_type"}},
        )
        assert "material" in cs.required_keys
        assert "width" in cs.optional_keys
        assert cs.protocol_overlays["v2"]["closure"] == "fastening_type"


class TestProvenance:
    """Tests for Provenance value object."""

    def test_defaults(self):
        p = Provenance()
        assert p.created_by == "SYSTEM"
        assert p.updated_by == "SYSTEM"
        assert isinstance(p.created_at, datetime)

    def test_custom_values(self):
        now = datetime.now(timezone.utc)
        p = Provenance(
            createdAt=now,
            createdBy="user-1",
            updatedAt=now,
            updatedBy="user-2",
        )
        assert p.created_by == "user-1"
        assert p.updated_by == "user-2"


class TestSchemaExports:
    """Ensure all models are exported from the schemas package."""

    def test_package_exports(self):
        from holiday_peak_lib import schemas

        for name in [
            "ProductStyle",
            "ProductVariant",
            "TruthAttribute",
            "ProposedAttribute",
            "GapReport",
            "AuditEvent",
            "AssetMetadata",
            "CategorySchema",
            "Provenance",
            "EntityType",
            "AttributeSource",
            "SharePolicy",
            "AttributeStatus",
            "AuditAction",
            "GapReportTarget",
        ]:
            assert hasattr(schemas, name), f"{name} not exported from schemas"
