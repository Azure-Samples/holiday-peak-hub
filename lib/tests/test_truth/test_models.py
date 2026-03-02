"""Tests for truth-layer data models."""

import pytest
from holiday_peak_lib.truth.models import (
    AssetMetadata,
    AuditEvent,
    CategorySchema,
    GapReport,
    MappingDocument,
    ProductStyle,
    ProductVariant,
    ProposedAttribute,
    TenantConfig,
    TruthAttribute,
)


class TestProductVariant:
    def test_create_with_required_fields(self):
        v = ProductVariant(
            style_id="s1",
            sku="SKU-001",
            source_system="pim",
            source_id="ext-001",
        )
        assert v.sku == "SKU-001"
        assert v.style_id == "s1"
        assert v.source_system == "pim"
        assert v.id is not None

    def test_optional_size_and_color(self):
        v = ProductVariant(
            style_id="s1",
            sku="SKU-001",
            source_system="pim",
            source_id="ext-001",
            size="M",
            color="blue",
        )
        assert v.size == "M"
        assert v.color == "blue"

    def test_attributes_default_empty(self):
        v = ProductVariant(
            style_id="s1",
            sku="SKU-001",
            source_system="pim",
            source_id="ext-001",
        )
        assert v.attributes == {}


class TestProductStyle:
    def test_create_minimal(self):
        ps = ProductStyle(
            category_id="CAT-1",
            name="Blue Jacket",
            source_system="pim",
            source_id="ext-s1",
        )
        assert ps.name == "Blue Jacket"
        assert ps.category_id == "CAT-1"

    def test_serializes_with_alias(self):
        ps = ProductStyle(
            category_id="CAT-1",
            name="Blue Jacket",
            source_system="pim",
            source_id="ext-s1",
        )
        data = ps.model_dump(mode="json", by_alias=True)
        assert "categoryId" in data
        assert data["categoryId"] == "CAT-1"

    def test_variants_default_empty(self):
        ps = ProductStyle(
            category_id="CAT-1",
            name="Jacket",
            source_system="pim",
            source_id="ext-s1",
        )
        assert ps.variants == []

    def test_roundtrip_validation(self):
        ps = ProductStyle(
            id="s1",
            category_id="CAT-1",
            name="Jacket",
            source_system="pim",
            source_id="ext-s1",
        )
        data = ps.model_dump(mode="json", by_alias=True)
        restored = ProductStyle.model_validate(data)
        assert restored.id == "s1"
        assert restored.category_id == "CAT-1"


class TestTruthAttribute:
    def test_create(self):
        ta = TruthAttribute(
            entity_id="s1",
            name="color",
            value="blue",
            confidence=0.99,
            source_system="enrichment",
            source_id="job-1",
        )
        assert ta.confidence == 0.99
        assert ta.name == "color"

    def test_confidence_range_invalid(self):
        with pytest.raises(Exception):
            TruthAttribute(
                entity_id="s1",
                name="color",
                value="blue",
                confidence=1.5,
                source_system="enrichment",
                source_id="job-1",
            )

    def test_serializes_entity_id_alias(self):
        ta = TruthAttribute(
            entity_id="s1",
            name="color",
            value="blue",
            confidence=0.9,
            source_system="enrichment",
            source_id="job-1",
        )
        data = ta.model_dump(mode="json", by_alias=True)
        assert "entityId" in data
        assert data["entityId"] == "s1"


class TestProposedAttribute:
    def test_default_status_pending(self):
        pa = ProposedAttribute(
            entity_id="s1",
            name="material",
            value="cotton",
            confidence=0.8,
            source_system="ai",
            source_id="run-42",
        )
        assert pa.status == "pending"

    def test_can_override_status(self):
        pa = ProposedAttribute(
            entity_id="s1",
            name="material",
            value="cotton",
            confidence=0.8,
            source_system="ai",
            source_id="run-42",
            status="approved",
        )
        assert pa.status == "approved"

    def test_roundtrip(self):
        pa = ProposedAttribute(
            entity_id="s1",
            name="material",
            value="cotton",
            confidence=0.8,
            source_system="ai",
            source_id="run-42",
        )
        data = pa.model_dump(mode="json", by_alias=True)
        restored = ProposedAttribute.model_validate(data)
        assert restored.entity_id == "s1"


class TestGapReport:
    def test_create(self):
        gr = GapReport(
            entity_id="s1",
            score=0.75,
            missing_required=["weight"],
            missing_optional=["color"],
        )
        assert gr.score == 0.75
        assert "weight" in gr.missing_required


class TestAuditEvent:
    def test_create(self):
        ae = AuditEvent(
            entity_id="s1",
            action="approve",
            actor="user@example.com",
            changes={"status": "approved"},
        )
        assert ae.action == "approve"
        assert ae.actor == "user@example.com"

    def test_serializes_entity_id_alias(self):
        ae = AuditEvent(
            entity_id="s1",
            action="approve",
            actor="user@example.com",
        )
        data = ae.model_dump(mode="json", by_alias=True)
        assert "entityId" in data


class TestAssetMetadata:
    def test_create(self):
        am = AssetMetadata(
            product_id="s1",
            url="https://cdn/img.jpg",
            asset_type="image",
            source_system="dam",
            source_id="dam-001",
        )
        assert am.asset_type == "image"

    def test_serializes_product_id_alias(self):
        am = AssetMetadata(
            product_id="s1",
            url="https://cdn/img.jpg",
            asset_type="image",
            source_system="dam",
            source_id="dam-001",
        )
        data = am.model_dump(mode="json", by_alias=True)
        assert "productId" in data
        assert data["productId"] == "s1"


class TestCategorySchema:
    def test_create(self):
        cs = CategorySchema(
            category_id="CAT-1",
            required_attributes=["color", "size"],
            optional_attributes=["material"],
        )
        assert "color" in cs.required_attributes

    def test_serializes_category_id_alias(self):
        cs = CategorySchema(category_id="CAT-1")
        data = cs.model_dump(mode="json", by_alias=True)
        assert "categoryId" in data


class TestMappingDocument:
    def test_create(self):
        md = MappingDocument(
            id="gs1:2024.1",
            protocol="gs1",
            protocol_version="2024.1",
            mappings={"color": "ColourCode"},
        )
        assert md.protocol == "gs1"
        assert md.mappings["color"] == "ColourCode"

    def test_serializes_protocol_version_alias(self):
        md = MappingDocument(
            protocol="gs1",
            protocol_version="2024.1",
        )
        data = md.model_dump(mode="json", by_alias=True)
        assert "protocolVersion" in data


class TestTenantConfig:
    def test_create(self):
        tc = TenantConfig(
            id="tenant-1",
            tenant_id="tenant-1",
            settings={"locale": "en-US"},
        )
        assert tc.tenant_id == "tenant-1"
        assert tc.settings["locale"] == "en-US"

    def test_serializes_tenant_id_alias(self):
        tc = TenantConfig(tenant_id="tenant-1")
        data = tc.model_dump(mode="json", by_alias=True)
        assert "tenantId" in data
        assert data["tenantId"] == "tenant-1"
