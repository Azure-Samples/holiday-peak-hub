"""Canonical category schema models used for completeness validation."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FieldType = Literal["string", "number", "enum", "list", "image", "boolean"]


class FieldDef(BaseModel):
    """Field definition for a canonical category schema."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type: FieldType
    required: bool = True
    enrichable: bool = True
    weight: float = Field(default=1.0, ge=0.0)
    allowed_values: list[str] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Field name must not be empty")
        return value

    @model_validator(mode="after")
    def validate_enum_allowed_values(self) -> "FieldDef":
        if self.type == "enum" and not self.allowed_values:
            raise ValueError("Enum fields require non-empty allowed_values")
        return self


class CategorySchema(BaseModel):
    """Canonical schema definition for a product category."""

    model_config = ConfigDict(extra="forbid")

    category_id: str
    label: str
    version: str
    fields: list[FieldDef]
    parent_category_id: str | None = None

    @field_validator("category_id", "label", "version")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Value must not be empty")
        return value

    @model_validator(mode="after")
    def validate_unique_field_names(self) -> "CategorySchema":
        names = [item.name for item in self.fields]
        if len(set(names)) != len(names):
            raise ValueError("Field names must be unique within a category schema")
        return self

    @property
    def schema_id(self) -> str:
        """Stable id used for Cosmos DB documents."""
        return f"{self.category_id}:{self.version}"

    def resolve_fields(self, parent_schema: "CategorySchema | None" = None) -> list[FieldDef]:
        """Resolve fields with optional parent inheritance.

        Child fields override parent fields by name.
        """
        if parent_schema is None:
            return list(self.fields)

        merged: dict[str, FieldDef] = {field.name: field for field in parent_schema.fields}
        for field in self.fields:
            merged[field.name] = field
        return list(merged.values())

    def to_cosmos_document(self) -> dict[str, Any]:
        """Serialize to a Cosmos DB compatible document."""
        payload = self.model_dump(mode="json")
        payload["id"] = self.schema_id
        return payload

    @classmethod
    def from_cosmos_document(cls, document: dict[str, Any]) -> "CategorySchema":
        """Deserialize from Cosmos DB document payload."""
        payload = dict(document)
        payload.pop("id", None)
        return cls.model_validate(payload)
