"""Inventory repository."""

from crud_service.repositories.base import BaseRepository


class InventoryRepository(BaseRepository):
    """Repository for inventory records keyed by SKU."""

    def __init__(self):
        super().__init__(container_name="inventory")
