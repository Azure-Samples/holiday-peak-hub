"""Unit tests for cart service layer."""

from unittest.mock import AsyncMock

import pytest
from crud_service.auth import User
from crud_service.schemas.domain.cart import AddCartItemCommand
from crud_service.services.cart_service import add_item_to_cart
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_add_item_to_cart_raises_when_product_missing():
    repo = AsyncMock()
    repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc:
        await add_item_to_cart(
            AddCartItemCommand(
                product_id="sku1",
                quantity=1,
                current_user=User(
                    user_id="u1",
                    email="u1@example.com",
                    name="User One",
                    roles=["customer"],
                ),
            ),
            product_repo=repo,
            cart_repo=AsyncMock(),
            agent_client=AsyncMock(),
            event_publisher=AsyncMock(),
            logger=AsyncMock(),
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_item_to_cart_creates_cart_when_missing():
    product_repo = AsyncMock()
    product_repo.get_by_id.return_value = {"id": "sku1", "price": 2.5}

    cart_repo = AsyncMock()
    cart_repo.get_by_user.return_value = None

    await add_item_to_cart(
        AddCartItemCommand(
            product_id="sku1",
            quantity=2,
            current_user=User(
                user_id="u1",
                email="u1@example.com",
                name="User One",
                roles=["customer"],
            ),
        ),
        product_repo=product_repo,
        cart_repo=cart_repo,
        agent_client=AsyncMock(),
        event_publisher=AsyncMock(),
        logger=AsyncMock(),
    )

    assert cart_repo.update.await_count == 1
