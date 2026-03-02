"""UCP schema and canonical category schemas (Issue #93).

Defines the Universal Catalog Protocol (UCP) attribute descriptor and
ships pre-built schemas for common retail categories.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# UCP attribute descriptor
# ---------------------------------------------------------------------------


class UcpAttribute(BaseModel):
    """Single attribute descriptor in a Universal Catalog Protocol schema."""

    model_config = ConfigDict(populate_by_name=True)

    name: str
    label: str
    data_type: Literal["string", "number", "boolean", "list", "object"] = "string"
    required: bool = False
    max_length: Optional[int] = None
    allowed_values: list[Any] = Field(default_factory=list)
    description: Optional[str] = None


class UcpSchema(BaseModel):
    """Universal Catalog Protocol schema for a product category."""

    model_config = ConfigDict(populate_by_name=True)

    category_id: str
    category_name: str
    version: str = "1.0.0"
    attributes: list[UcpAttribute] = Field(default_factory=list)

    # Convenience helpers ---------------------------------------------------

    @property
    def required_attribute_names(self) -> list[str]:
        """Return names of all required attributes."""
        return [a.name for a in self.attributes if a.required]

    @property
    def optional_attribute_names(self) -> list[str]:
        """Return names of all optional attributes."""
        return [a.name for a in self.attributes if not a.required]


# ---------------------------------------------------------------------------
# Canonical category schemas
# ---------------------------------------------------------------------------

CANONICAL_CATEGORY_SCHEMAS: dict[str, UcpSchema] = {
    "apparel": UcpSchema(
        category_id="apparel",
        category_name="Apparel",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="brand", label="Brand", required=True),
            UcpAttribute(name="gender", label="Gender", required=True,
                         allowed_values=["men", "women", "unisex", "kids"]),
            UcpAttribute(name="material", label="Material", required=True),
            UcpAttribute(name="size", label="Size", required=True),
            UcpAttribute(name="color", label="Color", required=True),
            UcpAttribute(name="care_instructions", label="Care Instructions"),
            UcpAttribute(name="country_of_origin", label="Country of Origin"),
            UcpAttribute(name="age_group", label="Age Group"),
            UcpAttribute(name="style", label="Style"),
        ],
    ),
    "footwear": UcpSchema(
        category_id="footwear",
        category_name="Footwear",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="brand", label="Brand", required=True),
            UcpAttribute(name="size", label="Size", required=True),
            UcpAttribute(name="width", label="Width"),
            UcpAttribute(name="material_upper", label="Upper Material", required=True),
            UcpAttribute(name="material_sole", label="Sole Material"),
            UcpAttribute(name="color", label="Color", required=True),
            UcpAttribute(name="closure_type", label="Closure Type"),
            UcpAttribute(name="heel_height_cm", label="Heel Height (cm)",
                         data_type="number"),
            UcpAttribute(name="gender", label="Gender",
                         allowed_values=["men", "women", "unisex", "kids"]),
        ],
    ),
    "electronics": UcpSchema(
        category_id="electronics",
        category_name="Electronics",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="brand", label="Brand", required=True),
            UcpAttribute(name="model_number", label="Model Number", required=True),
            UcpAttribute(name="voltage", label="Voltage", data_type="number"),
            UcpAttribute(name="wattage", label="Wattage", data_type="number"),
            UcpAttribute(name="connectivity", label="Connectivity",
                         data_type="list"),
            UcpAttribute(name="warranty_months", label="Warranty (months)",
                         data_type="number"),
            UcpAttribute(name="color", label="Color"),
            UcpAttribute(name="weight_kg", label="Weight (kg)", data_type="number"),
            UcpAttribute(name="dimensions_cm", label="Dimensions (cm)",
                         data_type="object"),
        ],
    ),
    "home_furniture": UcpSchema(
        category_id="home_furniture",
        category_name="Home Furniture",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="brand", label="Brand", required=True),
            UcpAttribute(name="material", label="Material", required=True),
            UcpAttribute(name="color", label="Color", required=True),
            UcpAttribute(name="dimensions_cm", label="Dimensions (cm)",
                         data_type="object", required=True),
            UcpAttribute(name="weight_kg", label="Weight (kg)", data_type="number"),
            UcpAttribute(name="assembly_required", label="Assembly Required",
                         data_type="boolean"),
            UcpAttribute(name="max_load_kg", label="Max Load (kg)",
                         data_type="number"),
            UcpAttribute(name="country_of_origin", label="Country of Origin"),
        ],
    ),
    "beauty": UcpSchema(
        category_id="beauty",
        category_name="Beauty & Personal Care",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="brand", label="Brand", required=True),
            UcpAttribute(name="volume_ml", label="Volume (ml)", data_type="number",
                         required=True),
            UcpAttribute(name="ingredients", label="Ingredients", data_type="list"),
            UcpAttribute(name="skin_type", label="Skin Type",
                         data_type="list"),
            UcpAttribute(name="fragrance", label="Fragrance"),
            UcpAttribute(name="cruelty_free", label="Cruelty Free",
                         data_type="boolean"),
            UcpAttribute(name="expiry_months", label="Shelf Life (months)",
                         data_type="number"),
        ],
    ),
}
