"""Product repository."""

from crud_service.repositories.base import BaseRepository


class ProductRepository(BaseRepository):
    """Repository for products container."""

    def __init__(self):
        super().__init__(container_name="products")

    async def search_by_name(self, search_term: str, limit: int = 20) -> list[dict]:
        """Search products by name."""
        return await self.query(
            query="SELECT * FROM c WHERE CONTAINS(LOWER(c.name), LOWER(@term)) OFFSET 0 LIMIT @limit",
            parameters=[
                {"name": "@term", "value": search_term},
                {"name": "@limit", "value": limit},
            ],
        )

    async def get_by_category(self, category_id: str, limit: int = 50) -> list[dict]:
        """Get products by category."""
        return await self.query(
            query="SELECT * FROM c WHERE c.category_id = @category_id OFFSET 0 LIMIT @limit",
            parameters=[
                {"name": "@category_id", "value": category_id},
                {"name": "@limit", "value": limit},
            ],
        )
