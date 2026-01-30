"""User repository."""

from crud_service.repositories.base import BaseRepository


class UserRepository(BaseRepository):
    """Repository for users container."""

    def __init__(self):
        super().__init__(container_name="users")

    async def get_by_email(self, email: str) -> dict | None:
        """Get user by email."""
        results = await self.query(
            query="SELECT * FROM c WHERE c.email = @email",
            parameters=[{"name": "@email", "value": email}],
        )
        return results[0] if results else None

    async def get_by_entra_id(self, entra_id: str) -> dict | None:
        """Get user by Entra ID."""
        results = await self.query(
            query="SELECT * FROM c WHERE c.entra_id = @entra_id",
            parameters=[{"name": "@entra_id", "value": entra_id}],
        )
        return results[0] if results else None
