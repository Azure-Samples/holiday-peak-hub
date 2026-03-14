"""Unit tests for the completeness engine and scoring logic."""

from __future__ import annotations

import pytest
from product_management_consistency_validation.completeness_engine import (
    CategorySchema,
    CompletenessEngine,
    FieldDefinition,
    GapReport,
    _get_nested_value,
    _is_empty,
    _type_valid,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _simple_schema(fields: list[dict]) -> CategorySchema:
    return CategorySchema(
        category_id="test-cat",
        schema_version="1.0",
        fields=[FieldDefinition(**f) for f in fields],
    )


# ---------------------------------------------------------------------------
# _get_nested_value
# ---------------------------------------------------------------------------


def test_get_nested_value_top_level():
    assert _get_nested_value({"name": "Widget"}, "name") == "Widget"


def test_get_nested_value_nested():
    data = {"attributes": {"color": "red"}}
    assert _get_nested_value(data, "attributes.color") == "red"


def test_get_nested_value_missing_returns_none():
    assert _get_nested_value({}, "attributes.color") is None


def test_get_nested_value_intermediate_not_dict():
    assert _get_nested_value({"attributes": "not-a-dict"}, "attributes.color") is None


# ---------------------------------------------------------------------------
# _is_empty
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, True),
        ("", True),
        ("  ", True),
        ([], True),
        ({}, True),
        ("hello", False),
        (0, False),
        (False, False),
        ([1], False),
        ({"k": "v"}, False),
    ],
)
def test_is_empty(value, expected):
    assert _is_empty(value) == expected


# ---------------------------------------------------------------------------
# _type_valid
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "value,expected_type,valid",
    [
        ("hello", "str", True),
        (3.14, "float", True),
        (1, "float", True),  # int is acceptable for float fields
        (1, "int", True),
        (True, "bool", True),
        ([], "list", True),
        ({}, "dict", True),
        (3.14, "str", False),
        ("hello", "float", False),
        (3.14, "unknown_type", True),  # unknown type is permissive
    ],
)
def test_type_valid(value, expected_type, valid):
    assert _type_valid(value, expected_type) == valid


# ---------------------------------------------------------------------------
# CompletenessEngine — basic scoring
# ---------------------------------------------------------------------------


def test_perfect_score_all_fields_present():
    engine = CompletenessEngine()
    schema = _simple_schema(
        [
            {"field_name": "name", "field_path": "name", "expected_type": "str"},
            {"field_name": "price", "field_path": "price", "expected_type": "float"},
        ]
    )
    report = engine.evaluate("SKU-1", {"name": "Widget", "price": 9.99}, schema)
    assert report.completeness_score == 1.0
    assert report.total_fields == 2
    assert report.filled_fields == 2
    assert report.gaps == []
    assert report.enrichable_gaps == []


def test_zero_score_all_fields_missing():
    engine = CompletenessEngine()
    schema = _simple_schema(
        [
            {"field_name": "name", "field_path": "name", "expected_type": "str"},
            {"field_name": "price", "field_path": "price", "expected_type": "float"},
        ]
    )
    report = engine.evaluate("SKU-1", {}, schema)
    assert report.completeness_score == 0.0
    assert report.total_fields == 2
    assert report.filled_fields == 0
    assert len(report.gaps) == 2


def test_partial_score_weighted():
    engine = CompletenessEngine()
    schema = _simple_schema(
        [
            {
                "field_name": "name",
                "field_path": "name",
                "expected_type": "str",
                "weight": 2.0,
            },
            {
                "field_name": "price",
                "field_path": "price",
                "expected_type": "float",
                "weight": 1.0,
            },
        ]
    )
    # Only name is present (weight 2 out of 3)
    report = engine.evaluate("SKU-1", {"name": "Widget"}, schema)
    assert abs(report.completeness_score - round(2.0 / 3.0, 4)) < 1e-6
    assert report.filled_fields == 1
    assert len(report.gaps) == 1
    assert report.gaps[0].field_name == "price"
    assert report.gaps[0].gap_type == "missing"


def test_invalid_type_gap():
    engine = CompletenessEngine()
    schema = _simple_schema(
        [
            {
                "field_name": "price",
                "field_path": "price",
                "expected_type": "float",
            }
        ]
    )
    report = engine.evaluate("SKU-1", {"price": "not-a-float"}, schema)
    assert report.completeness_score == 0.0
    assert report.gaps[0].gap_type == "invalid"
    assert report.gaps[0].current_value == "not-a-float"


def test_enrichable_gap_subset():
    engine = CompletenessEngine()
    schema = _simple_schema(
        [
            {
                "field_name": "name",
                "field_path": "name",
                "expected_type": "str",
                "enrichable": True,
            },
            {
                "field_name": "sku",
                "field_path": "sku",
                "expected_type": "str",
                "enrichable": False,
            },
        ]
    )
    report = engine.evaluate("SKU-1", {}, schema)
    assert len(report.gaps) == 2
    assert len(report.enrichable_gaps) == 1
    assert report.enrichable_gaps[0].field_name == "name"


def test_nested_field_path():
    engine = CompletenessEngine()
    schema = _simple_schema(
        [
            {
                "field_name": "color",
                "field_path": "attributes.color",
                "expected_type": "str",
            }
        ]
    )
    report = engine.evaluate("SKU-1", {"attributes": {"color": "red"}}, schema)
    assert report.completeness_score == 1.0
    assert report.gaps == []


def test_empty_schema_returns_perfect_score():
    engine = CompletenessEngine()
    schema = CategorySchema(category_id="empty", schema_version="1.0", fields=[])
    report = engine.evaluate("SKU-1", {}, schema)
    assert report.completeness_score == 1.0
    assert report.total_fields == 0


def test_gap_report_metadata():
    engine = CompletenessEngine()
    schema = CategorySchema(
        category_id="apparel",
        schema_version="2.1",
        fields=[FieldDefinition(field_name="name", field_path="name", expected_type="str")],
    )
    report = engine.evaluate("SKU-99", {"name": "Scarf"}, schema)
    assert report.entity_id == "SKU-99"
    assert report.category_id == "apparel"
    assert report.schema_version == "2.1"
    assert report.evaluated_at is not None


# ---------------------------------------------------------------------------
# CompletenessStorageAdapter — in-memory mock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_schema_returns_seeded_schema():
    from product_management_consistency_validation.adapters import (
        CompletenessStorageAdapter,
    )

    adapter = CompletenessStorageAdapter()
    schema = CategorySchema(
        category_id="electronics",
        schema_version="1.0",
        fields=[FieldDefinition(field_name="name", field_path="name", expected_type="str")],
    )
    adapter.seed_schema(schema)
    result = await adapter.get_schema("electronics")
    assert result is not None
    assert result.category_id == "electronics"


@pytest.mark.asyncio
async def test_get_schema_missing_returns_none():
    from product_management_consistency_validation.adapters import (
        CompletenessStorageAdapter,
    )

    adapter = CompletenessStorageAdapter()
    result = await adapter.get_schema("nonexistent")
    assert result is None


@pytest.mark.asyncio
async def test_store_gap_report_in_memory():
    from datetime import datetime, timezone

    from product_management_consistency_validation.adapters import (
        CompletenessStorageAdapter,
    )

    adapter = CompletenessStorageAdapter()
    report = GapReport(
        entity_id="SKU-1",
        category_id="test",
        schema_version="1.0",
        completeness_score=0.5,
        total_fields=2,
        filled_fields=1,
        gaps=[],
        enrichable_gaps=[],
        evaluated_at=datetime.now(tz=timezone.utc),
    )
    await adapter.store_gap_report(report)
    assert "SKU-1" in adapter._report_store
