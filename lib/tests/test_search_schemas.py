"""Unit tests for search-oriented schemas (search.py)."""

from datetime import datetime, timezone

import pytest
from holiday_peak_lib.schemas.search import IntentClassification, SearchEnrichedProduct


class TestSearchEnrichedProduct:
    """Tests for SearchEnrichedProduct model."""

    @pytest.mark.parametrize(
        "payload",
        [
            {
                "id": "SEP-1",
                "entityId": "STYLE-1",
                "sku": "SKU-1",
                "name": "Trail Shoe",
                "brand": "Contoso",
                "category": "footwear",
                "sourceApprovalVersion": 3,
            },
            {
                "id": "SEP-2",
                "entityId": "STYLE-2",
                "sku": "SKU-2",
                "name": "Running Shoe",
                "brand": "Fabrikam",
                "category": "footwear",
                "description": "Breathable upper",
                "price": 129.99,
                "useCases": ["running"],
                "complementaryProducts": ["SKU-SOCK-1"],
                "substituteProducts": ["SKU-ALT-1"],
                "searchKeywords": ["shoe", "breathable"],
                "enrichedDescription": "Lightweight breathable trail shoe.",
                "enrichedAt": datetime(2026, 3, 1, tzinfo=timezone.utc),
                "enrichmentModel": "gpt-4o-mini",
                "sourceApprovalVersion": 5,
            },
        ],
    )
    def test_required_and_optional_fields(self, payload: dict):
        model = SearchEnrichedProduct(**payload)
        assert model.id.startswith("SEP-")
        assert model.entity_id.startswith("STYLE-")
        assert model.source_approval_version > 0

    def test_json_roundtrip(self):
        model = SearchEnrichedProduct(
            id="SEP-3",
            entityId="STYLE-3",
            sku="SKU-3",
            name="Hiking Boot",
            brand="Contoso",
            category="boots",
            useCases=["hiking"],
            sourceApprovalVersion=7,
        )
        payload = model.model_dump_json(by_alias=True)
        restored = SearchEnrichedProduct.model_validate_json(payload)
        assert restored.entity_id == "STYLE-3"
        assert restored.use_cases == ["hiking"]


class TestIntentClassification:
    """Tests for IntentClassification model."""

    @pytest.mark.parametrize("query_type", ["simple", "complex"])
    def test_required_and_optional_fields(self, query_type: str):
        model = IntentClassification(queryType=query_type, confidence=0.84)
        assert model.query_type == query_type
        assert model.attributes == []
        assert model.price_range == (None, None)

    @pytest.mark.parametrize("confidence", [-0.01, 1.01])
    def test_confidence_bounds(self, confidence: float):
        with pytest.raises(Exception):
            IntentClassification(queryType="simple", confidence=confidence)

    def test_json_roundtrip(self):
        model = IntentClassification(
            queryType="complex",
            category="footwear",
            attributes=["waterproof", "lightweight"],
            useCase="hiking",
            brand="Contoso",
            priceRange=(100.0, 200.0),
            filters={"size": "10"},
            subQueries=["waterproof hiking shoe", "lightweight hiking boot"],
            confidence=0.91,
        )
        payload = model.model_dump_json(by_alias=True)
        restored = IntentClassification.model_validate_json(payload)
        assert restored.query_type == "complex"
        assert restored.sub_queries[0] == "waterproof hiking shoe"
