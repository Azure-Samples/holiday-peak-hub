"""Tests for UCP schema and canonical category schemas (Issue #93)."""

from holiday_peak_lib.truth.schemas import (
    CANONICAL_CATEGORY_SCHEMAS,
    UcpAttribute,
    UcpSchema,
    resolve_ucp_schema,
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
        expected = {
            "apparel",
            "footwear",
            "electronics",
            "home_furniture",
            "beauty",
            "toys_games",
            "sports_outdoors",
            "books_media",
            "jewelry_watches",
            "food_gourmet",
            "pet_supplies",
        }
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


class TestNewCategorySchemas:
    """Tests for the 6 new UCP category schemas."""

    def test_toys_games_has_required_attributes(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["toys_games"]
        assert isinstance(schema, UcpSchema)
        required = schema.required_attribute_names
        assert "age_range" in required
        assert "material" in required
        assert "safety_certification" in required

    def test_toys_games_battery_is_boolean(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["toys_games"]
        battery = next(a for a in schema.attributes if a.name == "battery_required")
        assert battery.data_type == "boolean"

    def test_sports_outdoors_has_required_attributes(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["sports_outdoors"]
        required = schema.required_attribute_names
        assert "sport_type" in required
        assert "material" in required
        assert "size" in required

    def test_books_media_format_allowed_values(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["books_media"]
        fmt = next(a for a in schema.attributes if a.name == "format")
        assert fmt.required
        assert set(fmt.allowed_values) == {"hardcover", "paperback", "digital", "vinyl"}

    def test_books_media_has_author_required(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["books_media"]
        assert "author" in schema.required_attribute_names

    def test_jewelry_watches_material_allowed_values(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["jewelry_watches"]
        mat = next(a for a in schema.attributes if a.name == "material")
        assert mat.required
        assert "gold" in mat.allowed_values
        assert "platinum" in mat.allowed_values

    def test_jewelry_watches_warranty_is_number(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["jewelry_watches"]
        warranty = next(a for a in schema.attributes if a.name == "warranty_months")
        assert warranty.data_type == "number"
        assert warranty.required

    def test_food_gourmet_has_required_attributes(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["food_gourmet"]
        required = schema.required_attribute_names
        assert "weight_g" in required
        assert "ingredients" in required
        assert "country_of_origin" in required

    def test_food_gourmet_allergens_is_list(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["food_gourmet"]
        allergens = next(a for a in schema.attributes if a.name == "allergens")
        assert allergens.data_type == "list"

    def test_pet_supplies_has_required_attributes(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["pet_supplies"]
        required = schema.required_attribute_names
        assert "pet_type" in required
        assert "size" in required
        assert "age_group" in required

    def test_pet_supplies_pet_type_allowed_values(self):
        schema = CANONICAL_CATEGORY_SCHEMAS["pet_supplies"]
        pet_type = next(a for a in schema.attributes if a.name == "pet_type")
        assert set(pet_type.allowed_values) == {
            "dog",
            "cat",
            "bird",
            "fish",
            "small_animal",
        }


class TestResolveUcpSchema:
    """Tests for the resolve_ucp_schema mapping function."""

    def test_exact_match(self):
        assert resolve_ucp_schema("electronics") is CANONICAL_CATEGORY_SCHEMAS["electronics"]

    def test_exact_match_all_categories(self):
        for key in CANONICAL_CATEGORY_SCHEMAS:
            assert resolve_ucp_schema(key) is not None

    def test_normalised_cat_prefix(self):
        result = resolve_ucp_schema("cat-electronics")
        assert result is CANONICAL_CATEGORY_SCHEMAS["electronics"]

    def test_normalised_spaces_and_ampersand(self):
        result = resolve_ucp_schema("sports & outdoors")
        assert result is CANONICAL_CATEGORY_SCHEMAS["sports_outdoors"]

    def test_alias_clothing_to_apparel(self):
        assert resolve_ucp_schema("clothing") is CANONICAL_CATEGORY_SCHEMAS["apparel"]

    def test_alias_cat_clothing(self):
        assert resolve_ucp_schema("cat-clothing") is CANONICAL_CATEGORY_SCHEMAS["apparel"]

    def test_alias_furniture(self):
        assert resolve_ucp_schema("furniture") is CANONICAL_CATEGORY_SCHEMAS["home_furniture"]

    def test_alias_cat_home_kitchen(self):
        assert (
            resolve_ucp_schema("cat-home-kitchen") is CANONICAL_CATEGORY_SCHEMAS["home_furniture"]
        )

    def test_alias_beauty_health(self):
        assert resolve_ucp_schema("beauty & health") is CANONICAL_CATEGORY_SCHEMAS["beauty"]

    def test_alias_cat_beauty_health(self):
        assert resolve_ucp_schema("cat-beauty-health") is CANONICAL_CATEGORY_SCHEMAS["beauty"]

    def test_alias_pet_supplies(self):
        assert resolve_ucp_schema("pet supplies") is CANONICAL_CATEGORY_SCHEMAS["pet_supplies"]

    def test_alias_cat_food_gourmet(self):
        assert resolve_ucp_schema("cat-food-gourmet") is CANONICAL_CATEGORY_SCHEMAS["food_gourmet"]

    def test_alias_cat_jewelry_watches(self):
        assert (
            resolve_ucp_schema("cat-jewelry-watches")
            is CANONICAL_CATEGORY_SCHEMAS["jewelry_watches"]
        )

    def test_alias_cat_books_media(self):
        assert resolve_ucp_schema("cat-books-media") is CANONICAL_CATEGORY_SCHEMAS["books_media"]

    def test_alias_cat_toys_games(self):
        assert resolve_ucp_schema("cat-toys-games") is CANONICAL_CATEGORY_SCHEMAS["toys_games"]

    def test_returns_none_for_unknown(self):
        assert resolve_ucp_schema("underwater_basket_weaving") is None

    def test_returns_none_for_empty_string(self):
        assert resolve_ucp_schema("") is None
