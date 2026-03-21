"""Unit tests for product service layer."""

from unittest.mock import AsyncMock

import pytest
from crud_service.schemas.domain.products import ProductQuery
from crud_service.services.product_service import (
    fetch_products,
    validate_product_responses,
)


@pytest.mark.asyncio
async def test_fetch_products_falls_back_to_repo_search():
    repo = AsyncMock()
    repo.search_by_name.return_value = [
        {
            "id": "p1",
            "name": "P1",
            "description": "d",
            "price": 1.0,
            "category_id": "c",
        }
    ]
    agent_client = AsyncMock()
    agent_client.semantic_search.side_effect = RuntimeError("down")
    logger = AsyncMock()

    products = await fetch_products(
        ProductQuery(search="shoe", category=None, limit=10, current_user=None),
        product_repo=repo,
        agent_client=agent_client,
        logger=logger,
        agent_fallback_exceptions=(RuntimeError,),
    )

    assert len(products) == 1
    assert products[0]["id"] == "p1"


def test_validate_product_responses_filters_invalid_records():
    logger = AsyncMock()
    valid = {
        "id": "p1",
        "name": "Product",
        "description": "Description",
        "price": 1.0,
        "category_id": "cat",
    }
    invalid = None

    result = validate_product_responses([valid, invalid], logger=logger)

    assert len(result) == 1
    assert result[0].id == "p1"
