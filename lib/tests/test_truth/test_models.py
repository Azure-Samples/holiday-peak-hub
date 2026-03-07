"""Tests for Product Truth Layer data models (Issue #90, #92)."""

import pytest

from holiday_peak_lib.truth.models import (
    AssetMetadata,
    AttributeStatus,
    AuditEvent,
    AuditEventType,
    CategorySchema,
    GapReport,
    MappingDocument,
    ProductStyle,
    ProductVariant,
    ProposedAttribute,
    TenantConfig,
    TruthAttribute,
)


class TestProductStyle:
    """Tests for ProductStyle model."""

    def test_create_with_required_fields(self):
        style = ProductStyle(
            categoryId="apparel",
            name="Classic T-Shirt",
            source_system="pim",
            source_id="pim-123",
        )
        assert style.category_id == "apparel"
        assert style.name == "Classic T-Shirt"
        assert style.source_system == "pim"
        assert style.id is not None
        assert style.style_id is not None

    def test_ids_are_unique(self):
        s1 = ProductStyle(categoryId="apparel", name="A", source_system="pim", source_id="1")
        s2 = ProductStyle(categoryId="apparel", name="B", source_system="pim", source_id="2")
        assert s1.id != s2.id

    def test_serialise_deserialise(self):
        style = ProductStyle(
            categoryId="apparel",
            name="Polo",
            source_system="dam",
            source_id="dam-1",
            tags=["summer"],
        )
        data = style.model_dump(by_alias=True)
        restored = ProductStyle(**data)
        assert restored.category_id == style.category_id
        assert restored.tags == ["summer"]


class TestProductVariant:
    """Tests for ProductVariant model."""

    def test_create_variant(self):
        variant = ProductVariant(
            style_id="style-abc",
            categoryId="apparel",
            sku="SKU-001",
            size="M",
            color="Blue",
            source_system="pim",
            source_id="pim-v-1",
        )
        assert variant.sku == "SKU-001"
        assert variant.size == "M"
        assert variant.color == "Blue"
        assert variant.currency == "USD"


class TestTruthAttribute:
    """Tests for TruthAttribute model."""

    def test_create_truth_attribute(self):
        attr = TruthAttribute(
            entityId="style-abc",
            attribute_name="material",
            attribute_value="cotton",
            confidence=0.99,
            source_system="ai",
            source_id="run-001",
        )
        assert attr.status == AttributeStatus.APPROVED
        assert attr.confidence == 0.99

    def test_confidence_bounds(self):
        with pytest.raises(Exception):
            TruthAttribute(
                entityId="e",
                attribute_name="x",
                attribute_value="v",
                confidence=1.5,
                source_system="pim",
                source_id="1",
            )


class TestProposedAttribute:
    """Tests for ProposedAttribute model."""

    def test_create_proposed(self):
        prop = ProposedAttribute(
            entityId="style-xyz",
            attribute_name="color",
            attribute_value="Red",
            confidence=0.85,
            source_system="ai",
            source_id="run-002",
        )
        assert prop.status == AttributeStatus.PENDING
        assert prop.evidence_ids == []


class TestGapReport:
    """Tests for GapReport model."""

    def test_create_gap_report(self):
        report = GapReport(
            entityId="style-abc",
            categoryId="apparel",
            completeness_score=0.75,
            required_missing=["material"],
            optional_missing=["care_instructions"],
        )
        assert report.completeness_score == 0.75
        assert "material" in report.required_missing


class TestAuditEvent:
    """Tests for AuditEvent model."""

    def test_create_audit_event(self):
        event = AuditEvent(
            entityId="style-abc",
            event_type=AuditEventType.APPROVED,
            actor="reviewer@example.com",
            attribute_name="material",
            new_value="cotton",
            source_system="hitl",
            source_id="review-001",
        )
        assert event.event_type == AuditEventType.APPROVED
        assert event.actor == "reviewer@example.com"


class TestAssetMetadata:
    """Tests for AssetMetadata model."""

    def test_create_asset(self):
        asset = AssetMetadata(
            productId="style-abc",
            asset_type="image",
            url="https://cdn.example.com/image.jpg",
            source_system="dam",
            source_id="dam-img-1",
        )
        assert asset.asset_type == "image"
        assert asset.metadata == {}


class TestCategorySchema:
    """Tests for CategorySchema model."""

    def test_create_schema(self):
        schema = CategorySchema(
            categoryId="electronics",
            category_name="Electronics",
            required_attributes=["brand", "model_number"],
            optional_attributes=["color"],
        )
        assert schema.version == "1.0.0"
        assert "brand" in schema.required_attributes


class TestTenantConfig:
    """Tests for TenantConfig model (Issue #92)."""

    def test_create_tenant_config(self):
        config = TenantConfig(
            tenantId="tenant-001",
            tenant_name="Acme Retail",
        )
        assert config.auto_approve_threshold == 0.95
        assert config.human_review_threshold == 0.70
        assert config.tenant_id == "tenant-001"

    def test_custom_thresholds(self):
        config = TenantConfig(
            tenantId="t2",
            tenant_name="Beta Corp",
            auto_approve_threshold=0.90,
            human_review_threshold=0.60,
        )
        assert config.auto_approve_threshold == 0.90

    def test_threshold_bounds(self):
        with pytest.raises(Exception):
            TenantConfig(
                tenantId="t3",
                tenant_name="Bad Corp",
                auto_approve_threshold=1.5,
            )


class TestMappingDocument:
    """Tests for MappingDocument model (Issue #91)."""

    def test_create(self):
        md = MappingDocument(
            id="gs1:2024.1",
            protocol="gs1",
            protocolVersion="2024.1",
            mappings={"color": "ColourCode"},
        )
        assert md.protocol == "gs1"
        assert md.mappings["color"] == "ColourCode"

    def test_serializes_protocol_version_alias(self):
        md = MappingDocument(
            protocol="gs1",
            protocolVersion="2024.1",
        )
        data = md.model_dump(mode="json", by_alias=True)
        assert "protocolVersion" in data
