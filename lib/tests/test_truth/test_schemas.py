"""Tests for UCP schema and canonical category schemas (Issue #93)."""

from holiday_peak_lib.truth.schemas import (
    CANONICAL_CATEGORY_SCHEMAS,
    UcpAttribute,
    UcpSchema,
)


class TestUcpAttribute:
    def test_defaults(self):
        attr = UcpAttribute(name="brand", label="Brand")
        assert attr.data_type == "string"
        assert not attr.required
        assert attr.allowed_values == []

    def test_required_attribute(self):
        attr = UcpAttribute(name="size", label="Size", required=True)
        assert attr.required


class TestUcpSchema:
    def test_required_attribute_names(self):
        schema = UcpSchema(
            category_id="test",
            category_name="Test",
            attributes=[
                UcpAttribute(name="brand", label="Brand", required=True),
                UcpAttribute(name="color", label="Color"),
            ],
        )
        assert schema.required_attribute_names == ["brand"]
        assert schema.optional_attribute_names == ["color"]

    def test_empty_schema(self):
        schema = UcpSchema(category_id="empty", category_name="Empty")
        assert schema.required_attribute_names == []


class TestCanonicalCategorySchemas:
    def test_all_five_categories_present(self):
        expected = {"apparel", "footwear", "electronics", "home_furniture", "beauty"}
        assert expected == set(CANONICAL_CATEGORY_SCHEMAS.keys())

    def test_apparel_has_required_attributes(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["apparel"]
        required = schema.required_attribute_names
        assert "brand" in required
        assert "size" in required
        assert "color" in required

    def test_electronics_has_brand_required(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["electronics"]
        assert "brand" in schema.required_attribute_names

    def test_schemas_are_ucp_schema_instances(self):
        for schema in CANONICAL_CATEGORY_SCHEMAS.values():
            assert isinstance(schema, UcpSchema)

    def test_beauty_contains_volume(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["beauty"]
        names = [a.name for a in schema.attributes]
        assert "volume_ml" in names
