"""Test fixtures for Truth Ingestion service tests."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from truth_ingestion.adapters import (
    DAMConnector,
    EventPublisher,
    IngestionAdapters,
    PIMConnector,
    TruthStoreAdapter,
)


@pytest.fixture
def sample_pim_product():
    """A minimal raw PIM product payload."""
    return {
        "id": "PROD-001",
        "name": "Winter Jacket",
        "category": "outerwear",
        "brand": "PeakWear",
        "description": "A warm winter jacket",
        "source": "pim",
        "variants": [
            {
                "variant_id": "VAR-001",
                "sku": "WJ-RED-M",
                "color": "red",
                "size": "M",
                "price": 129.99,
            }
        ],
    }


@pytest.fixture
def sample_pim_product_no_variants():
    """A raw PIM product payload without variants."""
    return {
        "id": "PROD-002",
        "name": "Summer T-Shirt",
        "category": "tops",
        "brand": "PeakWear",
        "description": "A lightweight summer tee",
        "source": "pim",
    }


@pytest.fixture
def mock_truth_store():
    """TruthStoreAdapter with mocked async methods."""
    store = TruthStoreAdapter()
    store.upsert_product_style = AsyncMock(
        side_effect=lambda style: style.to_dict()
    )
    store.upsert_product_variant = AsyncMock(
        side_effect=lambda variant: variant.to_dict()
    )
    store.write_audit_event = AsyncMock(return_value=None)
    store.get_product_style = AsyncMock(return_value=None)
    return store


@pytest.fixture
def mock_pim():
    """PIMConnector with mocked async methods."""
    pim = PIMConnector()
    pim.fetch_product = AsyncMock(return_value=None)
    pim.fetch_products_page = AsyncMock(return_value=[])
    pim.fetch_all_products = AsyncMock(return_value=[])
    return pim


@pytest.fixture
def mock_dam():
    """DAMConnector with mocked async methods."""
    dam = DAMConnector()
    dam.fetch_assets = AsyncMock(return_value=[
        {"type": "image", "url": "https://example.com/images/PROD-001.png"}
    ])
    return dam


@pytest.fixture
def mock_events():
    """EventPublisher with mocked async methods."""
    publisher = EventPublisher()
    publisher.publish = AsyncMock(return_value=None)
    publisher.publish_completeness_job = AsyncMock(return_value=None)
    publisher.publish_ingestion_notification = AsyncMock(return_value=None)
    return publisher


@pytest.fixture
def mock_adapters(mock_truth_store, mock_pim, mock_dam, mock_events):
    """IngestionAdapters with all adapters mocked."""
    return IngestionAdapters(
        truth_store=mock_truth_store,
        pim=mock_pim,
        dam=mock_dam,
        events=mock_events,
    )
