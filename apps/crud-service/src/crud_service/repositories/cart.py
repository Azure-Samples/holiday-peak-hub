"""Cart repository."""

from crud_service.repositories.base import BaseRepository


class CartRepository(BaseRepository):
    """Repository for cart container."""

    def __init__(self):
        super().__init__(container_name="cart")

    async def get_by_user(self, user_id: str) -> dict | None:
        """Get active cart for a user."""
        results = await self.query(
            query="SELECT * FROM c WHERE c.user_id = @user_id AND c.status = 'active'",
            parameters=[{"name": "@user_id", "value": user_id}],
            partition_key=user_id,
        )
        return results[0] if results else None

    async def clear_cart(self, user_id: str) -> None:
        """Clear user's cart (mark as completed)."""
        cart = await self.get_by_user(user_id)
        if cart:
            cart["status"] = "completed"
            await self.update(cart)
