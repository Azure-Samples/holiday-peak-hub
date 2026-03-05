"""Tests for UCP schema models."""

from datetime import datetime

import pytest
from holiday_peak_lib.schemas.ucp import (
    UcpCompliance,
    UcpImage,
    UcpMetadata,
    UcpPricing,
    UcpProduct,
)


class TestUcpModels:
    """Test UCP schema definitions."""

    def test_minimal_ucp_product(self):
        product = UcpProduct(entity_id="style-001", sku="SKU-001", title="Basic Tee")
        payload = product.model_dump()

        assert product.entity_id == "style-001"
        assert product.sku == "SKU-001"
        assert product.title == "Basic Tee"
        assert payload["images"] == []
        assert payload["pricing"]["currency"] == "USD"
        assert payload["compliance"]["completeness_score"] == 0.0
        assert payload["metadata"]["protocol"] == "ucp"

    def test_full_ucp_product(self):
        product = UcpProduct(
            entity_id="style-100",
            sku="SKU-100-BLK-M",
            title="Trail Jacket",
            brand="PeakWear",
            category_id="apparel",
            category_label="Apparel",
            enriched_description="Water-resistant technical jacket.",
            short_description="Trail Jacket",
            images=[
                UcpImage(
                    url="https://cdn.example.com/jacket-front.jpg",
                    role="primary",
                    alt_text="Black jacket front",
                )
            ],
            pricing=UcpPricing(list_price=149.99, sale_price=119.99, currency="USD"),
            attributes={"waterproof_rating": "10k", "season": "winter"},
            compliance=UcpCompliance(
                completeness_score=0.92,
                last_validated=datetime(2026, 3, 1, 10, 0, 0),
            ),
            metadata=UcpMetadata(version="1.1", protocol="ucp"),
        )
        payload = product.model_dump()

        assert product.brand == "PeakWear"
        assert payload["images"][0]["role"] == "primary"
        assert payload["pricing"]["sale_price"] == 119.99
        assert payload["attributes"]["season"] == "winter"
        assert payload["compliance"]["completeness_score"] == 0.92
        assert payload["metadata"]["version"] == "1.1"

    def test_compliance_score_bounds(self):
        valid = UcpCompliance(completeness_score=1.0)
        assert valid.completeness_score == 1.0

        with pytest.raises(Exception):
            UcpCompliance(completeness_score=1.5)
