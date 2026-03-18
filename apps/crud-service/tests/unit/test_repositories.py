"""Unit tests for product repository."""

import pytest
from crud_service.repositories import ProductRepository


@pytest.mark.asyncio
async def test_search_by_name(mock_cosmos_db):
    """Test product search by name."""
    repo = ProductRepository()
    results = await repo.search_by_name("test")

    assert len(results) >= 2
    assert all("test" in product["name"].lower() for product in results)


@pytest.mark.asyncio
async def test_get_by_category(mock_cosmos_db):
    """Test get products by category."""
    repo = ProductRepository()
    results = await repo.get_by_category("electronics")

    assert len(results) == 2
    assert all(product["category_id"] == "electronics" for product in results)
