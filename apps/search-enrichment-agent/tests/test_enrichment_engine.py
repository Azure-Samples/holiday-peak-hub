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

    assert set(fields.keys()) == {
        "use_cases",
        "complementary_products",
        "substitute_products",
        "search_keywords",
        "enriched_description",
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
