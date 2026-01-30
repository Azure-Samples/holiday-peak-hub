"""Order repository."""

from crud_service.repositories.base import BaseRepository


class OrderRepository(BaseRepository):
    """Repository for orders container."""

    def __init__(self):
        super().__init__(container_name="orders")

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get orders for a specific user."""
        return await self.query(
            query="SELECT * FROM c WHERE c.user_id = @user_id ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit",
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit},
            ],
            partition_key=user_id,
        )

    async def get_by_status(self, status: str, limit: int = 100) -> list[dict]:
        """Get orders by status."""
        return await self.query(
            query="SELECT * FROM c WHERE c.status = @status ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit",
            parameters=[
                {"name": "@status", "value": status},
                {"name": "@limit", "value": limit},
            ],
        )
