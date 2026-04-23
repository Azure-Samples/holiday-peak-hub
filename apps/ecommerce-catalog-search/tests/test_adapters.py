"""Unit tests for catalog adapter strategy."""

import pytest
from ecommerce_catalog_search.adapters import (
    SEARCH_MODE_INTELLIGENT,
    SEARCH_MODE_KEYWORD,
    build_catalog_adapters,
    normalize_search_mode,
)
from holiday_peak_lib.adapters.mock_adapters import MockProductAdapter


class TestBuildCatalogAdapters:
    """Strategy selection tests for adapter builder."""

    def test_build_catalog_adapters_defaults_to_mock_product_adapter(self, monkeypatch):
        # Agent isolation: CRUD_SERVICE_URL must not influence adapter selection.
        monkeypatch.setenv("CRUD_SERVICE_URL", "http://crud-service")

        adapters = build_catalog_adapters()

        assert isinstance(adapters.products.adapter, MockProductAdapter)


class TestSearchModeNormalization:
    """Tests for centralized mode normalization strategy."""

    @pytest.mark.parametrize("raw_mode", [None, "", "unsupported"])
    def test_normalize_search_mode_defaults_to_intelligent(self, raw_mode):
        assert normalize_search_mode(raw_mode) == SEARCH_MODE_INTELLIGENT

    def test_normalize_search_mode_preserves_explicit_keyword(self):
        assert normalize_search_mode("keyword") == SEARCH_MODE_KEYWORD
