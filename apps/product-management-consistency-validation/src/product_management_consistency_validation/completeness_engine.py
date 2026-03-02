"""Schema-driven completeness engine for product gap analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, Field


class FieldDefinition(BaseModel):
    """Definition of a single field in a category schema."""

    field_name: str
    field_path: str  # dot-notation path, e.g. "attributes.color"
    expected_type: str  # 'str', 'float', 'int', 'bool', 'list', 'dict'
    required: bool = True
    enrichable: bool = True
    weight: float = 1.0


class CategorySchema(BaseModel):
    """Schema describing required/optional fields for a product category."""

    category_id: str
    schema_version: str
    fields: list[FieldDefinition] = Field(default_factory=list)


class FieldGap(BaseModel):
    """Gap detail for a single field in a product."""

    field_name: str
    gap_type: str  # 'missing', 'invalid', 'below_quality'
    current_value: Optional[Any] = None
    expected_type: str
    enrichable: bool
    weight: float


class GapReport(BaseModel):
    """Completeness gap report produced per product evaluation."""

    entity_id: str
    category_id: str
    schema_version: str
    completeness_score: float
    total_fields: int
    filled_fields: int
    gaps: list[FieldGap] = Field(default_factory=list)
    enrichable_gaps: list[FieldGap] = Field(default_factory=list)
    evaluated_at: datetime


_TYPE_MAP: dict[str, type] = {
    "str": str,
    "float": float,
    "int": int,
    "bool": bool,
    "list": list,
    "dict": dict,
}


def _get_nested_value(data: dict[str, Any], path: str) -> Any:
    """Retrieve a value from a nested dict using a dot-notation path."""
    current: Any = data
    for part in path.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _is_empty(value: Any) -> bool:
    """Return True when a value is considered absent."""
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    if isinstance(value, (list, dict)) and len(value) == 0:
        return True
    return False


def _type_valid(value: Any, expected_type: str) -> bool:
    """Return True when *value* matches *expected_type*."""
    expected = _TYPE_MAP.get(expected_type)
    if expected is None:
        return True
    # Allow int where float is expected (int is a numeric subtype)
    if expected is float and isinstance(value, int):
        return True
    return isinstance(value, expected)


class CompletenessEngine:
    """Evaluate a product dict against a :class:`CategorySchema`."""

    def evaluate(
        self,
        entity_id: str,
        product_data: dict[str, Any],
        schema: CategorySchema,
    ) -> GapReport:
        """Score *product_data* and return a :class:`GapReport`.

        The completeness score is the ratio of filled field weight to total
        field weight (0.0 — 1.0).

        >>> from datetime import timezone
        >>> engine = CompletenessEngine()
        >>> schema = CategorySchema(
        ...     category_id="apparel",
        ...     schema_version="1.0",
        ...     fields=[
        ...         FieldDefinition(field_name="name", field_path="name",
        ...                         expected_type="str", weight=2.0),
        ...         FieldDefinition(field_name="price", field_path="price",
        ...                         expected_type="float", weight=1.0),
        ...     ],
        ... )
        >>> report = engine.evaluate("SKU-1", {"name": "Widget"}, schema)
        >>> round(report.completeness_score, 2)
        0.67
        >>> len(report.gaps)
        1
        """
        gaps: list[FieldGap] = []
        total_weight = sum(f.weight for f in schema.fields)
        filled_weight = 0.0
        filled_count = 0

        for field_def in schema.fields:
            value = _get_nested_value(product_data, field_def.field_path)

            if _is_empty(value):
                gap_type = "missing"
            elif not _type_valid(value, field_def.expected_type):
                gap_type = "invalid"
            else:
                gap_type = None

            if gap_type:
                gaps.append(
                    FieldGap(
                        field_name=field_def.field_name,
                        gap_type=gap_type,
                        current_value=value,
                        expected_type=field_def.expected_type,
                        enrichable=field_def.enrichable,
                        weight=field_def.weight,
                    )
                )
            else:
                filled_count += 1
                filled_weight += field_def.weight

        completeness_score = filled_weight / total_weight if total_weight > 0 else 1.0

        enrichable_gaps = [g for g in gaps if g.enrichable]

        return GapReport(
            entity_id=entity_id,
            category_id=schema.category_id,
            schema_version=schema.schema_version,
            completeness_score=round(completeness_score, 4),
            total_fields=len(schema.fields),
            filled_fields=filled_count,
            gaps=gaps,
            enrichable_gaps=enrichable_gaps,
            evaluated_at=datetime.now(tz=timezone.utc),
        )
