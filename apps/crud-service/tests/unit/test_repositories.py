"""Unit tests for product repository."""

import pytest

from crud_service.repositories import ProductRepository


@pytest.mark.asyncio
async def test_search_by_name(mock_cosmos_db):
    """Test product search by name."""
    repo = ProductRepository()
    
    # TODO: Mock Cosmos DB query
    # results = await repo.search_by_name("test")
    # assert len(results) > 0
    
    pass


@pytest.mark.asyncio
async def test_get_by_category(mock_cosmos_db):
    """Test get products by category."""
    repo = ProductRepository()
    
    # TODO: Mock Cosmos DB query
    # results = await repo.get_by_category("category-123")
    # assert len(results) > 0
    
    pass
