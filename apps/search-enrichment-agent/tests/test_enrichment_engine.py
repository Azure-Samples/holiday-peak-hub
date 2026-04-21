"""Unit tests for search enrichment engine."""

from __future__ import annotations

from search_enrichment_agent.enrichment_engine import SearchEnrichmentEngine


def test_build_simple_fields_returns_required_keys() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {
            "sku": "SKU-1",
            "name": "Trail Shoe",
            "category": "shoe",
            "description": "Lightweight trail running shoe for daily routes.",
            "brand": "Peak",
        }
    )

    assert set(fields.keys()) >= {
        "use_cases",
        "complementary_products",
        "substitute_products",
        "search_keywords",
        "enriched_description",
        "marketing_bullets",
        "seo_title",
        "target_audience",
        "seasonal_relevance",
        "facet_tags",
        "sustainability_signals",
        "care_guidance",
        "completeness_pct",
    }
    assert isinstance(fields["search_keywords"], list)
    assert fields["enriched_description"]


def test_build_complex_fields_prefers_model_values_when_present() -> None:
    engine = SearchEnrichmentEngine()
    approved = {
        "sku": "SKU-2",
        "name": "Winter Jacket",
        "category": "jacket",
        "description": "Insulated jacket with hood and water-resistant shell.",
    }
    model_output = {
        "use_cases": ["winter commuting", "travel"],
        "search_keywords": ["insulated", "winter jacket"],
        "enriched_description": "Warm insulated jacket for cold weather commuting.",
    }

    fields = engine.build_complex_fields(approved, model_output)

    assert fields["use_cases"] == ["winter commuting", "travel"]
    assert fields["search_keywords"] == ["insulated", "winter jacket"]
    assert "cold weather" in fields["enriched_description"].lower()


def test_is_complex_detects_long_description() -> None:
    engine = SearchEnrichmentEngine()
    approved = {
        "description": " ".join(["feature"] * 40),
        "features": ["f1"],
    }
    assert engine.is_complex(approved) is True


def test_validate_fields_normalizes_types() -> None:
    engine = SearchEnrichmentEngine()
    validated = engine.validate_fields(
        {
            "use_cases": "daily use",
            "complementary_products": None,
            "substitute_products": ["Alt A", "Alt B"],
            "search_keywords": ["a", "b"],
            "enriched_description": "  useful text  ",
        }
    )

    assert validated["use_cases"] == ["daily use"]
    assert validated["complementary_products"] == []
    assert validated["substitute_products"] == ["Alt A", "Alt B"]
    assert validated["enriched_description"] == "useful text"


# -----------------------------------------------------------------------
# Amplification dimension tests
# -----------------------------------------------------------------------


def test_simple_fields_include_amplification_keys() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {
            "sku": "SKU-A",
            "name": "Organic Cotton T-Shirt",
            "category": "apparel",
            "brand": "EcoWear",
            "description": "Soft organic cotton everyday tee.",
            "material": "organic cotton",
            "color": "navy",
            "price": 29.99,
        }
    )
    assert "marketing_bullets" in fields
    assert "seo_title" in fields
    assert "target_audience" in fields
    assert "seasonal_relevance" in fields
    assert "facet_tags" in fields
    assert "sustainability_signals" in fields
    assert "care_guidance" in fields
    assert "completeness_pct" in fields


def test_seo_title_generated() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {"name": "Running Shoe Pro", "brand": "Nike", "category": "footwear"}
    )
    assert "Running Shoe Pro" in fields["seo_title"]
    assert len(fields["seo_title"]) <= 70


def test_marketing_bullets_from_features() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {
            "name": "Widget",
            "brand": "Acme",
            "features": ["Waterproof design", "Lightweight frame", "USB-C charging"],
        }
    )
    assert len(fields["marketing_bullets"]) >= 3
    assert "Trusted quality from Acme" in fields["marketing_bullets"]


def test_facet_tags_include_brand_and_category() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {"name": "Jacket", "brand": "Patagonia", "category": "apparel", "color": "red"}
    )
    tags = fields["facet_tags"]
    assert "brand:patagonia" in tags
    assert "category:apparel" in tags
    assert "color:red" in tags


def test_facet_tags_include_price_tier() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {"name": "Watch", "brand": "Rolex", "category": "jewelry", "price": 8000}
    )
    assert "price:luxury" in fields["facet_tags"]


def test_sustainability_signals_detected() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {
            "name": "Eco Bag",
            "material": "recycled polyester",
            "description": "Made from 100% recycled materials, vegan and cruelty-free.",
            "cruelty_free": True,
        }
    )
    signals = fields["sustainability_signals"]
    assert "recycled" in signals
    assert "cruelty-free" in signals
    assert "vegan" in signals


def test_sustainability_signals_empty_for_conventional() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {"name": "Metal Wrench", "material": "steel", "description": "Heavy-duty wrench."}
    )
    assert fields["sustainability_signals"] == []


def test_care_guidance_from_material() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields({"name": "Leather Wallet", "material": "genuine leather"})
    assert fields["care_guidance"] is not None
    assert "leather" in fields["care_guidance"].lower() or "wipe" in fields["care_guidance"].lower()


def test_care_guidance_none_for_unknown_material() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields({"name": "Gadget", "material": "titanium alloy"})
    assert fields["care_guidance"] is None


def test_care_guidance_from_explicit_instructions() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {"name": "Shirt", "care_instructions": "Machine wash cold, hang dry."}
    )
    assert fields["care_guidance"] == "Machine wash cold, hang dry."


def test_completeness_pct_full_product() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {
            "name": "Shoe",
            "brand": "Nike",
            "category": "footwear",
            "description": "Running shoe",
            "price": 99.99,
            "features": ["lightweight"],
            "images": ["img1.jpg"],
        }
    )
    assert fields["completeness_pct"] == 1.0


def test_completeness_pct_sparse_product() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields({"name": "Unknown"})
    assert fields["completeness_pct"] < 0.5


def test_target_audience_inferred_from_gender() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields({"name": "Dress", "category": "apparel", "gender": "women"})
    assert "women" in fields["target_audience"]


def test_target_audience_fallback_general() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields({"name": "Widget", "category": "misc"})
    assert "general consumers" in fields["target_audience"]


def test_seasonal_relevance_winter() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields(
        {
            "name": "Thermal Jacket",
            "category": "winter apparel",
            "description": "Insulated winter coat.",
        }
    )
    assert "winter" in fields["seasonal_relevance"]


def test_seasonal_relevance_year_round() -> None:
    engine = SearchEnrichmentEngine()
    fields = engine.build_simple_fields({"name": "Pen", "category": "office"})
    assert "year-round" in fields["seasonal_relevance"]


def test_use_case_inference_expanded_categories() -> None:
    engine = SearchEnrichmentEngine()
    for cat, expected_marker in [
        ("electronics gadget", "productivity"),
        ("pet supplies store", "pet care"),
        ("garden tools", "gardening"),
        ("office desk", "productivity"),
        ("baby stroller", "infant care"),
    ]:
        fields = engine.build_simple_fields({"name": "Item", "category": cat})
        assert any(
            expected_marker in uc for uc in fields["use_cases"]
        ), f"Expected '{expected_marker}' for category '{cat}', got {fields['use_cases']}"


def test_validate_fields_includes_amplification() -> None:
    engine = SearchEnrichmentEngine()
    validated = engine.validate_fields(
        {
            "use_cases": ["a"],
            "complementary_products": [],
            "substitute_products": [],
            "search_keywords": ["k"],
            "enriched_description": "desc",
            "marketing_bullets": ["bullet 1"],
            "seo_title": "SEO Title",
            "target_audience": ["men"],
            "seasonal_relevance": ["summer"],
            "facet_tags": ["brand:x"],
            "sustainability_signals": ["organic"],
            "care_guidance": "Hand wash.",
            "completeness_pct": 0.85,
        }
    )
    assert validated["marketing_bullets"] == ["bullet 1"]
    assert validated["seo_title"] == "SEO Title"
    assert validated["completeness_pct"] == 0.85


def test_complex_fields_merge_amplification_from_model() -> None:
    engine = SearchEnrichmentEngine()
    approved = {
        "sku": "SKU-X",
        "name": "Pro Widget",
        "category": "electronics",
        "brand": "TechCo",
        "description": " ".join(["advanced"] * 35),
        "features": ["wireless", "bluetooth", "usb-c", "fast-charge"],
    }
    model_output = {
        "marketing_bullets": ["Next-gen wireless", "Ultra-fast charging"],
        "seo_title": "TechCo Pro Widget - Advanced Electronics",
        "sustainability_signals": ["recycled"],
    }
    fields = engine.build_complex_fields(approved, model_output)
    assert fields["marketing_bullets"] == ["Next-gen wireless", "Ultra-fast charging"]
    assert fields["seo_title"] == "TechCo Pro Widget - Advanced Electronics"
    assert "recycled" in fields["sustainability_signals"]
