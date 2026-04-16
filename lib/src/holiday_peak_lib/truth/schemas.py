"""UCP schema and canonical category schemas (Issue #93).

Defines the Universal Catalog Protocol (UCP) attribute descriptor and
ships pre-built schemas for common retail categories.
"""

from __future__ import annotations

from typing import Any, Literal

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
    max_length: int | None = None
    allowed_values: list[Any] = Field(default_factory=list)
    description: str | None = None


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
            UcpAttribute(
                name="gender",
                label="Gender",
                required=True,
                allowed_values=["men", "women", "unisex", "kids"],
            ),
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
            UcpAttribute(name="heel_height_cm", label="Heel Height (cm)", data_type="number"),
            UcpAttribute(
                name="gender", label="Gender", allowed_values=["men", "women", "unisex", "kids"]
            ),
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
            UcpAttribute(name="connectivity", label="Connectivity", data_type="list"),
            UcpAttribute(name="warranty_months", label="Warranty (months)", data_type="number"),
            UcpAttribute(name="color", label="Color"),
            UcpAttribute(name="weight_kg", label="Weight (kg)", data_type="number"),
            UcpAttribute(name="dimensions_cm", label="Dimensions (cm)", data_type="object"),
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
            UcpAttribute(
                name="dimensions_cm", label="Dimensions (cm)", data_type="object", required=True
            ),
            UcpAttribute(name="weight_kg", label="Weight (kg)", data_type="number"),
            UcpAttribute(name="assembly_required", label="Assembly Required", data_type="boolean"),
            UcpAttribute(name="max_load_kg", label="Max Load (kg)", data_type="number"),
            UcpAttribute(name="country_of_origin", label="Country of Origin"),
        ],
    ),
    "beauty": UcpSchema(
        category_id="beauty",
        category_name="Beauty & Personal Care",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="brand", label="Brand", required=True),
            UcpAttribute(name="volume_ml", label="Volume (ml)", data_type="number", required=True),
            UcpAttribute(name="ingredients", label="Ingredients", data_type="list"),
            UcpAttribute(name="skin_type", label="Skin Type", data_type="list"),
            UcpAttribute(name="fragrance", label="Fragrance"),
            UcpAttribute(name="cruelty_free", label="Cruelty Free", data_type="boolean"),
            UcpAttribute(name="expiry_months", label="Shelf Life (months)", data_type="number"),
        ],
    ),
    "toys_games": UcpSchema(
        category_id="toys_games",
        category_name="Toys & Games",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="age_range", label="Age Range", required=True),
            UcpAttribute(name="material", label="Material", required=True),
            UcpAttribute(
                name="battery_required",
                label="Battery Required",
                data_type="boolean",
            ),
            UcpAttribute(name="educational", label="Educational", data_type="boolean"),
            UcpAttribute(
                name="safety_certification",
                label="Safety Certification",
                required=True,
            ),
        ],
    ),
    "sports_outdoors": UcpSchema(
        category_id="sports_outdoors",
        category_name="Sports & Outdoors",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="sport_type", label="Sport Type", required=True),
            UcpAttribute(name="material", label="Material", required=True),
            UcpAttribute(name="weight_kg", label="Weight (kg)", data_type="number"),
            UcpAttribute(name="weather_resistance", label="Weather Resistance"),
            UcpAttribute(name="size", label="Size", required=True),
        ],
    ),
    "books_media": UcpSchema(
        category_id="books_media",
        category_name="Books & Media",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="author", label="Author", required=True),
            UcpAttribute(
                name="format",
                label="Format",
                required=True,
                allowed_values=["hardcover", "paperback", "digital", "vinyl"],
            ),
            UcpAttribute(name="language", label="Language"),
            UcpAttribute(name="pages", label="Pages", data_type="number"),
            UcpAttribute(name="isbn", label="ISBN"),
            UcpAttribute(name="genre", label="Genre"),
        ],
    ),
    "jewelry_watches": UcpSchema(
        category_id="jewelry_watches",
        category_name="Jewelry & Watches",
        version="1.0.0",
        attributes=[
            UcpAttribute(
                name="material",
                label="Material",
                required=True,
                allowed_values=["gold", "silver", "platinum", "stainless_steel"],
            ),
            UcpAttribute(name="gemstone", label="Gemstone"),
            UcpAttribute(name="size", label="Size", required=True),
            UcpAttribute(
                name="water_resistance",
                label="Water Resistance",
                data_type="boolean",
            ),
            UcpAttribute(
                name="warranty_months",
                label="Warranty (months)",
                data_type="number",
                required=True,
            ),
        ],
    ),
    "food_gourmet": UcpSchema(
        category_id="food_gourmet",
        category_name="Food & Gourmet",
        version="1.0.0",
        attributes=[
            UcpAttribute(name="weight_g", label="Weight (g)", data_type="number", required=True),
            UcpAttribute(name="ingredients", label="Ingredients", data_type="list", required=True),
            UcpAttribute(name="allergens", label="Allergens", data_type="list"),
            UcpAttribute(name="organic", label="Organic", data_type="boolean"),
            UcpAttribute(
                name="shelf_life_days",
                label="Shelf Life (days)",
                data_type="number",
            ),
            UcpAttribute(
                name="country_of_origin",
                label="Country of Origin",
                required=True,
            ),
        ],
    ),
    "pet_supplies": UcpSchema(
        category_id="pet_supplies",
        category_name="Pet Supplies",
        version="1.0.0",
        attributes=[
            UcpAttribute(
                name="pet_type",
                label="Pet Type",
                required=True,
                allowed_values=["dog", "cat", "bird", "fish", "small_animal"],
            ),
            UcpAttribute(name="material", label="Material"),
            UcpAttribute(name="size", label="Size", required=True),
            UcpAttribute(name="weight_kg", label="Weight (kg)", data_type="number"),
            UcpAttribute(name="age_group", label="Age Group", required=True),
        ],
    ),
}


# ---------------------------------------------------------------------------
# Category alias resolution
# ---------------------------------------------------------------------------

_CATEGORY_ALIASES: dict[str, str] = {
    "clothes": "apparel",
    "clothing": "apparel",
    "clothes & apparel": "apparel",
    "cat-clothing": "apparel",
    "furniture": "home_furniture",
    "home & kitchen": "home_furniture",
    "cat-furniture": "home_furniture",
    "cat-home-kitchen": "home_furniture",
    "beauty & health": "beauty",
    "cat-beauty-health": "beauty",
    "sports & outdoors": "sports_outdoors",
    "cat-sports-outdoors": "sports_outdoors",
    "toys & games": "toys_games",
    "cat-toys-games": "toys_games",
    "books & media": "books_media",
    "cat-books-media": "books_media",
    "jewelry & watches": "jewelry_watches",
    "cat-jewelry-watches": "jewelry_watches",
    "food & gourmet": "food_gourmet",
    "cat-food-gourmet": "food_gourmet",
    "pet supplies": "pet_supplies",
    "cat-pet-supplies": "pet_supplies",
    "cat-electronics": "electronics",
}


def resolve_ucp_schema(category: str) -> UcpSchema | None:
    """Resolve a category string to a canonical UCP schema.

    Resolution order:
    1. Exact match in ``CANONICAL_CATEGORY_SCHEMAS``.
    2. Normalised key (lowercase, strip ``cat-`` prefix, replace
       spaces / ``&`` with ``_``).
    3. Alias lookup in ``_CATEGORY_ALIASES``.
    """
    if not category:
        return None

    # 1. Exact match
    if category in CANONICAL_CATEGORY_SCHEMAS:
        return CANONICAL_CATEGORY_SCHEMAS[category]

    # 2. Normalised key
    normalised = category.lower().strip()
    normalised = normalised.removeprefix("cat-")
    normalised = (
        normalised.replace(" & ", "_").replace("&", "_").replace(" ", "_").replace("-", "_")
    )
    if normalised in CANONICAL_CATEGORY_SCHEMAS:
        return CANONICAL_CATEGORY_SCHEMAS[normalised]

    # 3. Alias lookup
    lowered = category.lower().strip()
    canonical_key = _CATEGORY_ALIASES.get(lowered)
    if canonical_key is not None:
        return CANONICAL_CATEGORY_SCHEMAS.get(canonical_key)

    return None
