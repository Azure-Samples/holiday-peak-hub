"""Return request repository."""

from crud_service.repositories.base import BaseRepository


class ReturnRequestRepository(BaseRepository):
    """Repository for return request records."""

    def __init__(self):
        super().__init__(container_name="return_requests")

    async def get_by_user(self, user_id: str, limit: int = 50) -> list[dict]:
        """Get return requests for a specific user."""
        return await self.query(
            query=(
                "SELECT * FROM c WHERE c.user_id = @user_id "
                "ORDER BY c.created_at DESC OFFSET 0 LIMIT @limit"
            ),
            parameters=[
                {"name": "@user_id", "value": user_id},
                {"name": "@limit", "value": limit},
            ],
            partition_key=user_id,
        )
