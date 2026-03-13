"""Refund repository."""

from crud_service.repositories.base import BaseRepository


class RefundRepository(BaseRepository):
    """Repository for refunds."""

    def __init__(self):
        super().__init__(container_name="refunds")

    async def get_by_return_id(self, return_id: str) -> dict | None:
        """Get refund by associated return id."""
        records = await self.query(
            query="SELECT * FROM c WHERE c.return_id = @return_id OFFSET 0 LIMIT 1",
            parameters=[{"name": "@return_id", "value": return_id}],
        )
        return records[0] if records else None
