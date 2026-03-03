"""Tests for canonical category schemas and inheritance behavior."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from holiday_peak_lib.schemas.canonical import CategorySchema, FieldDef


class TestFieldDef:
    def test_enum_requires_allowed_values(self):
        with pytest.raises(Exception):
            FieldDef(name="size", type="enum")

    def test_valid_non_enum_field(self):
        field = FieldDef(name="brand", type="string", required=True, weight=1.0)
        assert field.name == "brand"
        assert field.enrichable is True


class TestCategorySchema:
    def test_unique_fields_required(self):
        with pytest.raises(Exception):
            CategorySchema(
                category_id="general",
                label="General",
                version="1.0",
                fields=[
                    FieldDef(name="title", type="string"),
                    FieldDef(name="title", type="string"),
                ],
            )

    def test_inheritance_resolution(self):
        parent = CategorySchema(
            category_id="general",
            label="General",
            version="1.0",
            fields=[
                FieldDef(name="title", type="string", required=True),
                FieldDef(name="brand", type="string", required=True),
            ],
        )
        child = CategorySchema(
            category_id="apparel",
            label="Apparel",
            version="1.0",
            parent_category_id="general",
            fields=[
                FieldDef(name="brand", type="string", required=False),
                FieldDef(
                    name="size",
                    type="enum",
                    required=True,
                    allowed_values=["S", "M", "L"],
                ),
            ],
        )

        resolved = child.resolve_fields(parent)
        names = {field.name: field for field in resolved}

        assert set(names) == {"title", "brand", "size"}
        assert names["brand"].required is False

    def test_cosmos_document_roundtrip(self):
        schema = CategorySchema(
            category_id="electronics",
            label="Electronics",
            version="1.0",
            fields=[FieldDef(name="warranty_months", type="number", required=True)],
            parent_category_id="general",
        )

        document = schema.to_cosmos_document()

        assert document["id"] == "electronics:1.0"
        assert document["category_id"] == "electronics"

        json.dumps(document)

        restored = CategorySchema.from_cosmos_document(document)
        assert restored.category_id == schema.category_id
        assert restored.version == schema.version


class TestSampleCategorySchemas:
    def test_sample_category_schema_files_are_valid(self):
        category_dir = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "holiday_peak_lib"
            / "schemas"
            / "categories"
        )

        expected_files = {"general.json", "apparel.json", "electronics.json"}
        actual_files = {path.name for path in category_dir.glob("*.json")}

        assert expected_files.issubset(actual_files)

        for name in expected_files:
            payload = json.loads((category_dir / name).read_text(encoding="utf-8"))
            schema = CategorySchema.model_validate(payload)
            assert schema.category_id
            assert schema.version
            assert schema.fields
