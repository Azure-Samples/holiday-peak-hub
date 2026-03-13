"""Inventory reservation repository."""

from crud_service.repositories.base import BaseRepository


class ReservationRepository(BaseRepository):
    """Repository for inventory reservations."""

    def __init__(self):
        super().__init__(container_name="inventory_reservations")
